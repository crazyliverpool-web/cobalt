# ThaiVI "ห้องร้อยคนร้อยหุ้น" digest — `com.alonsi.roikonroihoon-digest`

## ทำอะไร
ทุกเช้า ดึงหน้าล่าสุดของกระทู้หุ้นกลุ่ม รพ. ที่ติดตามใน board.thaivi.org (forum f=49) → เทียบกับที่เห็นครั้งก่อน
→ ให้ Claude (`claude-sonnet-5` ผ่าน API) สรุปโพสต์ใหม่ → สร้างหน้า Notion (รายละเอียด) → ส่ง LINE สั้นๆ พร้อมลิงก์ Notion.

## รันเมื่อไหร่
ทุกวัน 07:00. สคริปต์: `tools/roikonroihoon_digest.py`. log: `stock-research/thaivi/digest_launchd.log`.
heartbeat: `stock-research/thaivi/digest_state.json` (watchdog เตือนถ้าเก่ากว่า 36 ชม.)

## เช็คยังไง
- ทดสอบแบบไม่ส่งจริง: `python3 tools/roikonroihoon_digest.py --dry-run` (scrape + log อย่างเดียว ไม่เรียก Claude/Notion/LINE)
- verify ของจริง: `launchctl kickstart -k gui/$(id -u)/com.alonsi.roikonroihoon-digest` → ดู exit code + mtime ของ heartbeat

## อะไรมักพัง / หลอกตา
- **ต้องมี session login ThaiVI** (`stock-research/thaivi/thaivi_state.json`, Playwright). หมดอายุ → ดึงได้แต่หน้า login → อาจรายงาน "ไม่มีอะไรใหม่" ทุกวันทั้งที่จริงพัง (PHILOSOPHY §4.7: บอทเงียบต้องสงสัยก่อน). login ใหม่: `stock-research/thaivi/login_and_fetch.py`. มีบอทเตือนล่วงหน้า → `thaivi-relogin-reminder.md`
- `--dry-run` ยังเขียนไฟล์ session อยู่ เพราะ phpBB หมุน autologin key ทุกครั้งที่ใช้ — อย่าลบไฟล์นี้ทิ้ง
- ต้องมี `tools/.env`: `ANTHROPIC_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID` (+ Notion key ที่ `notion_helper` ใช้)
- รันมือใน terminal ผ่าน ≠ launchd ผ่าน (TCC) — ดู `guides/guardrails.md`
