# Opus ↔ Sonnet handoff — `todos.md`

ตั้งแต่ 2026-10-09 งานทั้งหมดอยู่ใน **`todos.md` ไฟล์เดียว** (แนวคิดจาก poteto/noodle: 1 งาน = ลำดับ stage, แต่ละ stage ระบุ model).
`for-opus/questions.md` และ `for-sonnet/tasks.md` = **ประวัติ + รายละเอียดยาว** — ไม่ต้องอ่านทั้งไฟล์ อ่านเฉพาะหัวข้อที่ `detail:` ชี้ไป.

## รูปแบบงาน 1 ข้อ
```
- [ ] **<ID> <ชื่องานสั้นๆ>**
      stages: design:opus → execute:sonnet → verify:script → reflect
      detail: for-opus/questions.md Q<n> · for-sonnet/tasks.md T<n>
```
- stage ที่เสร็จ ใส่ ✅ ต่อท้าย · งานรอผู้ใช้สั่ง ใส่ ⏸️ หน้าชื่อ · ปิดงาน → ย้ายไป `## Done` (เก็บล่าสุด ~10 ข้อ, ที่เก่ากว่าลบได้ เพราะประวัติอยู่ใน git)
- model ต่อ stage: **opus** วางแผน/ออกแบบ/ตัดสิน logic · **sonnet** ลงมือ/วิจัย · **haiku** งานกลไก · **script** ตรวจอัตโนมัติ (lint, kickstart) · **user** ผู้ใช้ทำ/ตัดสิน
- stage `verify` ต้องเป็นของที่พิสูจน์ได้ (สคริปต์ผ่าน, exit code, เทียบไฟล์) — `guides/principles.md` §5

## ถ้าเป็น Opus
1. อ่าน `todos.md` → ทำ stage ที่เป็น `opus` และยังไม่ ✅
2. งานออกแบบยาว → เขียนรายละเอียดเป็นหัวข้อใหม่ใน `for-opus/questions.md` แล้วใส่ `detail:` ชี้ไป (ไม่เขียนยาวใน todos.md)
3. ใส่ ✅ ที่ stage ที่ทำ; ถ้า stage ถัดไปเป็น sonnet → ไม่ต้องทำอะไรเพิ่ม Sonnet จะเห็นเอง

## ถ้าเป็น Sonnet
1. อ่าน `todos.md` → ทำ stage แรกที่ยังไม่ ✅ ซึ่งเป็น `sonnet` (ข้ามงาน ⏸️)
2. **ก่อนเขียน logic ใหม่ / สร้าง tool / เปลี่ยนวิธี หรือเจองานยาว (transcribe, batch, pipeline ทั้งชุด) ที่แผนไม่ได้เขียนไว้ → หยุด แล้วบอกผู้ใช้ให้สลับ Opus** (กฎผู้ใช้ 2026-06-23 — เคยเสีย 3 รอบกับ MLX). งานที่แผนเขียนไว้ชัดแล้ว → ทำได้เลย
3. ใส่ ✅ ที่ stage ที่ทำ; บันทึกผลรายละเอียดในหัวข้อ T<n> ของ `for-sonnet/tasks.md` ถ้ายาว

## เพิ่มงานใหม่
เพิ่มใต้ `## Active` ตามรูปแบบข้างบน. ID ใหม่ต่อเลขเดิม (Q31+, T33+) หรือใช้ชื่อสั้น (เช่น Q-noodle).
