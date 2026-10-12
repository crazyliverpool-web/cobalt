# PROSPECT occupancy watch — `com.alonsi.prospect-occupancy-watch`

## ทำอะไร
ทุกสัปดาห์ เช็ค set.or.th ว่า PROSPECT REIT มีไฟลิ่งรายไตรมาสใหม่ (MD&A / สรุป F45) หรือยัง.
เจอไตรมาสใหม่ → ส่ง LINE เตือนให้อัปเดตตาราง occupancy ใน `reports/PROSPECT_deepdive.html`.
**แจ้งเตือนอย่างเดียว ไม่แก้ HTML เอง** — พอได้ LINE ให้สั่ง Claude อัปเดต (ถาม NotebookLM notebook ของ PROSPECT หาตัวเลขไตรมาสใหม่).

plist มี `EnvironmentVariables` PATH แล้ว (เพิ่ม 12 ต.ค. 2569, bootout/bootstrap). verify ล่าสุด: kickstart 12 ต.ค. 2569 18:38 → exit 0, `No change. Latest period Q2/2569 (… 5 watched item(s) on page)`, doctor PASS.

## รันเมื่อไหร่
ทุกวันจันทร์ 07:30. สคริปต์: `tools/prospect_occupancy_watch.py`. log/heartbeat: `stock-research/prospect_occupancy_watch.log`
(append ทุกรอบ — watchdog เตือนถ้าเก่ากว่า 216 ชม. ≈ 9 วัน; ไฟล์ state json เปลี่ยนเฉพาะตอนเจอไฟลิ่งใหม่ จึงใช้เป็น heartbeat ไม่ได้)

## เช็คยังไง
- `python3 -I tools/bots_doctor.py` — อ่านบรรทัดผลลัพธ์สุดท้ายของ log (ข้ามบรรทัด LINE push/retry): `No change`/`New filing` = PASS, `No matching filing found` = WARN (นับกี่รอบติด),
  `fetch failed`/`CRASH`/`New-filing alert not delivered` = FAIL. exit code: 1 = fetch ล้มหลัง retry / ส่งเตือนไฟลิ่งใหม่ไม่ได้ / ไม่มี env, 5 = crash
`launchctl kickstart -k gui/$(id -u)/com.alonsi.prospect-occupancy-watch` → exit code + บรรทัดใหม่ใน log

## อะไรมักพัง / หลอกตา
- ไม่มี LINE มาหลายเดือนเป็นเรื่องปกติ (ไฟลิ่งออกไตรมาสละครั้ง) — ดู log ว่ายังรันทุกจันทร์ ไม่ใช่ดูว่ามี LINE ไหม
- ต้องมี `tools/.env`: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
- **(แก้แล้ว 2026-10-12) "No matching filing found" 21 ก.ย. + 5 ต.ค. 2569 = ไฟลิ่งเก่าหลุดจาก preview** (ยืนยันด้วย screenshot): แท็บข่าวแสดงแค่ 5 รายการล่าสุดต่อหมวด
  ("ข่าวบริษัท" / "ข่าวงบการเงิน") + ปุ่ม "ดูเพิ่มเติม" — MD&A Q2 (10 ส.ค.) ถูกข่าวเพิ่มทุน/F53-5 ปลาย ก.ย. ดันตกไป.
  ตอนนี้: อ่าน**ทั้งสองหมวด** และเทียบด้วย **งวด (ปี พ.ศ., ไตรมาส)** ไม่ใช่ title — `งบการเงินไตรมาสที่ N/YYYY`, `งบการเงินรายปี YYYY` (=Q4), MD&A/F45 (`ไตรมาสที่ N … YYYY`, ไม่มีไตรมาส = รายปี).
  หมวดงบการเงิน 5 รายการ ≈ 1 ปี จึงแทบไม่หลุด. state: `last_period` = `[2569, 2]` (migrate ครั้งเดียวจาก `last_title` → ไม่เตือนซ้ำ Q2). งวดใหม่กว่า → LINE ครั้งเดียว (รวมทุก item ของงวดนั้น).
  ตอนนี้ถ้ายังขึ้น "No matching" = น่าสงสัยจริง (ชื่อ/โครงหน้าเปลี่ยน) → doctor WARN
- **หน้าข่าว render ฝั่ง client (Nuxt)** — HTML ดิบไม่มีรายการข่าว ต้องรอ XHR. บอทเช็คว่ามีหัวข้อ "ข่าวงบการเงิน" ก่อน parse; ไม่มี = `fetch failed: … did not render` (ไม่ใช่ "No matching")
- **(แก้แล้ว 2026-10-12) DarkWake ไม่มีเน็ต** — Mac หลับ 07:25 พลาดรอบ 07:30 → launchd รันชดตอน maintenance DarkWake 07:41:19 (ตื่น 45 วิ) ก่อน Wi-Fi ต่อ → `net::ERR_INTERNET_DISCONNECTED` → exit 1 เงียบ.
  ตอนนี้: goto `domcontentloaded` + networkidle แบบไม่บังคับ (30 วิ), ลอง 3 ครั้ง ห่าง 90 วิ (ข้ามไป wake ถัดไปได้); ล้มหมด = log บรรทัดเดียว + LINE "❌ บอทเช็คไฟลิ่ง PROSPECT ERROR" + exit 1;
  exception อื่น = exit 5 + LINE; เจอไฟลิ่งใหม่แต่ส่ง LINE ไม่ได้ = ไม่บันทึก state (รอบหน้าเตือนใหม่) + exit 1. `--dry-run` = ไม่ส่ง LINE ไม่เขียน state (แต่ยังเขียน log = heartbeat)
- **log ล้มเหลวยังขยับ heartbeat** (log คือ heartbeat) → watchdog มองว่าสด. ดูผลรอบจริงด้วย `bots_doctor.py` (อ่านบรรทัดผลลัพธ์สุดท้าย)
- set.or.th อยู่หลัง Imperva/Incapsula — จาก IP บ้าน (12 ต.ค. 2569) ไม่โดน challenge, โหลด ~1–4 วิ
- set.or.th เปลี่ยนโครงหน้าเว็บ → อาจหาไฟลิ่งไม่เจอแบบเงียบๆ. ถ้าไตรมาสใหม่ควรออกแล้ว (ราว 45 วันหลังปิดไตรมาส) แต่ไม่มีเตือน → เปิดหน้า SET เทียบเอง
