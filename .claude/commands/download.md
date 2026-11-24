Download a video using cobalt or yt-dlp based on the URL and quality requested.

## Instructions

The user wants to download a video. Follow this routing logic:

**Step 1 — Check if cobalt API is running**
```bash
curl -s http://localhost:9000/ 2>/dev/null | python3 -m json.tool
```
If not running, start it:
```bash
pnpm --prefix /Users/alonsi/Desktop/studio/api start &
```
If it dies with `ERR_MODULE_NOT_FOUND` → dependencies were deleted: `pnpm install --frozen-lockfile` in `/Users/alonsi/Desktop/studio`, then start again.

**Step 2 — Route by content type**

- **Facebook** (reel / video / watch) → skip cobalt, go straight to the Facebook section below (cobalt returns `error.api.fetch.empty` on login-walled posts)
- **Facebook group / learning content** → yt-dlp and cobalt both fail; use the Playwright method in memory `feedback_facebook_group_download.md`
- YouTube member content → use yt-dlp with cookies
- 1080p or higher requested → use yt-dlp with cookies
- Everything else → use cobalt API

**Save location:** no video on this Mac (see CLAUDE.md) → save to
`/Volumes/Acici Sanitsakul/studio-archive/media/<platform>/` when the drive is mounted (`ls /Volumes/`).
Only fall back to `~/Desktop` if the drive is not mounted, and say so.

**Step 3 — Download**

cobalt (public videos):
```bash
TUNNEL=$(curl -s -X POST http://localhost:9000/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{\"url\": \"$ARGUMENTS\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")
curl -L "$TUNNEL" -o ~/Desktop/video.mp4
```

yt-dlp (member / 1080p):
```bash
yt-dlp --cookies /Users/alonsi/Desktop/studio/yt_cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio" \
  --merge-output-format mp4 \
  --postprocessor-args "ffmpeg:-c:a aac -b:a 192k" \
  -o "~/Desktop/%(title)s.%(ext)s" \
  "$ARGUMENTS"
```

Cookies file: `/Users/alonsi/Desktop/studio/yt_cookies.txt`

Facebook (uses the user's logged-in Chrome session — may trigger a one-time Keychain prompt):
```bash
D="/Volumes/Acici Sanitsakul/studio-archive/media/facebook"; mkdir -p "$D"
yt-dlp --cookies-from-browser chrome --no-update \
  -f "bv*+ba/b" --merge-output-format mp4 \
  --postprocessor-args "ffmpeg:-c:v copy -c:a aac -b:a 192k" \
  --sleep-requests 2 \
  -o "$D/%(uploader)s - %(id)s.%(ext)s" --print after_move:filepath \
  "$ARGUMENTS"
```
- `ERROR: ... Cannot parse data` → yt-dlp is outdated for Facebook's page format: `python3 -m pip install -U yt-dlp`, retry once.
- **Pace batch downloads** (`--sleep-requests`, one at a time): on 2026-09-10 Facebook force-logged-out the Chrome session after many rapid page loads, which blocked the rest of the course.
- Facebook usually serves **VP9** video, which QuickTime/iPhone won't play. Check with `ffprobe`; if `vp9`, offer to re-encode:
  `ffmpeg -i in.mp4 -c:v libx264 -preset medium -crf 25 -c:a copy -movflags +faststart out.mp4`
  (CRF 25 keeps talk/chart videos visually identical at ~1/4 the size of a 3 Mbps hardware encode). Compare one frame before overwriting.

**If ffmpeg itself fails** (`dyld: Library not loaded`) → Homebrew deps are out of sync: `brew upgrade ffmpeg`.
If brew refuses with "not writable" the user must run `sudo chown -R alonsi /opt/homebrew` themselves.
Stopgap until then: standalone ffmpeg from pip — `python3 -m pip install imageio-ffmpeg`, binary path from
`python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`.

**หมายเหตุ:**
- `--postprocessor-args "ffmpeg:-c:a aac"` บังคับให้ audio เป็น aac เสมอ เพราะ yt-dlp อาจเลือก opus/webm ซึ่ง QuickTime บน Mac ไม่รองรับ
- cobalt ใช้ IOS client (default) — ห้ามตั้ง `CUSTOM_INNERTUBE_CLIENT=WEB_EMBEDDED` ใน .env โดยไม่มี poToken เพราะ YouTube จะ block

After downloading, show the file path and size.
