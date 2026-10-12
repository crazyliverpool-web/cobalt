## ก่อนประกาศว่าไฟล์ "หาย" และก่อน rebuild ที่แพง

ก่อนสรุปว่า source/ไฟล์ "หาย/ไม่มีแล้ว" และก่อนเริ่มงานสร้างใหม่ที่ใช้เวลา/effort มาก
(ถอดเสียง, รัน pipeline, เขียนไฟล์ใหญ่ทับ) ต้องทำครบ 3 ข้อก่อน:

1. เช็ค /Volumes/ ที่ mount อยู่ทั้งหมด (`ls /Volumes/`) — คอร์สที่เรียนจบเก็บ archive ไว้ที่
   /Volumes/Acici Sanitsakul/studio-archive/
2. เช็คไฟล์ "ปลายทาง" ที่ถูกต้อง ไม่ใช่แค่ที่เดิม/ร่างดิบ — correction ของ learn-session
   อยู่ที่ lesson_notes.md เสมอ ไม่ใช่ session_N_structured.md หรือ NotebookLM fulltext
   (ห้ามตัดสินว่า "แก้แล้ว/ยังไม่แก้" จากร่างดิบ)
3. ถาม user ตรงๆ ว่ามี backup ที่ไหนไหม

ครบ 3 ข้อแล้วไม่เจอ ค่อย rebuild. Diff กับของเดิมก่อนเขียนทับ deliverable ที่มีอยู่เสมอ.

---

## เรียก LLM แบบ scripted/programmatic ในโปรเจกต์นี้

Script ใดๆ ใน `tools/*.py` (หรือที่คล้ายกัน) ที่ต้องเรียก LLM แบบอัตโนมัติ/เป็น batch —
ให้เรียก Anthropic API ตรงผ่าน `anthropic` SDK เสมอ **ห้าม shell out ไป `claude -p`**.

เหตุผล: `claude -p` คือ interactive agent harness ไม่ใช่ batch endpoint — เปราะกับ prompt
ใหญ่ผสมหลายส่วน (พังแบบ crash เงียบหรือ hang หลายชั่วโมงได้ทั้งคู่, ดู T21) และกลืน stderr
จน debug ไม่ได้. API ให้ error message จริง, นับ token ล่วงหน้าได้, deterministic กว่า.

---

## launchd LaunchAgent ทุกตัวในเครื่องนี้

**ต้องเรียก `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` ตรงๆ ห้ามมี
shell wrapper** (`/bin/zsh`, `/bin/sh`) — macOS TCC ไม่ให้ grant `kTCCServiceSystemPolicyDesktopFolder`
กับ `/bin/zsh` (มีแต่ python3.14/Terminal/claude-code) ดังนั้นถ้า launchd เรียก zsh ไปเปิดไฟล์ใต้
`~/Desktop` จะได้ `EPERM` → `can't open input file` → exit 127 เงียบๆ ทุกวันโดยไม่มี error ที่เห็นชัด
(เจอเคสจริงกับ youtube-digest bot, เงียบ 32 วันไม่มีใครรู้ — ดู `for-opus/questions.md` Q29)

ผลที่ตามมา:
1. **ต้องกำหนด `EnvironmentVariables` PATH เองใน plist เสมอ** — launchd ให้ default PATH แค่
   `/usr/bin:/bin:/usr/sbin:/sbin` ไม่มี `/opt/homebrew/bin` ทำให้ `yt-dlp`/`node`/binary อื่นๆ
   ที่ปกติมาจาก shell profile หาไม่เจอ
2. **ห้าม verify ด้วยการรันสคริปต์มือใน terminal เด็ดขาด** — Terminal.app/claude-code มี TCC
   grant ของตัวเองอยู่แล้ว รันมือจะ "ผ่าน" เสมอไม่ว่า launchd job จะพังจริงแค่ไหน (นี่คือสาเหตุที่
   youtube-digest ดูเหมือน "fix แล้ว" ตอน 27 ก.ค. ทั้งที่ไม่เคยรันผ่าน launchd สำเร็จเลย) —
   ต้อง verify ด้วย `launchctl kickstart -k gui/<uid>/<label>` แล้วเช็ค `last exit code` เท่านั้น
3. จุดเปราะที่เหลือ: วันอัป Python เป็นเวอร์ชันใหม่ (เช่น 3.15) → path เปลี่ยน → TCC grant หาย
   ต้องขอ grant ใหม่/อัป path ในทุก plist — `tools/digest_watchdog.py` (รันทุกวัน 09:00 ผ่าน
   `com.alonsi.digest-watchdog`) จะจับความเงียบนี้ได้ภายใน 36 ชม. แต่ควรเช็ค TCC grant เองด้วย
   ถ้ามีการอัป Python
4. **บอทที่ใช้เน็ตต้องเรียก `netwait.hold_awake()` + `netwait.wait_for_network(<hosts ของบอท>)` เป็นอย่างแรก**
   (`tools/netwait.py`). launchd รันงานที่พลาดตอน Mac หลับ "ทันทีที่ตื่น" — ซึ่งมักเป็น maintenance DarkWake 45 วิ
   ก่อน Wi-Fi ต่อ (เคสจริง PROSPECT 12 ต.ค. 2569: `net::ERR_INTERNET_DISCONNECTED`). `hold_awake()` spawn
   `caffeinate -i -s -w <pid>` เป็น**ลูก**ของ python (`-s` กันทุก sleep รวม Maintenance Sleep — ใช้ได้เฉพาะไฟ AC;
   Mac mini เครื่องนี้ AC ตลอด). **ห้ามใส่ `caffeinate` ใน ProgramArguments** — TCC จะนับ caffeinate เป็นตัวที่เปิด
   ~/Desktop แล้ว EPERM แบบเดียวกับ zsh wrapper
