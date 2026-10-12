# ThaiVI "ห้องร้อยคนร้อยหุ้น" digest — `com.alonsi.roikonroihoon-digest`

## ทำอะไร
ทุกเช้า ดึงหน้าล่าสุดของกระทู้หุ้นกลุ่ม รพ. ที่ติดตามใน board.thaivi.org (forum f=49) → เทียบกับที่เห็นครั้งก่อน
→ ให้ Claude (`claude-sonnet-5` ผ่าน API) สรุปโพสต์ใหม่ → สร้างหน้า Notion (รายละเอียด) → ส่ง LINE สั้นๆ พร้อมลิงก์ Notion.

## รันเมื่อไหร่
ทุกวัน 07:00. สคริปต์: `tools/roikonroihoon_digest.py`. log: `stock-research/thaivi/digest_launchd.log`.
heartbeat: `stock-research/thaivi/digest_state.json` (watchdog เตือนถ้าเก่ากว่า 36 ชม.)

## เช็คยังไง
- `python3 -I tools/bots_doctor.py` — นอกจาก exit code/heartbeat ยังอ่าน `digest_state.json`: `_session_alert_sent`, ทุกกระทู้ `last_post_count` > 0 และ `last_checked` สด, วันหมดอายุ cookie autologin (`phpbb_thaivi_k`) ใน `thaivi_state.json`.
  exit code ของบอท: 2 = session หมด + auto-relogin ล้ม, 3 = login ได้แต่ parse 0 ทุกกระทู้,
  4 = มีโพสต์ใหม่แต่ Claude/Notion/LINE พัง (ไม่เขียน `digest_state.json` → รอบหน้าส่งใหม่; ส่ง LINE แจ้ง ERROR ถ้า LINE ยังใช้ได้),
  5 = crash กลางทาง (exception ที่ไม่ได้ดักไว้ เช่น โหลดหน้าเว็บ timeout หลัง retry) — traceback อยู่ใน `digest_log.txt` (บรรทัด `CRASH:`) + `digest_launchd.err`
- ทดสอบแบบไม่ส่งจริง: `python3 tools/roikonroihoon_digest.py --dry-run` (scrape + log อย่างเดียว ไม่เรียก Claude/Notion/LINE)
- verify ของจริง: `launchctl kickstart -k gui/$(id -u)/com.alonsi.roikonroihoon-digest` → ดู exit code + mtime ของ heartbeat

## อะไรมักพัง / หลอกตา
- **ต้องมี session login ThaiVI** (`stock-research/thaivi/thaivi_state.json`, Playwright). หมดอายุ → ดึงได้แต่หน้า login → อาจรายงาน "ไม่มีอะไรใหม่" ทุกวันทั้งที่จริงพัง (PHILOSOPHY §4.7: บอทเงียบต้องสงสัยก่อน). login ใหม่: `cd stock-research/thaivi && python3 login_and_fetch.py "https://board.thaivi.org/viewtopic.php?t=53828" /tmp/thaivi_login_test.md` (ต้องใส่ลิงก์กระทู้ + ไฟล์ปลายทางเสมอ; หน้าต่าง Chromium เปิดให้ login เอง). มีบอทเตือนล่วงหน้า → `thaivi-relogin-reminder.md`
- `--dry-run` ยังเขียนไฟล์ session อยู่ เพราะ phpBB หมุน autologin key ทุกครั้งที่ใช้ — อย่าลบไฟล์นี้ทิ้ง
- ต้องมี `tools/.env`: `ANTHROPIC_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID` (+ Notion key ที่ `notion_helper` ใช้)
- **heartbeat (`digest_state.json`) ถูกเขียนแม้ session หมด** (บันทึก `_session_alert_sent`/streak) → mtime สดไม่ได้แปลว่าดึงได้. ดูต่อกระทู้ `last_checked` (doctor ทำให้)
- **(แก้แล้ว 2026-10-11) โพสต์หายเมื่อสรุปพัง** — เดิม state ถูกบันทึกก่อนเรียก Claude; 10 ต.ค. 2569 Claude คืน response ไม่มี text block → `StopIteration` → โพสต์ใหม่ทั้ง 6 กระทู้ถูกนับว่าเห็นแล้วแต่ไม่เคยส่ง (วันนั้นเงียบ, วันถัดไป "ไม่มีโพสต์ใหม่").
  ตอนนี้: Claude ไม่คืนข้อความ/error → รอ 15 วิ ลองอีกครั้ง → ยังพัง = exit 4; Notion/LINE พังก็ exit 4. **`digest_state.json` เขียนเฉพาะหลังส่ง LINE สำเร็จ** (หรือวันไม่มีโพสต์ใหม่).
  ผลข้างเคียง: พังติดกันหลายวัน → heartbeat ไม่ขยับ → watchdog เตือนใน 36 ชม. (ตั้งใจ); LINE ล้มหลังสร้าง Notion แล้ว → รอบหน้าได้หน้า Notion ซ้ำ
