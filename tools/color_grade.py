#!/usr/bin/env python3
"""Colour-grade a photo toward the "Geisleralm / Cinema delle Odle" postcard look the user likes
(reference shown 2026-10-11): yellow-green lit grass, deep green pines, clean blue sky, crisp
haze-free rock, warm wood, punchy contrast.

Usage:
  python3 tools/color_grade.py IMG.jpg [-o OUT] [--haze 0.35] [--green 1.0] [--contrast 1.0] [--vib 1.0]
  python3 tools/color_grade.py --dir FOLDER     # every *_retouched.jpg (else the HEIC) -> *_graded.jpg

Order matters: remove people / flare FIRST (remove_people.py, remove_flare.py), grade last.
Then run tools/photo_check.py --global and the photo-reviewer agent before delivering.

Limits: a backlit shot stays backlit - grading crisps shaded rock but cannot light it like the
front-lit reference; no clouds are added.
Gotcha (2026-10-11): never use a spatial dark-channel dehaze here (no guided filter on this Mac):
it mottled the sky, put halos on ridges and blocks on rock. Every step is per-pixel or global.
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))



def load(path):
    if path.lower().endswith((".heic", ".heif")):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        subprocess.run(["sips", "-s", "format", "png", path, "--out", tmp], check=True, capture_output=True)
        path = tmp
    return np.array(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))


def grade(rgb, haze=0.35, green=1.0, contrast=1.0, vib=1.0):
    if haze > 0:
        # global veil removal: lower each channel's black point (haze lifts the darks, mostly blue).
        # No spatial dark-channel map: without a guided filter it leaves halos along every ridge and
        # 31-px blocks on hazy rock (photo-reviewer FAIL on 11 photos, 2026-10-11).
        f = rgb.astype(np.float32)
        black = np.percentile(f.reshape(-1, 3), 0.5, axis=0)
        veil = haze * black
        x = np.clip((f - veil) / (1 - veil / 255), 0, 255).astype(np.uint8)
    else:
        x = rgb
    lab = cv2.cvtColor(x, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    hue = np.degrees(np.arctan2(b, a)) % 360
    chroma = np.hypot(a, b)
    # foliage/grass (hue ~70-160): lit grass -> yellow-green, dark pines stay deep green
    g = np.clip(1 - np.abs(hue - 115) / 45, 0, 1) * np.clip((chroma - 4) / 8, 0, 1)
    lit = np.clip((L - 70) / 60, 0, 1)
    a = a - green * g * (6 + 4 * lit)
    b = b + green * g * (14 * lit + 3)
    # warm wood / orange
    w = np.clip(1 - np.abs(hue - 60) / 25, 0, 1) * np.clip((chroma - 12) / 8, 0, 1)  # not grey rock
    a, b = a * (1 + 0.25 * w), b * (1 + 0.25 * w)
    # sky blue: a little deeper
    s = np.clip(1 - np.abs(hue - 285) / 30, 0, 1) * np.clip((L - 120) / 40, 0, 1)
    b = b * (1 + 0.2 * s)
    L = L - 3 * s
    # vibrance: lift muted colours more than saturated ones
    c = np.hypot(a, b)
    k = 1 + (0.35 * vib) * np.clip(1 - c / 60, 0, 1) * np.clip((c - 3) / 6, 0, 1)  # leave near-grey rock grey
    a, b = a * k, b * k
    # gentle S-curve, then open up shaded rock a little
    t = L / 255
    t = np.clip(t + 0.12 * contrast * (t - 0.5) * (1 - np.abs(2 * t - 1)) * 2, 0, 1)
    t = t + 0.06 * np.clip(1 - t / 0.45, 0, 1) * (t / 0.45)
    lab = np.dstack([t * 255, a + 128, b + 128])
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--dir")
    ap.add_argument("--haze", type=float, default=0.35)
    ap.add_argument("--green", type=float, default=1.0)
    ap.add_argument("--contrast", type=float, default=1.0)
    ap.add_argument("--vib", type=float, default=1.0)
    a = ap.parse_args()
    jobs = []
    if a.dir:
        for h in sorted(glob.glob(os.path.join(a.dir, "IMG_*.HEIC")) + glob.glob(os.path.join(a.dir, "IMG_*.heic"))):
            stem = os.path.splitext(h)[0]
            src = stem + "_retouched.jpg" if os.path.exists(stem + "_retouched.jpg") else h
            jobs.append((src, stem + "_graded.jpg"))
    elif a.image:
        jobs = [(a.image, a.out or os.path.splitext(a.image)[0].replace("_retouched", "") + "_graded.jpg")]
    else:
        sys.exit("give an image or --dir")
    for src, out in jobs:
        Image.fromarray(grade(load(src), a.haze, a.green, a.contrast, a.vib)).save(out, quality=95, subsampling=0)
        print(f"{os.path.basename(src)} -> {out}")


if __name__ == "__main__":
    main()
