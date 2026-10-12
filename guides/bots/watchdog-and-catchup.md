# Watchdog + Catch-up — `com.alonsi.digest-watchdog`, `com.alonsi.digest-catchup`

สองตัวนี้คุมบอทอื่น ใช้ heartbeat file ชุดเดียวกัน (ดูแค่ mtime ของไฟล์ ไม่ import โค้ดบอท).

| | Watchdog | Catch-up |
|---|---|---|
| สคริปต์ | `tools/digest_watchdog.py` | `tools/digest_catchup.py` |
| รันเมื่อไหร่ | ทุกวัน 09:00 (หลังบอทรายวันรันเสร็จ) | ตอนเปิดเครื่อง/login (`RunAtLoad`) |
| ทำอะไร | heartbeat เก่าเกินเกณฑ์ → **ส่ง LINE เตือน** | heartbeat เก่าเกินเกณฑ์ → **kickstart บอทนั้นให้รันชดเลย** |
| เกณฑ์ รายวัน / PROSPECT | 36 ชม. / 216 ชม. | 25 ชม. / 100 ชม. |
| log | `tools/digest_watchdog.out.log` | `tools/digest_catchup.out.log` |

ทำไมมี: youtube-digest เคยตายเงียบ 32 วัน (`for-opus/questions.md` Q29). Catch-up มีไว้เพราะ launchd ไม่รันงานที่พลาดตอน Mac **ปิดเครื่อง** (ถ้าแค่ sleep มันรันชดเอง).

## เช็คยังไง
- `python3 -I tools/bots_doctor.py` (watchdog: exit code + `digest_watchdog.out.log` สดภายใน 36 ชม.; catch-up: exit code)
- ทดสอบว่าเตือนได้จริง: แตะ heartbeat ให้เก่า (`touch -t <เวลาเก่า> <ไฟล์>`) แล้ว kickstart watchdog → ต้องได้ LINE. คืนค่า mtime หลังทดสอบ

## อะไรมักพัง / หลอกตา
- **ถ้า watchdog เองพัง จะไม่มีใครเตือน** — ไม่ได้รับ LINE จาก watchdog ไม่ได้แปลว่าทุกอย่างปกติ. เช็ค log ของ watchdog เป็นระยะ
- `HEARTBEATS` / `JOBS` ไม่ได้ประกาศในสองไฟล์นี้แล้ว — มาจาก `tools/bot_registry.py` (แหล่งเดียว ใช้ร่วมกับ `bots_doctor.py`, refactor 2026-10-11).
  เพิ่มบอทใหม่แล้วลืมลงทะเบียน → ไม่มีใครเฝ้า. watchdog/catchup เช็คแค่ mtime: บอทที่ "รันจบ exit 0 แต่ดึงข้อมูลไม่ได้"
  ยังเขียน heartbeat ปกติ → watchdog ไม่เห็น ต้องใช้ `python3 -I tools/bots_doctor.py`
- ต้องมี `tools/.env` (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`) สำหรับ watchdog
