# ThaiVI re-login reminder — `com.alonsi.thaivi-relogin-reminder`

## ทำอะไร
ส่ง LINE เตือน (สคริปต์ `tools/line_reminder.py`, ข้อความอยู่ใน plist) **ครั้งเดียว** ว่า session login ThaiVI (ติ๊ก "จดจำฉัน" เมื่อ 26 ก.ค. 2569, อยู่ได้ ~1 ปี) ใกล้หมดอายุ
ให้เปิด Mac รัน `cd stock-research/thaivi && python3 login_and_fetch.py "https://board.thaivi.org/viewtopic.php?t=53828" /tmp/thaivi_login_test.md` (ต้องใส่ลิงก์กระทู้ + ไฟล์ปลายทางเสมอ; หน้าต่าง Chromium เปิดให้ login เอง) เพื่อ login ใหม่ ก่อนบอทหุ้น รพ. (`roikonroihoon-digest.md`) จะหยุดทำงาน.

## รันเมื่อไหร่
15 ก.ค. 2570 เวลา 07:05 (ข้อความอยู่ในตัว plist เอง). log: `stock-research/thaivi/relogin_reminder.log`.

## อะไรมักพัง / หลอกตา
- launchd ไม่รองรับ "Year" ใน `StartCalendarInterval` อย่างเป็นทางการ — ถ้า macOS ไม่สนช่อง Year มันอาจเตือนซ้ำทุกปีวันเดียวกัน หรือไม่เตือนเลย. **อย่าพึ่งตัวนี้ตัวเดียว**: ถ้า digest ThaiVI เริ่มรายงาน "ไม่มีอะไรใหม่" ติดกันหลายวัน ให้สงสัย session หมดก่อน
- หลัง login ใหม่ → อัปเดตวันที่ในข้อความ plist + วันที่เตือนครั้งถัดไป (อีก ~1 ปี) แล้ว `launchctl bootout` / `bootstrap` ใหม่
