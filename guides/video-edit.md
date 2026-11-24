# Video: colour grade / remove people

Installed 2026-10-11 (not yet used on a real clip; the first real job should update this file).

## Where things are
- venv: `~/.venvs/video` (`--system-site-packages`, reuses system torch 2.12 with MPS)
- SAM2 (people masks tracked across frames): `~/.local/share/studio-video/sam2`, weights
  `checkpoints/sam2.1_hiera_small.pt`, config `configs/sam2.1/sam2.1_hiera_s.yaml`, `device='mps'`
- ProPainter (video inpainting): `~/.local/share/studio-video/ProPainter`, weights in `weights/`
  `PYTORCH_ENABLE_MPS_FALLBACK=1 ~/.venvs/video/bin/python inference_propainter.py --video FRAMES_DIR_or_MP4 --mask MASK_DIR --output OUT --height H --width W`
  Smoke test: bundled bmx-trees (80 frames, 432x240) took ~75 s on MPS.

## Rules
- **No video on this Mac**: source and output clips live on `/Volumes/Acici Sanitsakul/studio-archive/media/`;
  extract frames / write outputs there too (scratch frames are deleted after the job).
- Grade: bake `tools/color_grade.py` into a 3D LUT with ONE fixed black point for the whole clip
  (per-frame percentiles flicker), apply with `ffmpeg -vf lut3d=...`.
- Remove people: SAM2 masks -> ProPainter. Do NOT run LaMa per frame (fills differ frame to frame -> shimmer).
  Works for a static/slow-pan camera and small passers-by; crowds and people close to the lens fail.
  Start with short clips (<=10 s) at reduced resolution.
- Verify before delivering, same rule as photos (CLAUDE.md): check stills from several frames + play the clip.
