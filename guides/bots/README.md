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
launchctl list | grep alonsi            # คอลัมน์ 2 = last exit code (0 = ปกติ)
for h in tools/youtube_digest/data/last_run.json stock-research/thaivi/digest_state.json \
         stock-research/prospect_occupancy_watch.log; do stat -f "%Sm  %N" -t "%F %H:%M" "$h"; done
```
heartbeat เก่ากว่าเกณฑ์ (รายวัน 36 ชม., PROSPECT 9 วัน) = บอทเงียบ แม้ exit code จะเป็น 0.

## เพิ่มบอทใหม่
1. plist เรียก python3.14 ตรง + `EnvironmentVariables` PATH (ดู guardrails)
2. บอทต้องเขียน heartbeat file ทุกรอบที่รันสำเร็จ
3. เพิ่มเข้า `HEARTBEATS` ใน `tools/digest_watchdog.py` **และ** `JOBS` ใน `tools/digest_catchup.py`
4. เขียนไฟล์คู่มือในโฟลเดอร์นี้ + เพิ่มแถวในตารางข้างบน
5. verify: `launchctl kickstart -k gui/$(id -u)/<label>` แล้วดู exit code + heartbeat
