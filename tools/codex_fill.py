#!/usr/bin/env python3
"""Remove people/objects with LaMa + Codex (gpt-image) working together.

LaMa fills every hole first (fast, free). Regions picked for Codex (big or complex: people behind
railings, on decks, against structures) are cropped with context, sent to Codex with a magenta-marked
copy, and only the masked pixels of Codex's answer are pasted back - tone-matched to the ring around
the hole and feathered - so the rest of the photo stays bit-identical at full resolution.

Usage:
  python3 -I tools/codex_fill.py IMG.JPG                          # detect people; regions >= --codex-min go to Codex
  python3 -I tools/codex_fill.py IMG.JPG --extra x0,y0,x1,y1      # add a rect to remove (full-res coords)
  python3 -I tools/codex_fill.py IMG.JPG --codex-box x0,y0,x1,y1  # force regions touching this rect to Codex
  python3 -I tools/codex_fill.py IMG.JPG --mask-only              # write <out>_regions.jpg, no fill
  python3 -I tools/codex_fill.py IMG.JPG --engine lama            # LaMa only (same as remove_people.py)

Outputs next to the input (or -o): <base>.jpg, <base>_overlay.jpg, <base>_compare.jpg,
<base>_zoom.jpg (each region: original | LaMa | final), <base>_codex/ (crops sent + answers).
Each Codex region costs one image generation (~1-2 min); jobs run in parallel (--jobs).
Always run photo-reviewer on the result before telling the user it is done (CLAUDE.md rule).

Lessons (2026-10-31, copenlake bench group, keep men / remove women):
- Keeping one person inside a removed crowd: his Mask R-CNN mask includes whoever stands behind him, and even a
  hand-drawn outline left their legs/shoulders/hair. If the kept person overlaps others, remove him too.
- Objects held/touched by removed people (bicycle, mobility scooter) come back as half-wheels: remove the whole object.
- Clip masks with a ~30 px margin around any earlier hand-restored box; a hard clip left dark wedges at the edge.
- Expect 1-2 tiny dark wedges per fill; reviewer finds them, a 30-px LaMa box fixes them.
"""
import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remove_people import load_upright, detect_people, add_extra, lama_model, inpaint, save_previews  # noqa: E402

RUN_SH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "codex-cli", "run.sh")
SIZES = [(1024, 1024), (1536, 1024), (1024, 1536)]  # gpt-image output shapes; crops use one of these aspects
PROMPT = """Photo retouch (inpainting), not a new picture. Image 1 is a crop of a real photograph. Image 2 is
the SAME crop with the area to remove painted solid magenta. Edit image 1: replace everything under the
magenta area with what would naturally be behind it ({what}) so it blends seamlessly with the surroundings -
same lighting, colour, grain, perspective and sharpness as the rest of the photo. Continue structures that
pass through the area (railings, posts, planks, shoreline, water ripples) correctly. Remove the {what}
completely, including shadows and reflections inside the magenta area. Outside the magenta area keep the
picture exactly as image 1: same framing, same objects, nothing added, nothing moved. No magenta in the result.
Output size {w}x{h}. Save it as filled.png in the current directory. Generate exactly one image."""


def regions_of(mask, gap=161):
    merged = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (gap, gap)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats((merged > 0).astype(np.uint8))
    return [(stats[i][:4], (lab == i) & (mask > 0)) for i in range(1, n)]


def context_box(x, y, w, h, W, H, pad_frac=1.2, min_side=640):
    """Crop around a hole with generous context, at the gpt-image aspect closest to the hole's."""
    side = max(w, h) * (1 + pad_frac)
    side = max(side, min_side)
    best = min(SIZES, key=lambda s: abs(np.log((w + side) / (h + side)) - np.log(s[0] / s[1])))
    cw = side * best[0] / max(best); ch = side * best[1] / max(best)
    cw, ch = min(cw, W), min(ch, H)
    cx, cy = x + w / 2, y + h / 2
    x0 = int(np.clip(cx - cw / 2, 0, W - cw)); y0 = int(np.clip(cy - ch / 2, 0, H - ch))
    return x0, y0, x0 + int(cw), y0 + int(ch), best


