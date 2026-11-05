# codex-cli — Codex เป็นลูกน้องของ Claude

| ไฟล์ | หน้าที่ |
|---|---|
| `AGENTS.md` | คำสั่งประจำของ Codex (เทียบเท่า CLAUDE.md) — Codex อ่านเองอัตโนมัติ |
| `run.sh` | ตัวที่ Claude ใช้สั่งงาน: สร้างโฟลเดอร์งาน → `codex exec` → พิมพ์รายงาน |
| `roles/*.md` | บทบาทเฉพาะงาน (`image`, `checker`, `extractor`, `reviewer`) เลือกด้วย `--role` และเติมเข้าคำสั่งเฉพาะงานนั้น |
| `rules/network.md` | กฎใช้เน็ต เติมอัตโนมัติเมื่อใช้ `--web` หรือ `--net` |
| `.codex/config.toml` | ตั้ง auto-compact แบบกระชับ และซ่อนการคิดระหว่างทำ |
| `outputs/<วันเวลา>-<ชื่องาน>/` | ผลงานแต่ละงาน + `task.txt` (คำสั่ง) + `report.txt` (รายงาน) + `codex.log` |
| `outputs/jobs.log` | ประวัติงานทั้งหมด |

## Claude ใช้ยังไง
```
codex-cli/run.sh mascot "Generate 3 character options ... save as mascot_a.png, mascot_b.png, mascot_c.png"
codex-cli/run.sh weather-vocab "Draw ... save as sunny.png" codex-cli/outputs/.../mascot_b.png   # แนบรูปอ้างอิง
```
หลังจากนั้น Claude ต้อง**เปิดดูทุกไฟล์ใน FILES เอง**ก่อนนำไปใช้ — ห้ามเชื่อรายงานของ Codex อย่างเดียว

## ผู้ใช้ใช้เอง
`cd codex-cli && codex` → ได้แชท Codex ที่โหลดกฎชุดเดียวกัน
