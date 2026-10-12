# YouTube digest — `com.alonsi.youtube-digest`

## ทำอะไร
อ่านช่องที่เปิดใช้ใน `tools/youtube_digest/config/channels.json` → ดึงคลิปใหม่ผ่าน RSS สาธารณะ (ไม่ใช้ API key)
→ ข้ามคลิปที่เคยทำแล้ว (`state.json`) → ดึง transcript ไทยด้วย yt-dlp → Claude API สรุป
→ เพิ่มแถวใน Google Sheet → สร้างหน้า Notion → ส่ง LINE สั้นๆ พร้อมลิงก์ Notion → เขียน heartbeat.

## รันเมื่อไหร่
ทุกวัน 08:00. สคริปต์: `tools/youtube_digest/digest.py`. log: `tools/youtube_digest/logs/launchd.out.log`.
heartbeat: `tools/youtube_digest/data/last_run.json` (เขียนตอนจบรอบ)

## เช็คยังไง
- `python3 -I tools/bots_doctor.py` (exit code, heartbeat, RSS รอบล่าสุด, อายุ OAuth token, yt-dlp บน PATH)
- ทดสอบ: `python3 tools/youtube_digest/digest.py --dry-run`
- verify ของจริง: `launchctl kickstart -k gui/$(id -u)/com.alonsi.youtube-digest` → exit code + heartbeat

## อะไรมักพัง / หลอกตา
- **docstring บนสุดของ `digest.py` ยังเขียนว่าส่ง Gmail** — ของจริงส่ง LINE + Notion (และยังเขียน Google Sheet). เชื่อโค้ด ไม่ใช่ docstring
- **Google auth:** `sheets_client.py` ใช้ service account ถ้าตั้งไว้ (ไม่หมดอายุ) ไม่งั้นใช้ OAuth token `data/google_oauth_token.json` — ถ้า Google Cloud app อยู่ใน Testing mode token หมดใน 7 วัน (memory `project_daily_digest_automation`)
- **yt-dlp ต้องหาเจอใน PATH ของ launchd** (`/opt/homebrew/bin` ต้องอยู่ใน plist `EnvironmentVariables`) และต้องอัปเดตเป็นระยะ — YouTube เปลี่ยนรูปแบบบ่อย
- **(แก้แล้ว 2026-10-11) RSS ล้มทุกช่องเคยหลอกว่าเป็นวันเงียบ** — 10–11 ต.ค. 2569 ทั้ง 2 ช่อง 404 สองวันติด (probe จาก terminal ได้ 200 → น่าจะ YouTube RSS 404 เป็นพักๆ) แต่บอท log "No new videos. Exiting cleanly." + heartbeat `status: ok` + exit 0.
  ตอนนี้: 404/408/429/5xx/network error → รอ 20 วิ ลองอีกครั้งต่อช่อง; **ล้มทุกช่อง = `ERROR: RSS fetch failed for all N channels` + exit 2 + ไม่เขียน heartbeat** (doctor FAIL ทันที, watchdog เตือนถ้าเกิน 36 ชม.);
  ล้มบางช่อง = ทำต่อ + `WARN: partial RSS failure k/N` (doctor WARN). log นี้ไม่มี timestamp — doctor แบ่งรอบด้วยบรรทัดจบรอบ (`No new videos`/`Sent LINE digest`/`ERROR:`)
- **DarkWake ไม่มีเน็ต (2026-10-12):** เริ่มรอบด้วย `netwait` — ถือ caffeinate (`-i -s`) ตลอดรอบ แล้วรอจน www.youtube.com, api.line.me, api.anthropic.com, api.notion.com, sheets.googleapis.com ต่อได้ (สูงสุด 10 นาที).
  log 1 บรรทัด: `network: ok (…)` / `network: up after Ns` / `network: never came up …` → exit 2 ไม่เขียน heartbeat (เหมือน RSS ล้มทุกช่อง; บอทนี้ไม่มีช่อง LINE แจ้ง error — watchdog เตือนเมื่อ heartbeat เกิน 36 ชม.). doctor แสดง "waited Ns for network" หรือ FAIL
- OAuth ถูกใช้เฉพาะรอบที่มีคลิปใหม่ → token ตายเงียบได้หลายวันแล้วค่อย crash วันที่มีคลิป. doctor เตือนเมื่อ token file อายุ ≥5 วัน
- เคยเงียบ 32 วันโดยไม่มีใครรู้ (shell wrapper โดน TCC บล็อก, exit 127) → ต้นเหตุของ watchdog. รันมือผ่านเสมอ ห้ามใช้ยืนยัน
