# YouTube digest — `com.alonsi.youtube-digest`

## ทำอะไร
อ่านช่องที่เปิดใช้ใน `tools/youtube_digest/config/channels.json` → ดึงคลิปใหม่ผ่าน RSS สาธารณะ (ไม่ใช้ API key)
→ ข้ามคลิปที่เคยทำแล้ว (`state.json`) → ดึง transcript ไทยด้วย yt-dlp → Claude API สรุป
→ เพิ่มแถวใน Google Sheet → สร้างหน้า Notion → ส่ง LINE สั้นๆ พร้อมลิงก์ Notion → เขียน heartbeat.

## รันเมื่อไหร่
ทุกวัน 08:00. สคริปต์: `tools/youtube_digest/digest.py`. log: `tools/youtube_digest/logs/launchd.out.log`.
heartbeat: `tools/youtube_digest/data/last_run.json` (เขียนตอนจบรอบ)

## เช็คยังไง
- ทดสอบ: `python3 tools/youtube_digest/digest.py --dry-run`
- verify ของจริง: `launchctl kickstart -k gui/$(id -u)/com.alonsi.youtube-digest` → exit code + heartbeat

## อะไรมักพัง / หลอกตา
- **docstring บนสุดของ `digest.py` ยังเขียนว่าส่ง Gmail** — ของจริงส่ง LINE + Notion (และยังเขียน Google Sheet). เชื่อโค้ด ไม่ใช่ docstring
- **Google auth:** `sheets_client.py` ใช้ service account ถ้าตั้งไว้ (ไม่หมดอายุ) ไม่งั้นใช้ OAuth token `data/google_oauth_token.json` — ถ้า Google Cloud app อยู่ใน Testing mode token หมดใน 7 วัน (memory `project_daily_digest_automation`)
- **yt-dlp ต้องหาเจอใน PATH ของ launchd** (`/opt/homebrew/bin` ต้องอยู่ใน plist `EnvironmentVariables`) และต้องอัปเดตเป็นระยะ — YouTube เปลี่ยนรูปแบบบ่อย
- เคยเงียบ 32 วันโดยไม่มีใครรู้ (shell wrapper โดน TCC บล็อก, exit 127) → ต้นเหตุของ watchdog. รันมือผ่านเสมอ ห้ามใช้ยืนยัน
