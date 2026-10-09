# PROSPECT occupancy watch — `com.alonsi.prospect-occupancy-watch`

## ทำอะไร
ทุกสัปดาห์ เช็ค set.or.th ว่า PROSPECT REIT มีไฟลิ่งรายไตรมาสใหม่ (MD&A / สรุป F45) หรือยัง.
เจอไตรมาสใหม่ → ส่ง LINE เตือนให้อัปเดตตาราง occupancy ใน `reports/PROSPECT_deepdive.html`.
**แจ้งเตือนอย่างเดียว ไม่แก้ HTML เอง** — พอได้ LINE ให้สั่ง Claude อัปเดต (ถาม NotebookLM notebook ของ PROSPECT หาตัวเลขไตรมาสใหม่).

## รันเมื่อไหร่
ทุกวันจันทร์ 07:30. สคริปต์: `tools/prospect_occupancy_watch.py`. log/heartbeat: `stock-research/prospect_occupancy_watch.log`
(append ทุกรอบ — watchdog เตือนถ้าเก่ากว่า 216 ชม. ≈ 9 วัน; ไฟล์ state json เปลี่ยนเฉพาะตอนเจอไฟลิ่งใหม่ จึงใช้เป็น heartbeat ไม่ได้)

## เช็คยังไง
`launchctl kickstart -k gui/$(id -u)/com.alonsi.prospect-occupancy-watch` → exit code + บรรทัดใหม่ใน log

## อะไรมักพัง / หลอกตา
- ไม่มี LINE มาหลายเดือนเป็นเรื่องปกติ (ไฟลิ่งออกไตรมาสละครั้ง) — ดู log ว่ายังรันทุกจันทร์ ไม่ใช่ดูว่ามี LINE ไหม
- ต้องมี `tools/.env`: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
- set.or.th เปลี่ยนโครงหน้าเว็บ → อาจหาไฟลิ่งไม่เจอแบบเงียบๆ. ถ้าไตรมาสใหม่ควรออกแล้ว (ราว 45 วันหลังปิดไตรมาส) แต่ไม่มีเตือน → เปิดหน้า SET เทียบเอง
