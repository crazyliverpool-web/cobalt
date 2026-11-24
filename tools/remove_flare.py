#!/usr/bin/env python3
"""Remove straight lens-flare streaks (sun "light beams") from a photo.

Usage:
  python3 tools/remove_flare.py IMG.HEIC --line 4220,0,3800,3000          # -> IMG_retouched.jpg next to input
  python3 tools/remove_flare.py IMG.HEIC --line ... --line ... --patch-safe-below 2250
  python3 tools/remove_flare.py IMG.HEIC --dehaze 0.5                      # veiling glare only

--line x0,y0,x1,y1   streak axis in upright full-res pixels, from where it enters the frame (x0,y0)
                     to where it has faded out (x1,y1). If the sun is in frame, start just outside
                     the sun disk, or the sun gets painted over as "flare". Rough is fine: the centre is re-measured
                     along the streak. Repeatable (one per streak).
--half-width N       how far either side of the axis the glow reaches (default 700 px @ 24 MP).
--patch-safe-below Y below image row Y (treeline), ignore bright patches shorter than ~600 px along
                     the streak — real sunlit grass between dark trees, not flare.
--sky-core-only      only repaint sky near the streak core (use when the streak runs through the
                     sun's glow or past a peak and the sky goes blotchy/dark).
--dehaze S           0..1, lift veiling glare over the whole frame (dark-channel style).

How it works (learned 2026-10-10 on IMG_2611, see git history for the dead ends):
- A flare streak is light ADDED on top of the scene: img = bg*(1-a) + 255*a. On rock/trees/grass we
  estimate a and invert it, so the real texture under the streak survives (inpainting invents it).
- bg per streak row is fitted from pixels outside the core, separately for sky and ground: one fit
  across a ridge line mixes blue sky into rock and paints dark patches.
- Sky inside the streak is replaced by that smooth fit (sky has no texture to keep).
- The sky mask comes from texture (sky is smooth even under the flare); colour fails because the
  flare desaturates sky to rock-grey. The mask stops ~12 px short of ridges; those pixels are
  claimed back if they look like sky after correction.
Learned on the 2nd set (2026-10-11): coordinates are full-res pixels and iPhone files in one folder can
be 5712 or 4032 wide - check with `sips -g pixelWidth`. Two parallel streaks < ~400 px apart: use ONE
line down the middle with --half-width 700 --core 330 (two narrow lines leave both visible). A dark
blob in the sky next to a ridge = sky-mask hole; patch it with remove_people.py --extra.
Always look at the _compare.jpg and zoom into ridges and bright patches near the streak.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageOps


def load_upright(path):
    if path.lower().endswith((".heic", ".heif")):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        subprocess.run(["sips", "-s", "format", "png", path, "--out", tmp], check=True, capture_output=True)
        path = tmp
    return np.array(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))


def sky_mask(img):
    L = img.astype(np.float32).mean(2)
    tex = cv2.GaussianBlur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 2)), (0, 0), 6)
    smooth = (tex < 0.5).astype(np.uint8)
    n, lab = cv2.connectedComponents(smooth)
    top = lab[:16][smooth[:16] > 0]  # not row 0 alone: some files have a textured top edge (IMG_2631)
    if top.size == 0:
        return np.zeros(L.shape, bool)
    # every big smooth region touching the top edge: a contrail can split the sky in two
    areas = np.bincount(lab.ravel())
    keep = [k for k in np.unique(top) if areas[k] > 0.002 * L.size]
    sky = np.isin(lab, keep).astype(np.uint8)
    sky = cv2.morphologyEx(sky, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    # small holes enclosed by sky = the clipped streak core near the sun (sharp edges read as
    # texture); left as "ground" they come out as white blocks (IMG_2650)
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - sky)
    H, W = sky.shape
    for k in range(1, n):
        x, y, w, h, area = st[k]
        if area < 0.0005 * sky.size and x > 0 and x + w < W and y + h < H:
            sky[lab == k] = 1
    return sky > 0


def nblur(x, m, sx, sy):
    m = m.astype(np.float32)
    num = cv2.GaussianBlur(x * m[..., None], (0, 0), sigmaX=sx, sigmaY=sy)
    den = cv2.GaussianBlur(m, (0, 0), sigmaX=sx, sigmaY=sy)[..., None]
    return num / np.maximum(den, 1e-3)


def strip_maps(p0, p1, HW, offset=None):
    """Rows = steps along the streak axis, columns = -HW..HW across it."""
    d = np.array(p1, np.float32) - np.array(p0, np.float32)
    length = int(np.hypot(*d)); d /= np.hypot(*d)
    nrm = np.array([-d[1], d[0]], np.float32)
    t = np.arange(length, dtype=np.float32)
    s = np.arange(-HW, HW + 1, dtype=np.float32)
    off = np.zeros_like(t) if offset is None else offset
    mapx = p0[0] + t[:, None] * d[0] + (s[None, :] + off[:, None]) * nrm[0]
    mapy = p0[1] + t[:, None] * d[1] + (s[None, :] + off[:, None]) * nrm[1]
    return mapx.astype(np.float32), mapy.astype(np.float32), t, s


def refine_axis(img, p0, p1):
    """Measure the streak centre every 200 px along the rough axis; return a smooth offset curve."""
    mx, my, t, s = strip_maps(p0, p1, 500)
    L = cv2.remap(img.astype(np.float32).mean(2), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    pts = []
    H, W = img.shape[:2]
    for ti in range(40, len(t) - 40, 100):
        cx, cy = mx[ti, 500], my[ti, 500]
        if not (0 <= cx < W and 0 <= cy < H):  # strip starts off-frame; reflected pixels lie
            continue
        prof = cv2.GaussianBlur(L[ti - 20:ti + 20].mean(0)[None], (0, 0), 8)[0]
        prof = prof - cv2.GaussianBlur(prof[None], (0, 0), 120)[0]  # remove the broad sun glow
        base = np.median(prof)
        p = prof.argmax()
        if prof[p] - base < 6:
            continue
        half = np.where(prof > base + (prof[p] - base) / 2)[0]
        if half.max() - half.min() > 400:  # not a streak here (bright scene object)
            continue
        pts.append((ti, s[(half.min() + half.max()) // 2]))
    if len(pts) < 3:
        print(f"  axis {p0}->{p1}: could not measure centre, using the line as given", file=sys.stderr)
        return np.zeros_like(t)
    pts = np.array(pts, np.float32)
    for _ in range(2):  # drop outliers, refit
        c = np.polyfit(pts[:, 0], pts[:, 1], 2)
        r = np.abs(np.polyval(c, pts[:, 0]) - pts[:, 1])
        pts = pts[r <= max(3 * np.median(r), 15)] if len(pts) > 4 else pts
    c = np.polyfit(pts[:, 0], pts[:, 1], 2)
    print(f"  axis {p0}->{p1}: centre measured at {len(pts)} points", file=sys.stderr)
    return np.polyval(c, t).astype(np.float32)


def remove_streak(img, sky_img, p0, p1, HW, core, patch_safe_below, lead=0, sky_core_only=False):
    H, W, _ = img.shape
    im = img.astype(np.float32)
    off = refine_axis(img, p0, p1)
    mapx, mapy, t, s = strip_maps(p0, p1, HW, off)
    R = lambda a, i=cv2.INTER_LINEAR: cv2.remap(a, mapx, mapy, i, borderMode=cv2.BORDER_REFLECT)
    strip = R(im)
    sky = R(sky_img.astype(np.uint8), cv2.INTER_NEAREST).astype(bool)
    outer = np.abs(s) > core
    bg = np.full_like(strip, np.nan)
    for r in range(len(t)):
        row = strip[r]
        for m, deg in ((sky[r], 2), (~sky[r], 1)):
            sel = m & outer
            if not m.any() or sel.sum() < 30:
                continue
            if (sel & (s < 0)).sum() < 15 or (sel & (s > 0)).sum() < 15:
                deg = 0
            V = np.stack([s ** k for k in range(deg + 1)], 1)
            coef, *_ = np.linalg.lstsq(V[sel], row[sel], rcond=None)
            bg[r, m] = V[m] @ coef
    valid = ~np.isnan(bg[..., 0]); bg = np.nan_to_num(bg)
    margin = (cv2.dilate(sky.astype(np.uint8), np.ones((51, 51), np.uint8)) > 0) & ~sky
    gm = ~sky & ~margin & valid; sm = sky & valid
    taper_s = np.clip((HW - np.abs(s)) / 250, 0, 1)
    fade = 0.15 * (len(t) - lead)
    taper_t = np.clip((len(t) - t) / fade, 0, 1)
    if lead == 0:  # starts inside the frame (below the sun disk): fade in, don't cut
        taper_t *= np.clip(t / 300, 0, 1)
    T = (taper_s[None, :] * taper_t[:, None])[..., None]
    # ground: screen-blend inverse
    Ds = np.clip(nblur(strip - bg, gm, 6, 60), 0, None) * T
    a = np.clip(Ds / np.maximum(255.0 - (strip - Ds), 20), 0, 0.9)
    a = np.where(gm[..., None], a, nblur(a, gm, 15, 40))  # ridge margin: borrow from clean ground
    if patch_safe_below is not None:
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 601))
        ao = np.dstack([cv2.morphologyEx(a[..., c].astype(np.float32), cv2.MORPH_OPEN, k) for c in range(3)])
        ao = cv2.GaussianBlur(ao, (0, 0), sigmaX=4, sigmaY=80)
        wy = np.clip((mapy - patch_safe_below) / 250, 0, 1)[..., None]
        a = (1 - wy) * a + wy * ao
    # sky: smooth fit
    bgs = nblur(bg, sm, 3, 40)
    den = cv2.GaussianBlur(sm.astype(np.float32), (0, 0), sigmaX=3, sigmaY=40)
    bgs = np.where((den < 0.3)[..., None], nblur(bg, sm, 40, 120), bgs)
    Tsky = T
    if sky_core_only:  # leave far sky alone (sun glow there is real; one-sided fits smudge it)
        Tsky = T * np.clip((core + 150 - np.abs(s)) / 150, 0, 1)[None, :, None]
    delta = (bgs - strip) * Tsky
    corr = np.dstack([a, delta]).astype(np.float32)
    # back to image space by inverse mapping (scattering leaves holes/ripples on diagonal streaks)
    d = np.array(p1, np.float32) - np.array(p0, np.float32); d /= np.hypot(*d)
    nrm = np.array([-d[1], d[0]], np.float32)
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    ti = (gx - p0[0]) * d[0] + (gy - p0[1]) * d[1]
    si = (gx - p0[0]) * nrm[0] + (gy - p0[1]) * nrm[1] - np.interp(ti, t, off).astype(np.float32)
    acc = cv2.remap(corr, (si + HW).astype(np.float32), ti.astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = acc[..., :3]; delta = acc[..., 3:]
    ground = (im - 255 * a) / (1 - a)
    skyres = im + delta
    g8 = np.clip(ground, 0, 255)
    near = cv2.dilate(sky_img.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    sky2 = sky_img | (near & ((g8[..., 2] - g8[..., 0]) > 80))  # RGB: blue - red
    sky2 = cv2.morphologyEx(sky2.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    w = cv2.GaussianBlur(sky2.astype(np.float32), (0, 0), 1.5)[..., None]
    return np.clip(w * skyres + (1 - w) * ground, 0, 255).astype(np.uint8)


def dehaze(img, strength):
    """Dark-channel veil removal, blended by strength (0..1)."""
    f = img.astype(np.float32) / 255
    dark = cv2.erode(f.min(2), np.ones((31, 31), np.uint8))
    A = np.percentile(f.reshape(-1, 3)[dark.reshape(-1) >= np.percentile(dark, 99.9)], 90, axis=0)
    tr = 1 - 0.9 * cv2.erode((f / A).min(2), np.ones((31, 31), np.uint8))
    tr = cv2.ximgproc.guidedFilter(f, tr.astype(np.float32), 60, 1e-3) if hasattr(cv2, "ximgproc") \
        else cv2.GaussianBlur(tr, (0, 0), 20)
    J = (f - A) / np.maximum(tr, 0.35)[..., None] + A
    out = (1 - strength) * f + strength * np.clip(J, 0, 1)
    return (out * 255).round().astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("-o", "--out")
    ap.add_argument("--line", action="append", default=[], help="x0,y0,x1,y1")
    ap.add_argument("--half-width", type=int, default=700)
    ap.add_argument("--core", type=int, default=260)
    ap.add_argument("--patch-safe-below", type=float)
    ap.add_argument("--dehaze", type=float, default=0)
    ap.add_argument("--sky-core-only", action="store_true")
    args = ap.parse_args()
    out = args.out or os.path.splitext(args.image)[0] + "_retouched.jpg"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img = load_upright(args.image)
    orig = img.copy()
    sky = sky_mask(img)
    print(f"{img.shape[1]}x{img.shape[0]}  sky {sky.mean():.0%}  streaks {len(args.line)}", file=sys.stderr)
    for ln in args.line:
        x0, y0, x1, y1 = map(float, ln.split(","))
        on_edge = x0 <= 0 or y0 <= 0 or x0 >= img.shape[1] - 1 or y0 >= img.shape[0] - 1
        lead = 0
        if on_edge:  # start the strip outside the frame so a diagonal streak has no seam
            dx, dy = x1 - x0, y1 - y0; n = np.hypot(dx, dy); lead = args.half_width + 100
            x0, y0 = float(x0 - dx / n * lead), float(y0 - dy / n * lead)
        img = remove_streak(img, sky, (x0, y0), (x1, y1), args.half_width, args.core, args.patch_safe_below,
                            lead=lead, sky_core_only=args.sky_core_only)
    if args.dehaze > 0:
        img = dehaze(img, args.dehaze)
    Image.fromarray(img).save(out, quality=95)
    base = os.path.splitext(out)[0]
    H, W = img.shape[:2]; w = 1800; h = H * w // W
    cmp = Image.new("RGB", (2 * w + 20, h), "white")
    cmp.paste(Image.fromarray(orig).resize((w, h)), (0, 0)); cmp.paste(Image.fromarray(img).resize((w, h)), (w + 20, 0))
    cmp.save(base + "_compare.jpg", quality=88)
    print(f"-> {out}\ncheck: {base}_compare.jpg", file=sys.stderr)


if __name__ == "__main__":
    main()
