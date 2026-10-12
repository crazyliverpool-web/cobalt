# คู่มือบอท launchd — 1 ไฟล์ต่อ 1 บอท

ต้นแบบ: poteto/verification-skill-example — อ่านเฉพาะไฟล์ของบอทที่เกี่ยว ไม่ต้องไล่ทั้งระบบ.
ทุกไฟล์ตอบ 4 คำถามเดิม: **ทำอะไร / รันเมื่อไหร่ / เช็คยังไง / อะไรมักพังหรือหลอกตา**.
กฎ launchd ร่วม (python3.14 ตรง, PATH ใน plist, verify ด้วย kickstart เท่านั้น): `guides/guardrails.md`.

| บอท | label | ไฟล์ |
|---|---|---|
| ThaiVI ร้อยคนร้อยหุ้น (หุ้น รพ.) | `com.alonsi.roikonroihoon-digest` | [roikonroihoon-digest.md](roikonroihoon-digest.md) |
| YouTube digest | `com.alonsi.youtube-digest` | [youtube-digest.md](youtube-digest.md) |
| PROSPECT occupancy watch | `com.alonsi.prospect-occupancy-watch` | [prospect-occupancy-watch.md](prospect-occupancy-watch.md) |
| Watchdog (แจ้งเตือนบอทเงียบ) | `com.alonsi.digest-watchdog` | [watchdog-and-catchup.md](watchdog-and-catchup.md) |
| Catch-up (รันชดเมื่อเปิดเครื่อง) | `com.alonsi.digest-catchup` | [watchdog-and-catchup.md](watchdog-and-catchup.md) |
| เตือน login ThaiVI ใหม่ (ครั้งเดียว) | `com.alonsi.thaivi-relogin-reminder` | [thaivi-relogin-reminder.md](thaivi-relogin-reminder.md) |

## เช็คทุกตัวในครั้งเดียว
```bash
python3 -I tools/bots_doctor.py     # 1 บรรทัด/บอท: PASS|WARN|FAIL <label> <เหตุผล>; exit 1 ถ้ามี FAIL
```
read-only (ไม่ kickstart, ไม่ส่ง LINE, ไม่แก้ state). เช็คต่อบอท: launchd โหลดอยู่ + `last exit code`,
heartbeat ความสด (รายวัน 36 ชม., PROSPECT 216 ชม. — exit 0 แต่ heartbeat เก่า = FAIL บอทเงียบ),
plist (python3.14 ตรง, script มีจริง, มี PATH), `.env` keys, yt-dlp บน PATH ของ plist, Traceback ใน stderr 72 ชม. ล่าสุด,
และ state ที่หลอกตา: ThaiVI parse ได้ทุกกระทู้ + cookie autologin, YouTube RSS ล้มทุกช่องแต่ log ว่า "No new videos",
Google OAuth (Testing mode ตาย ≤7 วันหลัง consent), PROSPECT หาไฟลิ่งบนหน้า SET ไม่เจอ.
WARN = ไปดูด้วยตา (ยังไม่ใช่พังแน่), FAIL = พัง/เงียบแน่นอน.
**doctor ไม่ได้พิสูจน์ว่า launchd รันผ่าน** — แค่อ่านผลรอบล่าสุด; verify หลังแก้ยังต้อง `kickstart` ตาม guardrails.

แบบมือ (ถ้า doctor เองพัง): `launchctl list | grep alonsi` (คอลัมน์ 2 = last exit code) + `stat` heartbeat ใน `tools/bot_registry.py`.

## เพิ่มบอทใหม่
1. plist เรียก python3.14 ตรง + `EnvironmentVariables` PATH (ดู guardrails)
2. บอทต้องเขียน heartbeat file ทุกรอบที่รันสำเร็จ
3. **ลงทะเบียนใน `BOTS` ของ `tools/bot_registry.py`** (label, script, heartbeat, `stale_hours`, `catchup_hours`,
   `watched`, `env_keys`, `path_bins`) — แหล่งเดียวที่ watchdog (`HEARTBEATS`), catch-up (`JOBS`) และ `bots_doctor.py` อ่าน.
   ไม่ลงทะเบียน = ไม่มีใครเฝ้า (doctor จะขึ้น WARN "plist not in tools/bot_registry.py"). ถ้าบอทมี state ที่บอก
   "ดึงไม่ได้" ต่างจาก "ไม่มีอะไรใหม่" ได้ → เพิ่ม `check_<bot>` ใน `bots_doctor.py`
4. เขียนไฟล์คู่มือในโฟลเดอร์นี้ + เพิ่มแถวในตารางข้างบน
5. verify: `launchctl kickstart -k gui/$(id -u)/<label>` แล้วรัน `python3 -I tools/bots_doctor.py` ต้องได้ PASS
