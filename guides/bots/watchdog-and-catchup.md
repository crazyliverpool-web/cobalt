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
- ดู `launchctl list | grep alonsi` และ log ทั้งสอง
- ทดสอบว่าเตือนได้จริง: แตะ heartbeat ให้เก่า (`touch -t <เวลาเก่า> <ไฟล์>`) แล้ว kickstart watchdog → ต้องได้ LINE. คืนค่า mtime หลังทดสอบ

## อะไรมักพัง / หลอกตา
- **ถ้า watchdog เองพัง จะไม่มีใครเตือน** — ไม่ได้รับ LINE จาก watchdog ไม่ได้แปลว่าทุกอย่างปกติ. เช็ค log ของ watchdog เป็นระยะ
- เพิ่มบอทใหม่แล้วลืมใส่ใน `HEARTBEATS` **และ** `JOBS` → บอทใหม่ไม่มีใครเฝ้า (สองไฟล์ต้องตรงกัน)
- ต้องมี `tools/.env` (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`) สำหรับ watchdog