def run_codex(job, crop, rmask, size, outdir, what):
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{job}_codex.png")
    if os.path.exists(out):  # answer from an earlier run: reuse it, don't spend another generation
        return out
    src, marked = os.path.join(outdir, f"{job}_crop.png"), os.path.join(outdir, f"{job}_marked.png")
    ci = cv2.resize(crop, size, interpolation=cv2.INTER_AREA)
    cm = cv2.resize(rmask.astype(np.uint8), size, interpolation=cv2.INTER_NEAREST) > 0
    mk = ci.copy(); mk[cm] = (255, 0, 255)
    Image.fromarray(ci).save(src); Image.fromarray(mk).save(marked)
    task = PROMPT.format(what=what, w=size[0], h=size[1])
    # stdin must be closed: `codex exec` otherwise waits forever on "Reading additional input from stdin"
    r = subprocess.run([RUN_SH, job, task, src, marked], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    m = re.search(r"JOB: (\S+)", r.stdout)
    path = os.path.join(m.group(1), "filled.png") if m else None
    # Codex often reports "partial" because it can't keep pixels outside the mask identical - fine, we
    # only paste the masked pixels. Accept any run that produced the file.
    if not (path and os.path.exists(path)):
        print(f"[{job}] Codex failed:\n{r.stdout[-800:]}", file=sys.stderr)
        return None
    Image.open(path).convert("RGB").save(out)
    return out


def paste_codex(out, img, x0, y0, x1, y1, rmask, answer, sigma=25):
    """Paste only masked pixels of Codex's crop after a smooth per-pixel colour correction: the difference
    (photo - Codex) on a ring around the hole is spread into it by normalized Gaussian blur.
    (2026-10-31) A single global mean/std match left a visible purple oval on big ground fills; this doesn't."""
    cw, ch = x1 - x0, y1 - y0
    a = cv2.resize(np.array(Image.open(answer).convert("RGB")), (cw, ch), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    m = rmask.astype(np.uint8)
    ring = ((cv2.dilate(m, np.ones((25, 25), np.uint8)) > 0) & (m == 0)).astype(np.float32)
    d = (img[y0:y1, x0:x1].astype(np.float32) - a) * ring[..., None]
    w = cv2.GaussianBlur(ring, (0, 0), sigma) + 1e-4
    a = (a + np.stack([cv2.GaussianBlur(d[..., c], (0, 0), sigma) for c in range(3)], -1) / w[..., None]).clip(0, 255)
    mf = m.astype(np.float32)
    alpha = np.maximum(cv2.GaussianBlur(mf, (0, 0), 4), mf)[..., None]
    out[y0:y1, x0:x1] = alpha * a + (1 - alpha) * out[y0:y1, x0:x1]
    magenta = ((a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] > 200) & (m > 0)).sum()
    return int(magenta)


def zoom_sheet(img, lama, final, boxes, path):
    rows = []
    for (x0, y0, x1, y1), eng in boxes:
        tiles = [cv2.resize(t[y0:y1, x0:x1], (600, int(600 * (y1 - y0) / (x1 - x0)))) for t in (img, lama, final)]
        row = np.hstack([np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=255) for t in tiles])
        cv2.putText(row, f"{eng}  ({x0},{y0})-({x1},{y1})   original | LaMa | final", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        rows.append(row)
    w = max(r.shape[1] for r in rows)
    Image.fromarray(np.vstack([np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])) \
        .save(path, quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("-o", "--out", help="output JPEG (default: <input>_codex_fill.jpg)")
    ap.add_argument("--thresh", type=float, default=0.3)
    ap.add_argument("--sky-frac", type=float, default=0.4)
    ap.add_argument("--min-size", type=int, default=0)
    ap.add_argument("--extra", action="append", default=[], help="x0,y0,x1,y1 extra area to remove")
    ap.add_argument("--codex-box", action="append", default=[], help="x0,y0,x1,y1: regions touching it use Codex")
    ap.add_argument("--codex-min", type=int, default=250, help="regions whose longer side >= this go to Codex")
    ap.add_argument("--engine", choices=["auto", "lama", "codex"], default="auto")
    ap.add_argument("--fill-res", type=int, default=1024)
    ap.add_argument("--what", default="people", help="what is being removed (goes into the Codex prompt)")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--mask-only", action="store_true")
    a = ap.parse_args()

    rect = lambda s: tuple(int(v) for v in s.split(","))
    out = a.out or os.path.splitext(a.image)[0] + "_codex_fill.jpg"
    base = os.path.splitext(out)[0]
    img = load_upright(a.image)
    H, W = img.shape[:2]
    mask, n = detect_people(img, a.thresh, a.sky_frac, a.min_size) if a.min_size < 99999 else (np.zeros((H, W), np.uint8), 0)
    mask = add_extra(mask, img, [rect(r) for r in a.extra], False)
    if not mask.any():
        sys.exit("nothing to remove")
    forced = [rect(r) for r in a.codex_box]
    regs = []
    for (x, y, w, h), rm in regions_of(mask):
        touch = any(x < bx1 and x + w > bx0 and y < by1 and y + h > by0 for bx0, by0, bx1, by1 in forced)
        eng = "codex" if a.engine == "codex" or (a.engine == "auto" and (touch or max(w, h) >= a.codex_min)) else "lama"
        regs.append(((x, y, w, h), rm, eng))
    print(f"{W}x{H}  detections {n}  regions {len(regs)}  codex {sum(r[2] == 'codex' for r in regs)}")
    for (x, y, w, h), _, eng in regs:
        print(f"  {eng:5s} {x},{y},{x + w},{y + h}  ({w}x{h})")

    ov = img.copy()
    ov[mask > 0] = (0.4 * ov[mask > 0] + 0.6 * np.array([255, 0, 255])).astype(np.uint8)
    for (x, y, w, h), _, eng in regs:
        cv2.rectangle(ov, (x, y), (x + w, y + h), (0, 255, 255) if eng == "codex" else (255, 255, 255), 6)
        cv2.putText(ov, f"{eng} {x},{y}", (x, max(y - 12, 40)), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 255, 255), 5)
    Image.fromarray(ov).resize((W // 3, H // 3)).save(base + "_regions.jpg", quality=85)
    if a.mask_only:
        print("regions preview:", base + "_regions.jpg")
        return

    lama, _ = inpaint(img, mask, lama_model(), max_side=a.fill_res)
    final = lama.astype(np.float32)
    cdir, boxes, todo = base + "_codex", [], []
    for i, ((x, y, w, h), rm, eng) in enumerate(regs):
        if eng == "codex":
            x0, y0, x1, y1, size = context_box(x, y, w, h, W, H)
            todo.append((f"fill{i}", x0, y0, x1, y1, size, rm[y0:y1, x0:x1]))
        else:
            boxes.append(((max(x - 60, 0), max(y - 60, 0), min(x + w + 60, W), min(y + h + 60, H)), "lama"))
    with ThreadPoolExecutor(a.jobs) as ex:
        answers = list(ex.map(lambda t: run_codex(t[0], img[t[2]:t[4], t[1]:t[3]], t[6], t[5], cdir, a.what), todo))
    for (job, x0, y0, x1, y1, size, rm), ans in zip(todo, answers):
        if ans is None:
            boxes.append(((x0, y0, x1, y1), "codex FAILED -> LaMa"))
            continue
        bad = paste_codex(final, img, x0, y0, x1, y1, rm, ans)
        boxes.append(((x0, y0, x1, y1), f"codex{' MAGENTA LEFT ' + str(bad) if bad > 50 else ''}"))
        print(f"[{job}] pasted ({x0},{y0})-({x1},{y1}){'  WARNING magenta px ' + str(bad) if bad > 50 else ''}")
    final = final.round().clip(0, 255).astype(np.uint8)
    exif = None
    if not a.image.lower().endswith((".heic", ".heif")):
        ex = Image.open(a.image).getexif()
        ex[0x0112] = 1  # pixels are already upright
        exif = ex.tobytes()
    Image.fromarray(final).save(out, quality=95, subsampling=0, **({"exif": exif} if exif else {}))
    save_previews(img, final, mask, base)
    zoom_sheet(img, lama, final, boxes, base + "_zoom.jpg")
    print(f"-> {out}\ncheck: {base}_compare.jpg  {base}_zoom.jpg  (then run photo-reviewer)")


if __name__ == "__main__":
    main()
