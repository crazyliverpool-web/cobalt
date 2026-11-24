#!/usr/bin/env python3
"""Remove people from a photo: Mask R-CNN finds them, big-LaMa fills the holes.

Usage:
  python3 tools/remove_people.py IMG.HEIC                       # -> IMG_no_people.jpg next to the input
  python3 tools/remove_people.py IMG.jpg --extra 2195,3356,2242,3448 --extra ...
  python3 tools/remove_people.py IMG.jpg --mask-only            # write mask preview, don't inpaint

--extra x0,y0,x1,y1   additional rectangle to remove (upright full-res pixel coords),
                      e.g. a reflection in water the detector missed. Repeatable.
--min-size N          only remove people whose box is at least N px on its longer side
                      ("clearly visible" people; tiny distant figures are kept). Default 0 = all.
--protect-light       inside --extra rects, keep pale bluish pixels (white flowers in front
                      of a reflection) instead of filling over them.

Always inspect <out>_overlay.jpg and <out>_compare.jpg before trusting the result:
reflections, shadows and objects overlapping a person are not detected automatically.

Gotchas this tool already handles (learned 2026-10-09):
- iPhone HEIC/JPG are stored rotated (EXIF orientation 6) -> upright before detecting.
- Clouds can score ~0.5 as "person" -> detections whose feet are in the top
  --sky-frac of the frame are dropped.
- Only the masked crop goes through LaMa, so the rest of the photo stays bit-identical.
- (2026-10-11) Full-res fills of people on benches/loungers came out as smudges; LaMa fills a copy
  downscaled to --fill-res 512 and only masked pixels are upscaled back. Detector misses people
  seen from behind in shade -> add them with --extra.
- Lens ghosts (soft discs/domes on rock, a red dot on a fence) also come out cleanly with --extra
  and --min-size 99999 (no people detection; --thresh 0.999 still removed half a person); subtracting them as added light left rings (IMG_8151/8158).
- (2026-10-12, untitled folder 2, "remove ALL people"): a second pass with --thresh 0.15 catches what pass 1
  missed. Crowded restaurant terraces and people lying on loungers came out smeared (broken railings, blocky
  patches) -> ask the user; they chose to keep those. Small figures on thin railings also go blocky; despeckle /
  Telea made it worse. People cut by the frame edge leave a few-px strip -> trimming 40 px beat refilling.
  Output names: macOS is case-insensitive, so x_g.jpg and x_G.jpg are the SAME file.
- (2026-10-14, "st mag", Santa Maddalena, Sony 6000x4000): default thresh missed ~half of the tiny (~30 px)
  sunset-blurred walkers on far roads; pass 2 (--thresh 0.15 + reviewer boxes) got most. Widening --extra boxes
  over fences/poles erased them -> keep boxes tight (pad ~8 px) near thin structures. Fills of long crowded
  paths came out slightly lavender/blurry. "Keep people in zone X" = run normally, then paste original rows/box back
  (only masked pixels change, so the paste is seamless). Cars/cyclists are user's call - ask.
- (2026-10-21, "lake", Braies, 27 photos, 6 review rounds): --thresh 0.15 still missed most far-shore/cliff-path
  walkers (5-20 px) -> expect 2-3 reviewer rounds of --extra boxes. Keep-zone pastes: paste the whole changed
  component touching the box (diff orig vs edited > 25, dilate, connectedComponents), a fixed box cut a bride in half.
  People IN small boats (user: keep boat): the detector mask eats the whole boat; LaMa leaves blobs. Paste the boat
  back, then cover only the people above the hull with water copied from beside the boat at the SAME rows (lake
  tone varies with x, not y), tone-matched per row to the box's left/right edge pixels, feather ~4 px. Poisson
  (seamlessClone) bled the person's colours into the water. Check the source strip contains no post/pole.
  Reflections of removed people stay in the water; LaMa then extends them up onto the sand like posts -> box them
  too. Thin wire crossing a fill: fill over it, then redraw it by darkening its rows by the ratio measured on a
  clean stretch (copying a stretch brought along mesh ticks). Rope crossing a fill: --protect-light keeps it.
- (2026-10-21, "lake" round 2): the "edge strips" were a bug here - the multiple-of-8 crop dropped the last
  rows/cols at the bottom/right frame edge, so a few px of person stayed. Fixed in inpaint(); trimming not needed.
  People BEHIND a railing: subtract hand-placed rail lines/posts (cv2.line, width ~ bar thickness - 5) from the
  person mask so LaMa fills only between the bars; colour-thresholding the wood failed (shadowed bars, skin).
  A big group in a corner (seated by the hut wall) always smeared into boat texture at every --fill-res -> ask
  whether that group must go; warping a clean plate from another frame failed (camera moved, boats moved).
  Small hole next to a boat: LaMa extends the boat into a blob/ghost -> restore the boat from the original first.
  Fill too smooth on gravel/sand: take a same-shape patch shifted sideways from clean ground at the same rows and
  add only its fine detail (patch - GaussianBlur 12) on top of the fill's own blur, feathered -> grain matches,
  no seam. Per-row shifted copies (row by row) made horizontal streaks; don't.
- (2026-10-30, "dump", Seceda/Giau, crowded hiking paths): default --fill-res 512 smeared long crowded
  paths into blurry blobs; re-running from the ORIGINAL with --thresh 0.15 --fill-res 2048 fixed it. Big
  --extra rects sent to Codex (codex_fill.py) came back as visible tone-mismatched rectangles (sky, grass) -
  don't. Far walkers (5-15 px) along a railing under a dark cliff are never detected: mask only blobs that
  differ from a 21-px median inside a thin band above the rail line (open 3x3 kills the rail, so it survives),
  then LaMa at full res (scratch script blobfill.py did this). That trick fails on light paths through grass
  (the path itself is the blob). People LYING on grass are missed at every thresh -> --extra. Low thresh pass
  also erased a dark hut + tree -> paste that box back from the original.
- (2026-10-21, "lake" round 3, people seated against the hut wall behind 3 rail bars): every LaMa variant left
  ghosts. What worked: a CLEAN PLATE from another frame where that corner is empty - SIFT homography fitted only
  on background features near the hole (people, rails and the wall masked out), ECC translation refine on the
  strip beside the hole, smooth low-frequency colour field from the border ring (+ Lab row match smoothed in y),
  our own rails kept, and LaMa only for the other frame's wood-coloured bars (H 3-25, S>70) and pixels next to
  our bars. A whole-frame homography misaligned it (camera moved). Rows the person hid but which run horizontally
  (far rail, bench top) rebuild best by a sideways shift / true-mirror tile of the same rows. Water next to a wall
  from another frame still reads as a glass pane - tell the user.
  A plate's painted box face never matched in tone/perspective (reviewer: "pink rectangle"). Better: rebuild
  a horizontal band (bench box face) from THIS frame - only her mask pixels, each row-run blended from mirrored
  edge strips on both sides - then flatten the smeared letters inside to the local median. Reviewer at 2-3x
  zoom will always find something here; show the user a before/after sheet and let them decide.
- (2026-10-27, "tre cime", 23 photos, 5 review rounds): false detections removed a fog-wrapped tower face,
  a fog edge and face stickers on signposts -> paste the original back in those boxes. Reviewer boxes for tiny
  figures were often 30-60 px off, so fills hit grass/bushes and missed the person -> locate on a gridded zoom
  yourself before filling. Refugio yards/terraces: --fill-res 1024 beat 512 (fences, sheds, flagpole kept).
  Rows of 3-6 px heads above a pale wall: mask only pixels darker than a medianBlur(31) background by >22,
  dilate 5, LaMa -> wall untouched (a rect over the strip smeared it). Walkers against a rock face that the
  detector misses even at --thresh 0.15: a same-row sideways shift (tone-matched to the box edges) beat LaMa.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

LAMA_URL = "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt"
LAMA_MD5 = "e3aa4aaa15225a33ec84f9f4bc47e500"
LAMA_PATH = os.path.expanduser("~/.cache/studio/big-lama.pt")


def load_upright(path):
    if path.lower().endswith((".heic", ".heif")):
        # Pillow can't read HEIC without pillow-heif; macOS sips can.
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        subprocess.run(["sips", "-s", "format", "png", path, "--out", tmp], check=True, capture_output=True)
        path = tmp
    return np.array(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))


def lama_model():
    if not os.path.exists(LAMA_PATH):
        os.makedirs(os.path.dirname(LAMA_PATH), exist_ok=True)
        print("downloading big-lama (~200 MB, once)…", file=sys.stderr)
        urllib.request.urlretrieve(LAMA_URL, LAMA_PATH)
    with open(LAMA_PATH, "rb") as f:
        if hashlib.md5(f.read()).hexdigest() != LAMA_MD5:
            sys.exit(f"checksum mismatch for {LAMA_PATH}; delete it and rerun")
    return torch.jit.load(LAMA_PATH, map_location="cpu").eval()


def detect_people(img, thresh, sky_frac, min_size=0):
    from torchvision.models.detection import maskrcnn_resnet50_fpn_v2, MaskRCNN_ResNet50_FPN_V2_Weights
    model = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT).eval()
    H, W = img.shape[:2]
    T, step = min(1400, H, W), 1000  # overlapping full-res tiles: distant people are small
    min_bottom = H * sky_frac
    mask = np.zeros((H, W), np.uint8)
    n = 0
    with torch.no_grad():
        for y in range(0, max(H - T, 0) + step, step):
            for x in range(0, max(W - T, 0) + step, step):
                y0, x0 = min(y, H - T), min(x, W - T)
                t = torch.from_numpy(img[y0:y0 + T, x0:x0 + T]).permute(2, 0, 1).float() / 255
                r = model([t])[0]
                for lbl, sc, m, b in zip(r["labels"], r["scores"], r["masks"], r["boxes"]):
                    if lbl.item() == 1 and sc.item() >= thresh and b[3].item() + y0 > min_bottom \
                            and max(b[2] - b[0], b[3] - b[1]).item() >= min_size:
                        mask[y0:y0 + T, x0:x0 + T] |= (m[0].numpy() > 0.3).astype(np.uint8)
                        n += 1
    # grow to cover hair, edges and contact shadows
    return cv2.dilate(mask * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))), n


def add_extra(mask, img, rects, protect_light):
    for x0, y0, x1, y1 in rects:
        region = np.zeros_like(mask)
        region[y0:y1, x0:x1] = 255
        if protect_light:
            o = img.astype(int)
            light = ((o[..., 2] > o[..., 0] - 10) & (o.mean(axis=2) > 125)).astype(np.uint8)
            light = cv2.dilate(cv2.morphologyEx(light, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), np.ones((7, 7), np.uint8))
            region[light > 0] = 0
        mask |= region
    return mask


def inpaint(img, mask, model, pad=200, max_side=512):
    H, W = mask.shape
    merged = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (161, 161)))
    n, _, stats, _ = cv2.connectedComponentsWithStats((merged > 0).astype(np.uint8))
    out = img.astype(np.float32)
    for i in range(1, n):
        x, y, w, h = stats[i][:4]
        x0, y0 = max(x - pad, 0), max(y - pad, 0)
        x1, y1 = min(x + w + pad, W), min(y + h + pad, H)
        # LaMa needs multiples of 8: trim the side away from the frame edge, or a hole touching the
        # bottom/right edge keeps its last few rows of person (the old "edge strips")
        w8, h8 = (x1 - x0) // 8 * 8, (y1 - y0) // 8 * 8
        x0, x1 = (x1 - w8, x1) if x1 == W else (x0, x0 + w8)
        y0, y1 = (y1 - h8, y1) if y1 == H else (y0, y0 + h8)
        m = (mask[y0:y1, x0:x1] > 0).astype(np.float32)
        crop = img[y0:y1, x0:x1]
        # LaMa was trained ~512 px: big holes at 24 MP come out as smudges, so fill a downscaled
        # copy and upscale (only the masked pixels are used)
        s = min(1.0, max_side / max(crop.shape[:2]))
        cw, ch = (int(crop.shape[1] * s) // 8 * 8, int(crop.shape[0] * s) // 8 * 8) if s < 1 else crop.shape[1::-1]
        ci, cm = cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_AREA), cv2.resize(m, (cw, ch)) > 0.01
        ti = torch.from_numpy(ci).permute(2, 0, 1)[None].float() / 255
        with torch.no_grad():
            o = model(ti, torch.from_numpy(cm.astype(np.float32))[None, None])[0].permute(1, 2, 0).numpy()
        o = cv2.resize(np.clip(o * 255, 0, 255), crop.shape[1::-1], interpolation=cv2.INTER_CUBIC)
        alpha = np.maximum(cv2.GaussianBlur(m, (0, 0), 3), m)[..., None]  # replace masked, feather edges
        out[y0:y1, x0:x1] = alpha * o + (1 - alpha) * out[y0:y1, x0:x1]
    return out.round().clip(0, 255).astype(np.uint8), n - 1  # bicubic overshoot wrapped to speckles


def save_previews(img, result, mask, base):
    H, W = mask.shape
    ov = img.copy()
    ov[mask > 0] = (0.4 * ov[mask > 0] + 0.6 * np.array([255, 0, 255])).astype(np.uint8)
    Image.fromarray(ov).resize((W // 4, H // 4)).save(base + "_overlay.jpg", quality=85)
    if result is None:
        return
    ys, xs = np.nonzero(mask)
    y0, y1 = max(ys.min() - 150, 0), min(ys.max() + 150, H)
    a, b = Image.fromarray(img[y0:y1]), Image.fromarray(result[y0:y1])
    s = 2000 / W
    a, b = a.resize((2000, int(a.height * s))), b.resize((2000, int(b.height * s)))
    c = Image.new("RGB", (2000, a.height * 2 + 10), "white")
    c.paste(a, (0, 0)); c.paste(b, (0, a.height + 10))
    c.save(base + "_compare.jpg", quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("-o", "--out", help="output JPEG (default: <input>_no_people.jpg)")
    ap.add_argument("--thresh", type=float, default=0.3, help="person score threshold")
    ap.add_argument("--sky-frac", type=float, default=0.4, help="ignore detections whose feet are in this top fraction")
    ap.add_argument("--extra", action="append", default=[], help="x0,y0,x1,y1 extra area to remove")
    ap.add_argument("--min-size", type=int, default=0, help="skip people smaller than this (px, longer box side)")
    ap.add_argument("--protect-light", action="store_true")
    ap.add_argument("--fill-res", type=int, default=512, help="LaMa works on crops downscaled to this many px")
    ap.add_argument("--mask-only", action="store_true")
    a = ap.parse_args()

    out = a.out or os.path.splitext(a.image)[0] + "_no_people.jpg"
    base = os.path.splitext(out)[0]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img = load_upright(a.image)
    mask, n = detect_people(img, a.thresh, a.sky_frac, a.min_size)
    rects = [tuple(int(v) for v in r.split(",")) for r in a.extra]
    mask = add_extra(mask, img, rects, a.protect_light)
    print(f"{img.shape[1]}x{img.shape[0]}  people detections: {n}  extra rects: {len(rects)}")
    if not mask.any():
        sys.exit("nothing to remove")
    if a.mask_only:
        save_previews(img, None, mask, base)
        print("mask preview:", base + "_overlay.jpg")
        return
    # (2026-10-31 copenlake) a crowded bench group (~700x230 px hole) smeared to dark patches at every LaMa
    # fill-res and two LaMa passes; Codex filled it cleanly on the first try. Point big holes at codex_fill.
    n_lab, _, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8))
    big = [tuple(st[i][:4]) for i in range(1, n_lab) if max(st[i][2], st[i][3]) >= 250]
    if big:
        print(f"WARNING: {len(big)} hole(s) >= 250 px (x,y,w,h): {big}\n"
              "  LaMa smears big/crowded holes -> use tools/codex_fill.py for these (CLAUDE.md rule)", file=sys.stderr)
    result, regions = inpaint(img, mask, lama_model(), max_side=a.fill_res)
    Image.fromarray(result).save(out, quality=95, subsampling=0)
    save_previews(img, result, mask, base)
    print(f"filled {regions} regions -> {out}\ncheck: {base}_overlay.jpg  {base}_compare.jpg")


if __name__ == "__main__":
    main()