- **(แก้แล้ว 2026-10-11) โหลดหน้า timeout = crash เงียบ** — เดิม `page.goto(..., wait_until="load")` รอ asset ภายนอกจนเกิน 30 วิ → `TimeoutError` หลุดออกไป → exit 1, ไม่มี LINE (10 และ 11 ต.ค. 2569).
  ตอนนี้: `wait_until="domcontentloaded"` (phpBB render ฝั่ง server, parser ไม่ต้องรอ asset), timeout 45 วิ, ลองซ้ำ 1 ครั้งหลัง 5 วิ.
  exception ที่หลุดถึงบนสุด → log traceback, ส่ง LINE "❌ … ERROR … รันพังกลางทาง: <ชนิด error>", exit 5, ไม่เขียน `digest_state.json`.
  **กันเตือนซ้ำ:** ส่ง LINE ครั้งเดียวต่อชนิด error — จำไว้ใน `stock-research/thaivi/digest_crash_alert.json` (แยกไฟล์ เพราะตัวดัก crash ห้ามเขียน `digest_state.json` ที่อาจถูกแก้ค้างในหน่วยความจำ).
  รอบที่ไม่ crash (exit 0/1/2/3/4) ลบไฟล์นี้ทิ้ง → crash ครั้งหน้าเตือนใหม่. crash ซ้ำชนิดเดิม = เงียบแต่ exit 5 (doctor FAIL, watchdog เตือนเมื่อ heartbeat เกิน 36 ชม.)
- **auto-relogin ได้ "การส่งค่าผิดพลาด. กรุณาลองใหม่อีกครั้ง"** = phpBB `FORM_INVALID`. `check_form_key()` ของ phpBB ปฏิเสธฟอร์มที่ส่งภายในวินาทีเดียวกับที่สร้าง token (กันบอท) — บอทเดิมโหลดหน้า login→กดส่งใน ~0.7 วิ (11 ต.ค. 2569).
  ตอนนี้รอ 2.5 วิ ก่อนกด login (`LOGIN_SUBMIT_DELAY_S`). **ยังไม่ได้ลองกับ login จริง** — ถ้ายังได้ข้อความเดิม อาจเป็นเรื่อง sid/cookie หรือ captcha แทน
- **DarkWake ไม่มีเน็ต (2026-10-12):** เริ่มรอบด้วย `netwait` — ถือ caffeinate (`-i -s`) ตลอดรอบ แล้วรอจน board.thaivi.org, api.line.me, api.anthropic.com, api.notion.com ต่อได้ (สูงสุด 10 นาที).
  log 1 บรรทัด: `network: ok (…)` / `network: up after Ns` / `network: never came up …` → ไปที่ crash handler: exit 5, LINE แจ้ง 1 ครั้ง (ถ้าส่งไม่ได้เพราะยังไม่มีเน็ต จะไม่ตั้ง flag → รอบหน้าเตือนใหม่), ไม่แตะ `digest_state.json`. doctor แสดง "waited Ns for network" หรือ FAIL
- **pagination: กระทู้ขึ้นหน้าใหม่ = โพสต์หาย** (ยังไม่แก้) — บอทดูแค่หน้าสุดท้าย; 12 ต.ค. 2569 BDMS 30 → 1 (หน้าเต็ม 30 แล้วขึ้นหน้าใหม่) ถูกรายงาน "no new posts" และอย่างน้อย 1 โพสต์ไม่ถูกสรุป
- plist มี `EnvironmentVariables` PATH แล้ว (2026-10-12)
- กู้ batch ที่หาย: ตั้ง `last_post_count` ทุกกระทู้ = 0 แล้ว kickstart → บอทถือว่าทั้งหน้าสุดท้ายเป็นโพสต์ใหม่ (ได้ batch เดิม + ที่ใหม่กว่า). ใช้ได้เฉพาะถ้ากระทู้ยังไม่ขึ้นหน้าใหม่ (บอทดูแค่หน้าสุดท้าย)
- รันมือใน terminal ผ่าน ≠ launchd ผ่าน (TCC) — ดู `guides/guardrails.md`
