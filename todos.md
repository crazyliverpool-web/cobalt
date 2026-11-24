# todos — งานทั้งหมดของ studio (ไฟล์เดียว)

> **ทุก session อ่านไฟล์นี้ไฟล์เดียว** (แทน `for-opus/questions.md` + `for-sonnet/tasks.md` ซึ่งตอนนี้เป็นประวัติ/รายละเอียด อ่านเฉพาะเมื่อ `detail:` ชี้ไป).
> รูปแบบ + กติกา: `guides/opus-sonnet-handoff.md`. ย้ายมาระบบนี้ 2026-10-09 (แนวคิดจาก poteto/noodle).
>
> **Stage** = ขั้นตอนของงาน, ทำทีละขั้นตามลำดับ. `model` = ใครทำขั้นนั้น (opus วางแผน/ออกแบบ · sonnet ลงมือ/วิจัย · haiku งานกลไก · script = สคริปต์ตรวจ · user = ผู้ใช้ต้องทำ/ตัดสิน).
> ขั้นที่เสร็จใส่ ✅. งานรอผู้ใช้สั่ง ใส่ ⏸️ ที่หัวข้อ.

## Active

- [ ] **T32 youtube-digest: heartbeat ให้ซื่อสัตย์ + ลดผลกระทบ Google auth หมดอายุ**
      stages: design:opus ✅ → execute:sonnet → verify:script (`launchctl kickstart` + exit code) → reflect
      detail: `for-sonnet/tasks.md` T32 · `for-opus/questions.md` Q30 · คู่มือ `guides/bots/youtube-digest.md`

- [ ] ⏸️ **T33 QHBREIT: อัปเดตราคาหลังประกาศผล Q3** — ผู้ใช้: "ค่อยทำ" (2026-11-10) รอสั่ง
      stages: execute:sonnet (ดึงราคาปิดล่าสุดจาก qhpf.com หน้าแรก → รัน `reports/_drafts/QHBREIT_val_model.py` ที่ราคาใหม่: IRR, r โดยนัย, P/NAV → แก้ valuation.md §7 + atoms + deep dive ทุกจุดที่อ้าง 3.60) → verify:script (`tools/lint_deepdive.py`, grep 3.60 เหลือเฉพาะบริบท "ก่อนประกาศผล")
      detail: `reports/_drafts/QHBREIT_valuation.md` §7 · ถ้า NAV 30 ก.ย. 69 ออกแล้ว ให้แทนเงินสดสุทธิ 1,547.9 ด้วย

- [ ] ⏸️ **T29 เติม ROE / ROA / กำไรสะสม ใน deep dive เก่า 11 ตัว** — ผู้ใช้: "เดี๋ยวค่อยทำทีเดียว" รอสั่ง
      stages: design:opus ✅ → execute:sonnet (ทีละตัว, ถาม NotebookLM ของหุ้นนั้น) → lint:script (`tools/lint_deepdive.py` ต้อง PASS) → reflect
      detail: `for-sonnet/tasks.md` T29 · ผล lint 2026-10-09: ทั้ง 11 ตัว FAIL (ROE/ROA ขาด 10/11)

- [ ] ⏸️ **Q-noodle ที่เหลือ** — ช่วง 1–3 ทำแล้ว (ดูหัวข้อ Done)
      stages: เหลือแค่ทดลองใช้ `/how` กับงานจริง แล้ว `/reflect` ปรับ skill
      detail: `for-opus/questions.md` Q-noodle

## Done (ล่าสุด)

- [x] 2026-10-10 ผู้ใช้ยืนยันปิด: T7 (Master of Valuation อยู่ใน archive), T26–T28 (BCH deep dive เสร็จแล้ว), T2.6 (AI Leading Indicator ครบ), T25 (YouTube digest รันอยู่แล้ว)

- [x] 2026-10-09 Q-noodle ช่วง 3: `todos.md` (ไฟล์นี้), `/how`, hook rebuild `KNOWLEDGE_INDEX.md`, คู่มือบอท `guides/bots/`
- [x] 2026-10-09 Q-noodle ช่วง 2: `trendlongtun-brief` ฉบับเต็ม + Step 5c critique, `tools/lint_deepdive.py`, global skill → symlink
- [x] 2026-10-09 Q-noodle ช่วง 1: `/reflect` `/ruminate` `/meditate`, `guides/principles.md`, fixes จาก ruminate (archivist, download FB, Python SSL, `tools/remove_people.py`), เก็บ transcript 365 วัน

## Cancelled

- **บอทคลินิก Alonsi (เลิกใช้ 2026-09-02)**: Q8, T8 (Sheets backend), T9 (reset step), T10 (code-review fixes), T11 (n8n Pro), T12 (ยืนยันนัด), T13 (FB Messenger)
