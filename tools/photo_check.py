#!/usr/bin/env python3
"""Pre-delivery check for an edited photo: zoomed before/after crops of every place that changed,
plus automatic flags for defects we have shipped (or nearly shipped) before.

Usage:
  python3 tools/photo_check.py ORIGINAL EDITED [-o OUT_DIR] [--global]
  python3 tools/photo_check.py --pairs DIR            # every *_retouched.jpg / *_graded.jpg in DIR vs its HEIC/JPG

--global   the edit touches the whole frame (colour grade, dehaze): crops come from a fixed grid of
           risky areas (sky near the sun, ridges, shadows, highlights) instead of the change map.

Writes OUT_DIR/<name>_check.jpg (full frame side by side + up to 8 zoomed before/after crops, each
labelled with its pixel box) and prints one line per image: OK, or FLAG with the reasons.
FLAG does not mean broken and OK does not mean clean: the crops still have to be LOOKED AT. The
`photo-reviewer` agent does that; never deliver photo edits before it passes (see CLAUDE.md).

Automatic flags (each one is a real defect from 2026-10):
- sky_dark_blob   : a patch of sky got much darker than the sky around it (sky-mask hole, IMG_2619)
- sky_white_block : near-white blocks appeared in the sky (clipped streak core, IMG_2650)
- banding         : a smooth sky gradient turned into visible steps (dehaze near the sun, IMG_2650)
- clipped         : many more pure-black/pure-white pixels than the original (over-grade)
- colour_cast     : the average colour of the frame shifted strongly (wrong white balance)
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def load(path, size=None):
    if path.lower().endswith((".heic", ".heif")):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        subprocess.run(["sips", "-s", "format", "png", path, "--out", tmp], check=True, capture_output=True)
        path = tmp
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.array(im)


def sky_mask(img):
    L = img.astype(np.float32).mean(2)
    tex = cv2.GaussianBlur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 2)), (0, 0), 6)
    smooth = (tex < 0.6).astype(np.uint8)
    n, lab = cv2.connectedComponents(smooth)
    top = np.unique(lab[:16][smooth[:16] > 0])
    areas = np.bincount(lab.ravel())
    keep = [k for k in top if areas[k] > 0.002 * L.size]
    return np.isin(lab, keep)


def flags(orig, edit, is_global):
    out = []
    o, e = orig.astype(np.float32), edit.astype(np.float32)
    sky = sky_mask(orig)
    Lo, Le = o.mean(2), e.mean(2)
    if sky.mean() > 0.03:
        # a patch darker than the sky around it IN THE EDIT (removing a bright streak darkens the
        # sky vs the original, but leaves it level with its surroundings - that is fine)
        ref = cv2.GaussianBlur(Le * sky, (0, 0), 120) / np.maximum(cv2.GaussianBlur(sky.astype(np.float32), (0, 0), 120), 1e-3)
        inner = cv2.erode(sky.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
        blob = (Le - ref < -18) & (Le - Lo < -8) & inner
        blob = cv2.morphologyEx(blob.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        if blob.sum() > 400:
            ys, xs = np.nonzero(blob)
            out.append(f"sky_dark_blob@{xs.min()},{ys.min()},{xs.max()},{ys.max()}")
        white = (Le > 245) & (Lo < 235) & sky
        white = cv2.morphologyEx(white.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        if white.sum() > 400:
            ys, xs = np.nonzero(white)
            out.append(f"sky_white_block@{xs.min()},{ys.min()},{xs.max()},{ys.max()}")
        # banding: second derivative of the smoothed sky is spiky in the edit but not in the original
        def steps(L):
            g = cv2.GaussianBlur(L, (0, 0), 3)
            lap = np.abs(cv2.Laplacian(g, cv2.CV_32F, ksize=5))
            core = cv2.erode(sky.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
            return np.percentile(lap[core], 99.5) if core.any() else 0
        so, se = steps(Lo), steps(Le)
        if se > 2.5 * so + 3:
            out.append(f"banding({so:.1f}->{se:.1f})")
    for name, v in (("black", 2), ("white", 253)):
        po = ((o.max(2) <= v) if name == "black" else (o.min(2) >= v)).mean()
        pe = ((e.max(2) <= v) if name == "black" else (e.min(2) >= v)).mean()
        if pe > po + 0.01:
            out.append(f"clipped_{name}({po:.1%}->{pe:.1%})")
    shift = np.abs(e.reshape(-1, 3).mean(0) - o.reshape(-1, 3).mean(0))
    rb = (e[..., 0] - e[..., 2]).mean() - (o[..., 0] - o[..., 2]).mean()
    if abs(rb) > (45 if is_global else 25) or (not is_global and shift.max() > 12):
        out.append(f"colour_cast(dRGB={shift.round(1).tolist()})")
    return out


def change_boxes(orig, edit, n=8, box=700):
    d = np.abs(orig.astype(np.int16) - edit.astype(np.int16)).sum(2).astype(np.float32)
    d = cv2.GaussianBlur(d, (0, 0), 25)
    H, W = d.shape
    boxes = []
    for _ in range(n):
        y, x = np.unravel_index(d.argmax(), d.shape)
        if d[y, x] < 6:
            break
        x0, y0 = int(np.clip(x - box // 2, 0, W - box)), int(np.clip(y - box // 2, 0, H - box))
        boxes.append((x0, y0, x0 + box, y0 + box))
        d[max(y0 - box // 4, 0):y0 + box + box // 4, max(x0 - box // 4, 0):x0 + box + box // 4] = 0
    return boxes


def global_boxes(orig, box=700):
    H, W = orig.shape[:2]
    L = orig.astype(np.float32).mean(2)
    sky = sky_mask(orig)
    boxes = []
    def add(x, y):
        x0, y0 = int(np.clip(x - box // 2, 0, W - box)), int(np.clip(y - box // 2, 0, H - box))
        boxes.append((x0, y0, x0 + box, y0 + box))
    yb, xb = np.unravel_index(cv2.GaussianBlur(L, (0, 0), 50).argmax(), L.shape)
    add(xb, yb)                                            # brightest area (sun / near it)
    if sky.any():                                          # ridge line: lowest sky row per column, mid-frame
        cols = np.where(sky.any(0))[0]
        for cx in (cols[len(cols) // 4], cols[len(cols) // 2], cols[3 * len(cols) // 4]):
            add(cx, np.where(sky[:, cx])[0].max())
    add(*np.unravel_index(cv2.GaussianBlur(L, (0, 0), 50).argmin(), L.shape)[::-1])  # deepest shadow
    add(W // 2, int(H * 0.8))                              # foreground
    return boxes


def sheet(orig, edit, boxes, labels, path):
    H, W = orig.shape[:2]
    fw = 900
    fh = int(H * fw / W)
    tile = 440
    rows = (len(boxes) + 1) // 2
    S = Image.new("RGB", (2 * fw + 10, fh + 30 + rows * (tile + 24)), "white")
    d = ImageDraw.Draw(S)
    S.paste(Image.fromarray(orig).resize((fw, fh)), (0, 0))
    ed = Image.fromarray(edit).resize((fw, fh))
    de = ImageDraw.Draw(ed)
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        de.rectangle([x0 * fw / W, y0 * fh / H, x1 * fw / W, y1 * fh / H], outline=(255, 0, 255), width=2)
        de.text((x0 * fw / W + 3, y0 * fh / H + 2), str(i + 1), fill=(255, 0, 255))
    S.paste(ed, (fw + 10, 0))
    d.text((5, fh + 8), "  |  ".join(labels) if labels else "no automatic flags (still look at every crop)", fill="red" if labels else "black")
    for i, b in enumerate(boxes):
        r, c = divmod(i, 2)
        x, y = c * (fw + 10), fh + 30 + r * (tile + 24)
        S.paste(Image.fromarray(orig[b[1]:b[3], b[0]:b[2]]).resize((tile, tile)), (x, y + 18))
        S.paste(Image.fromarray(edit[b[1]:b[3], b[0]:b[2]]).resize((tile, tile)), (x + tile + 10, y + 18))
        d.text((x + 2, y + 2), f"#{i + 1} box {b}  before | after", fill="black")
    S.save(path, quality=88)


def check(orig_path, edit_path, out_dir, is_global):
    edit = load(edit_path)
    orig = load(orig_path, size=(edit.shape[1], edit.shape[0]))
    fl = flags(orig, edit, is_global)
    boxes = global_boxes(orig) if is_global else change_boxes(orig, edit)
    name = os.path.splitext(os.path.basename(edit_path))[0]
    path = os.path.join(out_dir, name + "_check.jpg")
    sheet(orig, edit, boxes, fl, path)
    print(f"{'FLAG' if fl else 'OK  '} {name}: {', '.join(fl) if fl else '-'}  -> {path}")
    return bool(fl)


def find_original(edit_path):
    base = os.path.basename(edit_path).split("_")[0] + "_" + os.path.basename(edit_path).split("_")[1] \
        if os.path.basename(edit_path).count("_") >= 2 else os.path.splitext(os.path.basename(edit_path))[0]
    stem = os.path.join(os.path.dirname(edit_path), base)
    for ext in (".HEIC", ".heic", ".JPG", ".jpg", ".jpeg", ".PNG", ".png"):
        if os.path.exists(stem + ext):
            return stem + ext
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--pairs", help="directory of *_retouched.jpg / *_graded.jpg next to their originals")
    ap.add_argument("-o", "--out", help="where to write *_check.jpg (default: a 'check' folder in the scratch/tmp dir)")
    ap.add_argument("--global", dest="is_global", action="store_true")
    a = ap.parse_args()
    out = a.out or os.path.join(tempfile.gettempdir(), "photo_check")
    os.makedirs(out, exist_ok=True)
    pairs = []
    if a.pairs:
        for f in sorted(glob.glob(os.path.join(a.pairs, "*_retouched.jpg")) + glob.glob(os.path.join(a.pairs, "*_graded.jpg"))):
            o = find_original(f)
            if o:
                pairs.append((o, f))
    elif len(a.files) == 2:
        pairs = [tuple(a.files)]
    else:
        sys.exit("give ORIGINAL EDITED, or --pairs DIR")
    nflag = sum(check(o, e, out, a.is_global or e.endswith("_graded.jpg")) for o, e in pairs)
    print(f"{len(pairs)} checked, {nflag} flagged. Sheets in {out}")


if __name__ == "__main__":
    main()
