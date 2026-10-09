# Questions for Opus

> Instructions: Read this file, answer or design solutions for each question, then update the status.
> If your answer requires Sonnet to execute something, append a task to `for-sonnet/tasks.md`.
> Context: `/Users/alonsi/Desktop/studio/knowledge/index.md` has the NotebookLM notebook ID.

---

## Q9 — ควร upgrade n8n Pro เพื่อใช้ Variables หรือ hardcode channel secret?
**Status:** done (Opus, 2026-07-01) — คำตอบด้านล่าง. Sonnet executes **T11** + อัปเดต C2 ใน T10.

**Context (สรุปสั้นๆ):**
- บอทคลินิก Alonsi LINE Bot รันบน n8n Cloud (csmileyala.app.n8n.cloud) แผนปัจจุบัน = Starter
- C1 เสร็จแล้ว: LINE access token ย้ายไป n8n Header Auth credential (เข้ารหัส, ไม่อยู่ใน JSON)
- C2 (Verify LINE Signature): code deploy แล้วแต่ยัง skip เพราะ `$env.LINE_CHANNEL_SECRET` ว่าง
- n8n Variables (วิธีที่ clean ที่สุด) = **Pro plan only** — user บอกไม่มีปัญหาเรื่อง cost
- ทางเลือกที่ไม่ต้อง upgrade: hardcode channel secret ตรงใน Code node

**ทางเลือกที่ประเมิน:**

| Option | วิธี | ข้อดี | ข้อเสีย |
|--------|------|-------|---------|
| A | Upgrade n8n Pro → ตั้ง Variable `LINE_CHANNEL_SECRET` | Clean, encrypted, ไม่อยู่ใน workflow JSON | ค่าใช้จ่ายรายเดือน ถ้าใช้แค่ตัวนี้ = overkill |
| B | Hardcode ใน Code node (ผ่าน n8n API) | ฟรี, ทำได้ทันที | secret อยู่ใน Code node string — ถ้า export workflow JSON → เห็นได้ |
| C | ใช้ n8n Expressions ดึงจาก Google Sheet | ไม่ต้อง upgrade | เพิ่ม latency + complexity, overkill มาก |
| D | ข้ามไป (skip C2 ตลอดกาล) | ไม่ต้องทำอะไร | webhook เปิดรับ forged events — fake bookings, เผา Gemini quota |

**สิ่งที่รู้เพิ่มเติม:**
- Webhook URL คือ `/webhook/alonsi-clinic-line` — path สั้น ไม่ใช่ UUID → คนเดาได้ง่ายกว่า UUID
- ปัจจุบัน failure rate = 45.5% (เห็นใน n8n Overview) — มีปัญหาอื่นด้วย
- user ready to pay ถ้าคุ้มค่า

**คำถาม:**
1. ระหว่าง Option A (Pro upgrade) กับ B (hardcode) อันไหนแนะนำสำหรับ production chatbot คลินิกจริง?
2. Pro plan n8n มี feature อื่นที่ช่วยงาน clinic bot นี้ได้บ้างไหม (เพื่อประเมินว่า upgrade คุ้มหรือเปล่า)?
3. failure rate 45.5% น่าเป็นห่วงไหม? root cause น่าจะเป็นอะไร (hint: C3 ยังไม่ได้แก้ + C4 ยังไม่ได้แก้)?
4. ลำดับความสำคัญ: ควรแก้ C2 (signature) หรือ C3 (Gemini error fallback) หรือ C4 (delete race) ก่อน?

### ANSWER (Opus, 2026-07-01)

**Q9.1 — Upgrade Pro (Option A) ชนะขาด. Hardcode (Option B) คือการทำผิดซ้ำที่เพิ่งแก้ไปกับ C1.**

Channel secret ไม่ใช่ config ธรรมดา — มันคือ **กุญแจ HMAC** ที่ C2 ใช้ verify signature. ถ้า secret หลุด = attacker ปลอม signature ที่ผ่าน verify ได้ → C2 ไร้ค่าทันที. ดังนั้น secret ตัวนี้ **ห้ามอยู่ใน workflow JSON** เด็ดขาด.

Option B เอา secret ไปฝังใน string ของ Code node → **export/commit workflow เมื่อไหร่ก็หลุดลง git** = ช่องรั่วตัวเดียวกับที่ C1 เพิ่งอุด (LINE token ที่หลุดลง git มาแล้ว). เราเพิ่งย้าย token **ออก** จาก JSON ผ่าน Header Auth credential แล้วจะเอา channel secret **กลับเข้า** JSON = ขัดหลักตัวเอง และเปิดคลาสบั๊ก "secret ใน git" อีกรอบ. "ฟรีแต่ผิด."

Option A เก็บ secret ไว้ใน n8n Variables — **encrypted at rest, ไม่ถูก export ใน workflow JSON**. cost ไม่ใช่ปัญหา + นี่ระบบคนไข้จริงที่พลาดเรื่อง secret มาแล้วหนึ่งครั้ง → อย่าพลาดซ้ำ. **แนะนำ A.** (Code node เข้าถึง variable ผ่าน `$vars.LINE_CHANNEL_SECRET` — จำไว้ตอนแก้ C2: ไม่ใช่ `$env` แล้ว).

> หมายเหตุ: ต่อให้ยังไม่ upgrade วันนี้ วิธี "ฟรีที่ยังพอรับได้" คือใช้ Cloud env var — แต่ Q8 ยืนยันแล้วว่า n8n Cloud ตั้ง custom env var ตามแพลน/จำกัด. Variables คือทางเนทีฟของ Cloud และเป็น Pro. เมื่อ cost ไม่ติด → upgrade ตรงๆ ดีกว่าดิ้นหาทางฟรี.

**Q9.2 — Pro คุ้ม "เกินกว่า" แค่ Variables — มี feature ที่แก้ปัญหา operational ของบอทนี้โดยตรง:**

| Pro feature | ช่วยบอทคลินิกยังไง |
|---|---|
| **Variables** | เหตุผลตั้งต้น + เก็บ admin userId / price config / (อนาคต) branch config รวมศูนย์ที่เดียว (ตรงกับ Q8.4 multi-branch) |
| **Execution data retention ยาวขึ้น + search/filter** | 🔑 ตัวจริงที่ต้องมีตอนนี้ — Starter เก็บ execution history สั้น. ต้องใช้ค้นว่า execution ไหน fail และ **ทำไม** เพื่อไล่ 45.5% failure. ระบบ production ต้อง debug ย้อนหลังได้ |
| **Insights / dashboard** | ดู failure rate เป็น trend ว่าแก้แล้วดีขึ้นจริงไหม |
| **Concurrency สูงขึ้น** | รับ burst ข้อความคนไข้พร้อมกันได้ดีขึ้น (ไม่ได้แก้ C4 race แต่ลด queue backpressure) |
| **Workflow history / versioning ยาวขึ้น** | แก้บอท live แล้วพัง → rollback ได้ ปลอดภัยกับระบบที่คนไข้ใช้อยู่จริง |
| **Active workflows / executions/เดือน เพิ่ม** | headroom เผื่อโต |

สรุป: **upgrade คุ้ม** ไม่ใช่เพราะ Variables อย่างเดียว แต่เพราะ execution retention+search (ไว้ debug 45%) กับ versioning (แก้ live อย่างปลอดภัย) เป็นของที่ production bot ควรมี. (ชื่อ/ขอบเขต feature ตาม tier อาจขยับ — ให้ verify หน้า pricing n8n ตอนกดจริง แต่ทิศทางคือ Pro เติมของที่จำเป็นพอดี.)

**Q9.3 — 45.5% failure = น่าเป็นห่วงมาก แต่ต้อง segment ก่อนตกใจ. Root cause หลักน่าจะ M1 มากกว่า C3/C4.**

เกือบครึ่งของ execution จบด้วย error. แต่ "failure" ใน n8n Overview นับ execution ที่ status=error — ซึ่งรวม event ขยะด้วย. สาเหตุเรียงตามน้ำหนักที่คาด:
1. 🥇 **M1 (skip filter พัง — expression ขาด `=`)** — น่าจะเป็นตัวใหญ่สุด. LINE ยิง webhook ที่ไม่ใช่ message เยอะมาก (follow/unfollow/postback/delivery). พอ skip ไม่เคยทำงาน → ทุก event พวกนี้ทะลุเข้า Read State/Gemini ด้วย `userId` ว่าง → crash downstream ทุกตัว. อธิบายได้ว่าทำไม failure ค้างที่ ~ครึ่งอย่างสม่ำเสมอ ไม่ขึ้นกับสุขภาพ Gemini.
2. 🥈 **C3 (Gemini ไม่มี error branch)** — Gemini timeout/quota/500 เมื่อไหร่ → execution error + **คนไข้ไม่ได้ reply**. ตัวนี้คือ failure ที่กระทบคนไข้จริง.
3. 🥉 **C4 (delete by stale row_number)** — ลบแถวที่ไม่มี/ผิด → throw → error. ความถี่ต่ำกว่า (คลินิกเดียว concurrency น้อย) แต่รุนแรงตอนโดน.

> C2 ไม่ใช่ตัวทำ failure — ตอนนี้ signature check ปล่อยผ่าน (secret ว่าง) จึงไม่ throw. มันเป็น "รูความปลอดภัย" ไม่ใช่ "ตัวทำ error rate".

**สิ่งที่ต้องทำก่อนสรุป:** ใช้ execution search (นี่แหละเหตุผล Q9.2) ดูว่า 45% ที่ fail **เป็น event ชนิดไหน** — ถ้าเป็น follow/unfollow/non-message ล้วน → กระทบคนไข้น้อยกว่าตัวเลข (M1 fix ตัวเดียวตัวเลขจะดิ่ง). ถ้ามี booking message จริงปนอยู่ในนั้น = ฉุกเฉิน (C3). ไม่ว่าทางไหน fix คือ **M1 ก่อน แล้ว C3**.

**Q9.4 — อย่ามองแค่ C2/C3/C4 — M1 คือของถูกสุด+ผลมากสุด ต้องมาก่อน. ลำดับที่แนะนำ:**

1. **Upgrade Pro + สร้าง Variable `LINE_CHANNEL_SECRET` เดี๋ยวนี้** (5 นาที) — ปลด block C2 **และ** เปิด execution-search ไว้ diagnose 45%. ทำก่อนเพราะมันปลดล็อกทั้งสองงาน.
2. **M1** (เติม `=` ตัวเดียว) — เกือบฟรี, น่าจะฆ่า failure rate ไปก้อนใหญ่ทันที, หยุด event ขยะเผา Gemini. ของถูกที่สุด ผลชัดที่สุด → **มาก่อน C2/C3/C4 เสมอ**.
3. **C3** (Gemini fallback) — กันคนไข้เจอบอทเงียบ. นี่คือ active patient-harm ที่เกิดอยู่ตอนนี้.
4. **C2** (flip signature ให้ reject จริง) — ตอนนี้ unblocked แล้วเพราะมี Variable. ปิดรู forgery. (path webhook เดาง่าย ยิ่งควรปิด แต่ยังไม่มีหลักฐานโดน exploit → จัดหลัง reliability ที่กำลังเจ็บอยู่จริง).
5. **C4** (delete by `userId` ไม่ใช่ row index) — กัน data corruption.

**เหตุผลที่สลับ C2 ลงมาหลัง M1/C3** (ต่างจากลำดับ security-first ใน Q8): บอท live กำลัง fail ~ครึ่ง = คนไข้จริงอาจไม่ได้รับ reply **ตอนนี้** = harm ที่เกิดแล้ว. C2 เป็นความเสี่ยงเชิงทฤษฎี (ยังไม่เห็นการโจมตี) และเพิ่ง unblocked. เอา reliability ที่เลือดออกอยู่ก่อน แล้วปิด security ต่อทันที (C2 เป็นแค่การ flip เมื่อ Variable พร้อม). แต่ M1 ต้องมาก่อนทุกอย่างเพราะมันคือ one-char fix ที่คืน failure rate มากที่สุด.

**สรุปลำดับ:** `Pro+Variable → M1 → C3 → C2 → C4` (C4 ยังตามด้วย M3/M4 ใน T10 ตามเดิม).

---

## Q1 — Query Template Design for research-idea pipeline
**Status:** UNBLOCKED 2026-06-23 (all 5 transcripts now in the notebook). Ready to do — see T2.6 in for-sonnet/tasks.md. Was: waiting for transcripts.

**Context:**
- NotebookLM notebook "AI Leading Indicator" (ID: `70025843-85b8-44dc-bd15-f249a11aa360`) currently has 4 PDF slides
- 5 transcripts will be added once Whisper finishes (~today)
- The course teaches stock analysis using AI (Claude, ChatGPT, Gemini) + leading indicators
- Instructor: Alongkot Manorungrueangrat (4-day course, Thai language)
- The existing `research-idea` skill (at `~/.claude/skills/research-idea/SKILL.md`) has a Query Agent step that asks NotebookLM questions

**Question:**
Once transcripts are in NotebookLM, what specific questions should the Query Agent ask the "AI Leading Indicator" notebook when researching a stock? Design 5–8 reusable query templates that extract the instructor's framework (leading indicators to watch, story vs number analysis, red flags, etc.) and apply them to any stock under research.

---

## Q2 — Synthesize investment ai + stock-research → studio
**Status:** done — see answer below. Architecture recommendation written; awaiting user approval before Sonnet restructures anything. Transcription-fix task written to for-sonnet/tasks.md.

### ANSWER (Opus, 2026-06-22)

**Core insight: these are not 3 competing systems — they are 3 different LAYERS.**

| System | What it really is | Verdict |
|--------|-------------------|---------|
| `stock-research` (Claudy, 6 agents) | The **RESEARCH** engine: idea → query → synthesize → critique → fact-check → archive. Produces a *fact-checked research doc*. Makes NO decision. | This == the `research-idea` skill (duplicate). |
| `investment ai` (Investment OS) | The **DECISION** engine: 10 investor personas (Buffett/Graham/Munger/Lynch/Fisher/Damodaran/Kahneman/Marks/Dalio/Greenblatt) → Berkshire Committee → Buy/Watchlist/Avoid + portfolio/journal/memory. | Heavy; its unique asset is the *committee + decision discipline*. |
| `studio` + AI Leading Indicator | The **METHODOLOGY** source (how to research using AI + leading indicators) + the media/download + NotebookLM + Opus/Sonnet handoff infra. | Natural HUB. |

They stack: **methodology (studio) → research (6-agent) → decision (committee)**. The 6-agent pipeline's output is literally the *input* to the Berkshire Committee. No real overlap in function — only overlap in plumbing (both have a Query→NotebookLM step + a `knowledge/index.md`).

**Recommendation: DO NOT merge into one mega-system. Make `studio` the hub; harvest the best parts of the other two into it; retire the other two to archives.**

**Q2.1 — Overlap/diverge:** Overlap is only infrastructure (NotebookLM query, knowledge index, "no hallucination / cite sources" rules). Function diverges cleanly (research vs decide vs teach). → Keep one pipeline, one knowledge base, add a decision layer.

**Q2.2 — What to port from `investment ai`:**
- **Berkshire Committee → YES (highest value).** Runs AFTER the 6-agent research pipeline as the decision layer. Clean separation: 6 agents produce the doc, Committee makes the call.
- **Decision Journal → YES.** Lightweight, high value for reviewing past calls honestly.
- **Investment Memory → PARTIAL.** studio already has `.claude` memory + stock-research has `knowledge/insights/*_atoms.md`. Do NOT create a third memory. Consolidate into ONE `knowledge/insights/`.
- **AutoLog → OPTIONAL/LIGHT.** studio already has retrospectives + Opus/Sonnet handoff logs. Only add a trimmed version if the user runs many sessions.
- **10 persona agents → DEFER to user.** They are investment ai's depth but heavy to port all. Option A: keep them living in `investment ai`, call it for deep dives. Option B: port a single condensed "panel" prompt. (User decision.)
- **Notion integration → SKIP** unless user explicitly wants it (NotebookLM is already the hub).

**Q2.3 — Methodology connection (the important one):** YES — the AI Leading Indicator course becomes the **methodological backbone**. The "AI Leading Indicator" NotebookLM notebook is consulted by **Minnie** (idea framing) and **Reese** (synthesis): "what leading indicators would the instructor watch for *this* type of business? how does he separate story vs numbers? what are his red flags?" → This is exactly what Q1's query templates operationalize. So Q1 and Q3 are the same work: the course's framework is injected into the research pipeline via NotebookLM queries.

**Q2.4 — Unified architecture:**
```
studio/  (HUB — single working environment going forward)
├── (media/download infra — already here)
├── methodology → NotebookLM "AI Leading Indicator" (the HOW)
├── research pipeline = research-idea skill  (Minnie→Query→Reese→Chris→Vera→Indy)
├── decision layer   = Berkshire Committee (ported)   ← runs after pipeline
├── knowledge/       = ONE knowledge base (index, insights/atoms, retrospectives)
│        └── per-stock NotebookLM notebooks (BDMS exists; new stocks added here)
├── reports/         = research docs + committee decisions + journals
└── for-opus / for-sonnet  (handoff)
```
`investment ai` and `stock-research` become **source archives** — harvest, then freeze. Migrate the existing BDMS notebook + atoms + research from stock-research into studio's knowledge base so nothing is lost.

**Decisions that need USER approval before Sonnet executes:**
1. Approve "studio = hub, retire the other two to archive"? (vs keep 3 separate)
2. Port the 10 persona agents, or keep them only in `investment ai`?
3. Include AutoLog, or rely on existing retrospectives/handoff logs?

### REFINED (user clarified 2026-06-22): "don't port everything — recommend which agents/workflows fit my CURRENT situation"

User's current situation: a value investor LEARNING to research stocks with AI + leading indicators, NotebookLM as hub, wants lean not bloated. Note: the 10 personas (Buffett/Graham/…) listed in INVESTMENT_OS_MASTER do NOT exist as files — only 6 agent files exist (00 Discovery, 01 Master, 14 Committee, 15 Memory, 16 NotebookLM Pub, 17 AutoLog). So "porting 10 personas" is moot.

**Curated pick — adopt only these 4, in value order:**

| # | Adopt | From | Why it fits NOW | Overhead |
|---|-------|------|-----------------|----------|
| 1 | **Minnie's Question Playbook** (adapt + extend) | stock-research | THE keystone. Tested NotebookLM querying technique (ask 1 thing at a time, always state year, fact vs sentiment, name the document to force citation). Directly connects the AI Leading Indicator course → research pipeline. Generalize the hospital-only template + add a "leading indicator" question set from the course = this IS Q1. | Low |
| 2 | **Company Discovery** (pre-step) | investment ai #00 | Pure value-investing discipline: understand the business in plain language BEFORE touching numbers ("if you can't explain it simply, don't invest"). Perfect for a learner. Runs before Minnie. | Low |
| 3 | **Decision Journal** (lightweight standalone) | investment ai #14/MASTER | Most underrated value habit: record WHY you decided, what would prove the thesis WRONG, and the review date. Lets you learn from past calls. Adopt as a simple template even without the full committee. | Low |
| 4 | **Simplified Berkshire Committee** (framework only) | investment ai #14 | Honest final-call discipline: composite quality score, valuation-overlay table, governance/macro/bias OVERRIDE rules, conviction scale. Adopt the *framework* WITHOUT requiring 10 persona runs (they don't exist). The "make a defensible call" layer. | Medium — add after pipeline is solid |

**Keep as-is:** the 6-agent `research-idea` pipeline (the spine — already global, already works).

**Skip / defer (overhead > value right now):**
- Investment Memory #15 (14-section template too heavy — `knowledge/insights/*_atoms.md` via Indy already captures durable knowledge)
- AutoLog #17 (Opus/Sonnet handoff + retrospectives already cover the trail)
- NotebookLM Publisher #16 (user adds sources directly via CLI/skill)
- Notion integration (NotebookLM is the hub)
- Portfolio / Monitoring / Watchlist layers (useful when actively holding, not while learning)

**The throughline (the loop to build):**
`Understand business (Discovery) → Ask good questions (Minnie playbook + course framework) → Research (6-agent pipeline) → Decide honestly (simplified Committee) → Journal the decision (learn from it)`
A complete value-investing loop, lean, that also teaches as it runs. Everything else stays in the archives until a concrete need appears.

**Context:**
Two existing investment research systems were found on this machine:

**`/Users/alonsi/Desktop/investment ai`** — Investment OS (heavier, more structured):
- Agents: Company Discovery, Master Workflow, Berkshire Committee (final decision), Investment Memory, NotebookLM Publisher, AutoLog
- Post-analysis outputs: report → decision journal → investment memory → watchlist → NotebookLM source → AutoLog
- Has Notion integration
- Has Thai stocks support

**`/Users/alonsi/Desktop/stock-research`** — Orchestra Model "Claudy" (lighter, CLI-focused):
- 6-agent pipeline: Minnie → Query → Reese → Chris → Vera → Indy (same as `~/.claude/skills/research-idea/SKILL.md`)
- Knowledge base: profile, watchlist, thesis, atoms, retrospectives
- NotebookLM notebook: BDMS.BK (`05feefc2-2e82-4091-9c24-a6578e4d8ba0`)
- Has BDMS research, atoms, and retrospectives already

**`/Users/alonsi/Desktop/studio`** — Current working project:
- AI Leading Indicator course (4 videos + 4 PDFs, transcripts pending)
- NotebookLM notebook: "AI Leading Indicator" (`70025843-85b8-44dc-bd15-f249a11aa360`)
- Has `research-idea` skill available globally
- Has `knowledge/index.md` and `reports/` directories (just created)

**Questions:**
1. Where do these three systems overlap and where do they diverge? Should they merge or stay separate?
2. What is worth porting from `investment ai` to studio — specifically: Berkshire Committee Agent, AutoLog, Decision Journal, Investment Memory?
3. How should the AI Leading Indicator course knowledge connect with the research pipeline? (The course teaches HOW to research stocks — can it serve as the methodological backbone for Query Agent?)
4. Recommend a unified architecture: one system, or three that reference each other?

If Sonnet needs to execute any setup work, write tasks to `for-sonnet/tasks.md`.

---

---

## Q3 — Video-to-Knowledge Pipeline Design
**Status:** design done + pilot reviewed by Opus 2026-06-23. Pilot CONTENT approved (6 quotes verified present in transcript, chapters clean & in order). ONE defect found: Haiku's `[Slide p.N]` ranges drift ±3 pp (estimated, not anchored). Fix specified as T4 Step 1b (deterministic page re-anchoring by header match). Awaiting Sonnet to add Step 1b → re-run pilot → user approval → batch.

**Context:**
User wants to build a full pipeline that goes beyond plain transcript. The target architecture:
```
วิดีโอต้นฉบับ
  → FFmpeg แยกเสียง
  → Whisper ถอดเสียง                     ← already done (vad_transcribe.py)
  → ตรวจจับช่วงเปลี่ยนสไลด์ + แคปภาพ  ← NEW
  → AI รวม Transcript + สไลด์           ← NEW
  → สร้างสรุปแยกเป็นรายบท              ← NEW
  → นำเข้า NotebookLM                   ← already done
  → ใช้ AI สอน ถามตอบ ออกข้อสอบ        ← already done
```

**Known constraints:**
- Source videos = Facebook Live recordings (instructor + screen share mix; may not be slides-only)
- We already have PDFs for each session (AI Leading Indicator 1-4.pdf) — these are the actual slide decks
- Transcripts already exist and are in NotebookLM (text-only, no structure/chapters right now)
- Tools available: FFmpeg, Python, Claude API (vision), mlx-whisper, silero-vad

**Sonnet's assessment:**
- Steps 4-5 (slide detection + AI combining) are the high-value gaps
- PDF slides already exist → can use PDF page timestamps instead of video screenshots
- Key insight: if we can timestamp each transcript segment to the corresponding PDF page, NotebookLM gets multimodal context (text says X, slide shows Y)
- Scene detection via `ffmpeg -vf select='gt(scene,0.3)'` works for screenshare; less reliable if camera is on instructor face

**Questions for Opus:**
1. Given that PDFs already exist, what's the most efficient way to align transcript segments to PDF pages? (Don't re-extract screenshots if PDFs are already there)
2. What's the right output format? Options: (a) enriched transcript with [SLIDE: page N] markers, (b) chapter-by-chapter markdown docs, (c) structured JSON for NotebookLM
3. Should this pipeline live in `vad_transcribe.py` (extend existing tool) or be a separate `video_to_knowledge.py` script?
4. Is Claude Vision the right tool for alignment, or is there a cheaper/faster approach?
5. Write the Sonnet execution tasks once the design is clear.

### ANSWER (Opus, 2026-06-23)

**Verified facts that drive the design:**
- PDF text extracts cleanly in Thai via `pypdf` (checked: PDF 1 p.2 = 338 chars of real slide text, not scanned images). → **No OCR, no Claude Vision, no video screenshots needed.** The PDFs *are* the slide deck in machine-readable form.
- The current transcripts are **plain text with NO timestamps** (vad_transcribe.py concatenates speech and strips timing). So we cannot do time-based alignment without re-transcribing — and we shouldn't, because:
- The source videos are **Facebook Live** (instructor face + screen-share mix). `ffmpeg select='gt(scene,...)'` scene detection is unreliable here (camera cuts ≠ slide changes). The user's own constraint note flags this.

**Therefore the user's diagram steps 4-5 ("detect slide change + screenshot" → "AI combine") are replaced by a cheaper, more robust path: PDF-text-anchored chapterization.** This is a deliberate deviation — surface it to the user. We don't detect slides from video; we use the PDF pages directly as the slide spine and let an LLM map transcript prose onto them by *content*, not by *time*.

**Recommended pipeline (lean, no video reprocessing):**
```
PDF (already have)  ──pypdf──>  per-page slide text:  [{page, text}]
transcript (already have, plain text)
        │
        └──> ONE LLM pass per session (Haiku 4.5 for cost):
             "Here is the full lecture transcript, and here are the N slides
              in order with their text. Segment the transcript into chapters
              that follow the slide order. For each chapter output:
                ## Ch.k — <title>   [Slide p.X–Y]
                - 3–5 bullet summary (in Thai, grounded in transcript)
                - key terms / tickers mentioned
                - 1–2 verbatim quote anchors from the transcript"
        │
        └──> session_N_structured.md
        └──> add to NotebookLM (alongside raw transcript + PDF, which are already sources)
```

**Answers to the 5 questions:**
1. **Alignment = LLM content-matching, not timestamps.** Feed full transcript (~55K tokens) + ordered slide texts in a single call; the model maps prose→page by meaning. The PDF page order is the anchor (lectures move through slides in order, so it's a near-monotonic alignment — easy for the model). No embeddings infra, no vision.
2. **Output = (b) chapter-by-chapter markdown with `[Slide p.N]` markers.** It's text-native (NotebookLM loves it), human-readable, and citeable. JSON adds friction with no benefit here; inline-marker-only transcript loses the chapter structure the user explicitly wants. Markdown chapters give BOTH structure and slide refs.
3. **Separate script: `tools/structure_transcript.py`.** Do NOT bloat `vad_transcribe.py` — it has one clean job (audio→text). The new step is text→structured-text and belongs in its own tool. Most of the user's "video" pipeline is already done; the real remaining work is transcript-structuring, so name it for what it does.
4. **Claude Vision is NOT the right tool — text is.** Vision would only be needed if PDFs were scanned images; they're not. Use **Haiku 4.5** for the chapterization (cheap, 5 sessions × ~55K tokens). Pilot one session; if Thai chapter quality is weak, escalate that session to Sonnet. Reserve Vision only as a fallback for the handful of slides that are pure charts with no extractable text (optional, likely unnecessary).
5. Sonnet tasks written below as **T4** in `for-sonnet/tasks.md`.

**Cost/scope guardrails for Sonnet:** pilot on Session 2 first (smallest, 43 pp) → show the user → only then batch the other 4. Grounding rule stays: every bullet must trace to the transcript; if a slide has no matching spoken content, mark it `[ไม่ได้พูดถึง]` rather than inventing.

---

<!-- Add new questions below as they arise -->

---

## Q10 — ออกแบบระบบยืนยันนัดหมายอัตโนมัติ (LINE Bot คลินิก Alonsi)
**Status:** done (Opus, 2026-07-01) — คำตอบด้านล่าง. Sonnet executes **T12**.

**บริบท:**
- LINE Bot คลินิก Alonsi (ดู Q8/Q9 สำหรับ architecture รวม) รันบน n8n + Google Sheets
- ตอนนี้บอทรับจองนัดได้แล้ว แต่ **ยังไม่มีระบบยืนยันนัดล่วงหน้า** (เช่น ส่งข้อความ 1 วันก่อนนัด)
- คนไข้บางส่วนนัดผ่านบอท LINE / บางส่วนนัดทางโทรศัพท์แล้วหมอบันทึกเองใน Sheet
- คลินิกมีโปรแกรม OPD แยกต่างหาก — มี HN (Hospital Number) ของทุกคนไข้ — อาจ export เป็น CSV ได้ (กำลังสอบถาม developer)

**สิ่งที่ตกลงกันแล้ว (ห้าม re-litigate):**
1. ต้องสร้าง **Contacts sheet ใหม่** — เก็บ userId ↔ HN ถาวร (State sheet ไม่ใช่ที่เก็บเพราะถูก clear หลัง session)
2. ใช้ **HN จาก OPD** เป็น patient identifier (ไม่สร้าง ID ใหม่) — ทำให้ระบบ LINE ↔ OPD เชื่อมกันในอนาคตได้
3. **ทั้ง 2 วิธี register** ต้องมี:
   - **QR Code ต่อคนไข้** (ฝัง HN ในลิงก์) — สแกนที่เคาน์เตอร์หรือแนบใบนัด → คนไข้กด Send ครั้งเดียว
   - **พิมพ์ HN เอง** — สำหรับคนที่ add บอทจากบ้านโดยไม่มี QR
4. หลัง register → บอทส่ง **Flex Message "นามบัตรดิจิทัล"** กลับ (ชื่อ / HN / นัดถัดไป)
5. QR สร้างได้จาก Google Sheet สูตร `=IMAGE("https://api.qrserver.com/v1/create-qr-code/?data=HN:XXXXX&size=150x150")`

**Logic ที่ตกลงคร่าวๆ:**
```
scan QR หรือพิมพ์ HN
  → บอทรับ HN + userId
  → เช็ค Contacts sheet:
      ไม่มี HN นี้ → ลงทะเบียนใหม่ ✅
      มี HN + userId ตรง → แจ้งว่าลงทะเบียนแล้ว ✅
      มี HN + userId ไม่ตรง → ปฏิเสธ (ป้องกันสวมรอย) ⛔
  → ส่งนามบัตรดิจิทัล

ระบบยืนยันนัด (Cron ทุกเช้า):
  → ดึง Appointments ที่ date = พรุ่งนี้ + status = "pending"
  → หา userId จาก Contacts sheet (match ด้วย HN)
  → ส่ง LINE push: "ยืนยันนัดพรุ่งนี้ เวลา XX:XX น. ไหมคะ?"
      [✅ ยืนยัน] → update status = "confirmed"
      [🔄 ขอเลื่อนนัด] → trigger handoff ให้เจ้าหน้าที่
```

**คำถามสำหรับ Opus:**
1. **Contacts sheet schema** — ควรเก็บ field อะไรบ้าง? (HN, userId, ชื่อ, เบอร์, วันที่ลงทะเบียน, อื่นๆ?) และควร sync ข้อมูลชื่อ/เบอร์จาก OPD เมื่อไหร่?
2. **QR link format ที่ถูกต้อง** — `line.me/R/oaMessage/@botId?text=HN:00123` ทำงานได้จริงไหม? หรือต้องใช้ LIFF? ข้อดี/ข้อเสียของแต่ละทาง?
3. **Verify HN** — ควร verify HN กับ OPD database ไหม? หรือ accept ทุก HN? ถ้า verify ต้องทำผ่านอะไร (OPD อาจไม่มี API)?
4. **กรณีคนไข้นัดทางโทรศัพท์** — Appointments row ที่หมอบันทึกเอง จะไม่มี HN ผูก Contacts → ส่งยืนยันไม่ได้ ควรจัดการอย่างไร? (skip? แจ้งเจ้าหน้าที่? ให้หมอกรอก HN ตอนบันทึก?)
5. **Flex Message นามบัตรดิจิทัล** — ควรแสดงข้อมูลอะไร? และข้อมูล "นัดถัดไป" ดึงมาจาก Appointments sheet ยังไง (คนไข้อาจมีหลายนัด)?
6. **ลำดับการ implement** — ควรทำอะไรก่อน? (Contacts sheet → registration flow → QR → cron ยืนยันนัด) และมีขั้นตอนไหนที่ควรทำก่อน/หลังพิเศษไหม?
7. **Edge cases** — มี edge case สำคัญที่ Sonnet น่าจะมองข้ามไหม? (เช่น คนไข้เปลี่ยนโทรศัพท์ → LINE userId ใหม่, HN เดิม / QR สแกนก่อน add บอทเป็น friend / คนไข้เด็กที่ผู้ปกครองใช้ LINE แทน ฯลฯ)

ถ้า Sonnet ต้องทำอะไรหลัง Opus ตอบ ให้เขียนใน `for-sonnet/tasks.md` ด้วย

### ANSWER (Opus, 2026-07-01)

**⚠️ ข้อค้นพบที่เปลี่ยนทั้งดีไซน์ (ตรวจจาก sheet จริง `sheets/structure.md`):**
Appointments tab ตอนนี้ **ไม่มีคอลัมน์วันที่ที่ machine-readable เลย** — มีแค่ `preferred_time` ที่เป็น **ข้อความอิสระจาก Gemini** ("พรุ่งนี้บ่ายสองค่ะ", "เสาร์หน้า 10 โมง") และ key ที่ `userId` ไม่ใช่ HN. คอลัมน์จริง:
`timestamp | userId | name | surname | phone | procedure | doctor | preferred_time | status | confirmed_time`

**ผลลัพธ์:** cron ที่ต้อง query `date = พรุ่งนี้` **ทำไม่ได้เลยบน schema ปัจจุบัน** — ไม่มีอะไรให้เทียบวันที่ และไม่มี HN ให้ join กับ Contacts. ดังนั้น **prerequisite อันดับ 0 ของทั้ง Q10 คือแปลง `preferred_time` free-text → คอลัมน์ `appointment_date` (YYYY-MM-DD) + `appointment_time` (HH:MM) แบบ structured และเพิ่ม `hn` ลง Appointments.** ทุกคำถามข้างล่างตั้งอยู่บนสมมติฐานนี้ — ถ้าไม่ทำ ข้อ 6 (cron) เป็นไปไม่ได้.

---

**Q10.1 — Contacts sheet schema + จังหวะ sync จาก OPD**

**ตัดสินใจหลัก: แยกเป็น 2 sheet — `OPD_Master` (source of truth, overwrite ด้วย CSV) + `Contacts` (mapping HN↔LINE, ของบอทเขียนเอง). join กันด้วย HN.** เหตุผล: OPD เป็นเจ้าของชื่อ/เบอร์จริง — ถ้าเอาไปปนใน Contacts แล้ว CSV import ทับ จะชนกับข้อมูลที่บอทเขียน. แยกให้ import เขียนทับ OPD_Master ได้อิสระ โดยไม่แตะ mapping.

`OPD_Master` (read-only mirror ของ OPD, ทับทั้ง sheet ทุกครั้งที่ import CSV) — คอลัมน์:
`hn | first_name | last_name | phone | qr_link | opd_updated_at`
- `hn` = **เก็บเป็น text เสมอ** (กัน Sheets ตัด leading zero — ดู edge case)
- `qr_link` = สูตร `=IMAGE(...)` ต่อแถว (ข้อ 2)

`Contacts` (บอทเขียน 1 แถว = 1 การผูก HN↔userId) — คอลัมน์:
`hn | line_user_id | display_name | source | verified | registered_at | opt_out | updated_at`
- `hn` = **ไม่ unique** (พ่อแม่ 1 LINE ผูกหลาย HN ได้ — ดู edge case เด็ก). composite key จริง = `(hn, line_user_id)`.
- `line_user_id` = LINE userId
- `display_name` = ชื่อโปรไฟล์ LINE (จาก getProfile — ไว้ทักทาย ไม่ใช่ตัวตนจริง)
- `source` = `qr` | `manual`
- `verified` = ผ่านการ match กับ OPD_Master แล้วหรือยัง (`true`/`false`)
- `opt_out` = คนไข้ขอไม่รับ reminder (PDPA safety valve)

**อย่าเก็บ name/phone ซ้ำใน Contacts เป็น authoritative** — ดึงสดจาก OPD_Master ตอนต้องใช้ (join by hn). ชื่อคนไข้เปลี่ยน/แก้ที่ OPD ที่เดียว.

**จังหวะ sync:** OPD_Master ทับใหม่ทั้ง sheet ทุกครั้ง import CSV (ตั้ง schedule รายสัปดาห์ หรือ manual เมื่อ dev ส่ง CSV มา). Contacts ไม่ต้อง sync — มันแค่ผูก id, ชื่อ/เบอร์ join จาก OPD_Master แบบ real-time เสมอ จึงไม่มีวันเก่า.

---

**Q10.2 — QR link format: ใช้ `oaMessage` deep link (ไม่ใช่ LIFF)**

`https://line.me/R/oaMessage/@BOT_BASIC_ID?text=HN%3A00123` — **ทำงานจริง**. เปิดแชท OA พร้อม prefill ข้อความ `HN:00123` → คนไข้กด Send ครั้งเดียว. ถ้ายังไม่เป็นเพื่อน LINE จะ prompt add friend ก่อนแล้วค่อยเปิดแชท.
- **ต้อง URL-encode** `:` เป็น `%3A` → `data=HN%3A00123` ใน QR. (ถ้าไม่ encode บาง client จะ prefill เพี้ยน)
- `@BOT_BASIC_ID` = **Basic ID ของ OA (ขึ้นต้น @)** ไม่ใช่ channel id.
- สูตรใน OPD_Master: `=IMAGE("https://api.qrserver.com/v1/create-qr-code/?size=150x150&data="&ENCODEURL("https://line.me/R/oaMessage/@BOT_BASIC_ID?text=HN:"&A2))` — `ENCODEURL` จะ escape ให้เอง (สะอาดกว่าฝัง `%3A` มือ).

| | oaMessage deep link (แนะนำ) | LIFF |
|---|---|---|
| ตั้งค่า | ศูนย์ — แค่ URL | ต้องสร้าง LIFF app + endpoint + login flow |
| คนไข้ทำ | สแกน → กด Send | สแกน → เปิด webview → login → submit |
| ข้อเสีย | ข้อความ prefill **แก้ได้** (คนไข้อาจแก้ HN) — แต่เรา verify ฝั่ง server อยู่แล้ว จึงไม่เป็นปัญหา | overkill, เพิ่ม failure surface, ต้อง maintain |

→ **oaMessage ชนะขาด.** LIFF ไม่คุ้มสำหรับงานแค่ส่ง HN. คงทาง "พิมพ์ HN เอง" เป็น fallback (ตกลงแล้ว).

---

**Q10.3 — Verify HN: verify กับ OPD_Master + echo ชื่อกลับให้ยืนยัน (สำคัญกว่าที่คิด)**

OPD ไม่มี API → verify กับ **OPD_Master sheet** (ที่ import จาก CSV) เท่านั้น. Logic:
- HN เจอใน OPD_Master → `verified=true`, ดึงชื่อมา **echo กลับให้คนไข้ยืนยัน**: *"คุณ [ชื่อจาก OPD] ใช่ไหมคะ?"* ก่อน finalize การผูก.
- HN ไม่เจอ → **อย่า hard-accept มั่ว** และ **อย่า hard-reject**: ตอบ "ไม่พบ HN นี้ในระบบค่ะ" + ผูกแบบ `verified=false` แล้ว **flag ให้เจ้าหน้าที่ตรวจ** (อาจพิมพ์ผิด หรือ OPD ยังไม่ sync). ทำให้ระบบใช้ได้แม้ CSV ยังไม่มา แล้วค่อยรัดกุมขึ้นเมื่อมี.

**ทำไม echo ชื่อถึงจำเป็น:** ถ้าคนไข้พิมพ์ HN ผิดไปตรงกับ HN ของ**คนอื่นที่มีจริง** → verify ผ่าน → ระบบจะส่งนัดของคนอื่นให้เขา = **ข้อมูลคนไข้รั่วข้ามคน (PDPA breach)**. การ echo ชื่อกลับให้คนไข้กดยืนยัน = ด่านจับ typo ที่ถูกที่สุดและกันเคสนี้ได้ตรงจุด. **ห้ามข้าม.**

---

**Q10.4 — คนไข้นัดทางโทรศัพท์ (หมอบันทึกเอง): ผูกทุกอย่างด้วย HN, ไม่ใช่ userId**

รากปัญหา: ปัจจุบัน Appointments key ที่ `userId` — แต่แถวที่หมอกรอกเองไม่มี userId. ทางแก้เดียวที่ scale = **ให้ HN เป็น join key กลางของทั้ง 2 ช่องทาง**:
- เพิ่มคอลัมน์ `hn` ใน Appointments. **หมอกรอก HN ทุกครั้งที่บันทึกนัดเอง** (นิสัยเดียวที่สำคัญที่สุดของงานนี้).
- นัดที่บอทสร้าง: stamp `hn` อัตโนมัติจาก Contacts (lookup ด้วย userId).
- Cron ยืนยันนัด: ต่อแถว → `hn` → lookup Contacts → **ถ้ามี `line_user_id` (คนไข้ register แล้ว)** → LINE push. **ถ้าไม่มี** (ยังไม่ register / นัดโทรศัพท์ล้วน) → **ไม่ push, แต่รวมเข้า "call list" รายวัน** ส่งให้ admin/เจ้าหน้าที่โทรยืนยันเอง.

→ ไม่มีนัดไหน "หาย": register แล้ว = LINE อัตโนมัติ; ยังไม่ register = ตกไป call list ให้คนโทร. **อย่า skip เงียบ** — เจ้าหน้าที่ต้องเห็นว่าเหลือใครต้องโทร.

---

**Q10.5 — Flex Message "นามบัตรดิจิทัล"**

แสดง:
- Header: โลโก้/ชื่อคลินิก
- Body: `display_name` (หรือชื่อจาก OPD) + **HN** (ตัวใหญ่ อ่านชัด) + สถานะ "ลงทะเบียนสำเร็จ ✅"
- **นัดถัดไป**: 1 นัดที่ใกล้ที่สุด — วันที่/เวลา/หมอ/หัตถการ. ถ้าไม่มี → "ยังไม่มีนัดหมายค่ะ"
- Footer buttons: `[ดูนัดทั้งหมด]` `[ติดต่อเจ้าหน้าที่]`

**ดึง "นัดถัดไป" ยังไงเมื่อมีหลายนัด:** query Appointments where `hn = X` AND `appointment_date >= today` AND `status ∈ {confirmed, pending}` → **sort `appointment_date, appointment_time` ascending → เอาแถวแรก** (ใกล้สุด). ถ้ามีมากกว่า 1 → แสดงนัดใกล้สุด + บรรทัด "และอีก N นัด" ให้กด `[ดูนัดทั้งหมด]`. (ต้องมี `appointment_date` structured — ย้ำ prerequisite 0; sort บน free-text `preferred_time` ทำไม่ได้).

---

**Q10.6 — ลำดับ implement (schema ก่อนเสมอ — มันคือคอขวด):**

1. **Prerequisite 0 — แก้ Appointments schema ก่อนทุกอย่าง**: เพิ่ม `hn`, `appointment_date` (YYYY-MM-DD), `appointment_time` (HH:MM), `confirm_status`, `confirm_sent_at`. อัปเดต Build Gemini Request ให้ Gemini output วันที่แบบ **normalized** (ให้มันแปลง "พรุ่งนี้บ่ายสอง" → `2026-07-02` + `14:00` โดยรู้ today's date) แทน free-text. **ถ้าข้อนี้ไม่เสร็จ ข้อ 4 เป็นไปไม่ได้.**
2. **OPD_Master + import CSV** (ถ้า dev ส่ง CSV มาแล้ว; ถ้ายัง → ทำ Contacts ต่อได้เลยแบบ verified=false).
3. **Contacts sheet + registration flow**: parse ข้อความ `HN:xxxxx` → verify กับ OPD_Master → echo ชื่อยืนยัน → upsert Contacts → ตอบ Flex นามบัตร. **ต้องแก้ skip filter (M1 ใน T10) ก่อน** ไม่งั้น postback/ข้อความ HN อาจโดน drop.
4. **QR generation** (สูตร IMAGE ใน OPD_Master) — ทำขนานกับข้อ 3 ได้.
5. **Cron ยืนยันนัด** (ทำ**สุดท้าย** เพราะกินทั้ง structured date + Contacts): Schedule ทุกเช้า (Asia/Bangkok) → อ่าน Appointments where `appointment_date = พรุ่งนี้` AND `status = confirmed` AND `confirm_status = ''` → per แถว join HN→Contacts → มี userId → push Flex ยืนยัน `[✅ ยืนยัน]`/`[🔄 ขอเลื่อนนัด]` + set `confirm_sent_at` → ไม่มี userId → call list. ปุ่มยิง **postback** → route: ยืนยัน→`confirm_status=confirmed`; ขอเลื่อน→trigger handoff (reuse flow เดิม) + notify admin.

**ทำไมลำดับนี้:** schema เป็น dependency ของทุกอย่าง → มาก่อน. registration สร้าง mapping ที่ cron ต้องใช้ → มาก่อน cron. QR แค่ช่องทางกระจาย → ขนานได้. cron consume ทุกอย่าง → สุดท้าย. **แนะนำ pilot cron กับตัวเอง/เจ้าหน้าที่ 1 คนก่อน broadcast จริง.**

---

**Q10.7 — Edge cases ที่ Sonnet น่าจะมองข้าม (เรียงตามความร้ายแรง):**

1. 🔴 **คนไข้เปลี่ยนมือถือ → userId ใหม่ HN เดิม (ชนกับ "ตกลงข้อ 3": HN ตรง userId ไม่ตรง → ปฏิเสธ).** กฎปฏิเสธนั้นถูกสำหรับกันสวมรอย **แต่จะ block เคส legit นี้ผิดๆ**. อย่าตีความ "ปฏิเสธ" เป็น "เงียบ block" — ให้แปลว่า **"ไม่ผูกทับทันที แต่ส่งให้เจ้าหน้าที่อนุมัติการ re-bind"** หรือให้คนไข้ยืนยันตัวตนซ้ำ (เช่น echo ชื่อ OPD + ให้พิมพ์เบอร์ที่ตรงกับ OPD) แล้ว **อัปเดต `line_user_id` ของแถว HN นั้น** (ไม่ใช่สร้างแถวใหม่). นี่ไม่ใช่การ re-litigate ข้อ 3 — เป็นการ**นิยาม "ปฏิเสธ" ให้มีทางออก** ไม่ให้คนไข้จริงติดตาย. (ธง: ควรให้ user ตัดสินว่า auto-approve เมื่อเบอร์ตรง หรือ staff-approve เสมอ.)
2. 🔴 **เด็ก/ผู้ปกครอง: 1 LINE userId ↔ หลาย HN.** สมมติฐาน "1 userId = 1 HN" **พัง**. → Contacts key ต้องเป็น `(hn, line_user_id)` ไม่ใช่ userId unique (ทำไว้ใน Q10.1 แล้ว). registration HN ที่สองภายใต้ userId เดิม = อนุญาต (ครอบครัว). Flex นามบัตร + cron ต้องรองรับ "userId นี้มีนัดของหลาย HN" — เวลา push ให้ระบุชื่อคนไข้ในข้อความเสมอ ("ยืนยันนัดของ **น้องมาย** พรุ่งนี้...") ไม่งั้นพ่อแม่งง.
3. 🔴 **HN พิมพ์ผิดไปตรง HN คนอื่นที่มีจริง → ส่งนัดผิดคน (PDPA).** กันด้วย echo ชื่อ OPD ให้ยืนยัน (Q10.3). ย้ำอีกรอบเพราะร้ายแรง.
4. 🟡 **HN leading zero โดน Sheets ตัด** (`00123`→`123`). → format คอลัมน์ `hn` เป็น **Plain text** ทั้ง OPD_Master + Contacts + Appointments, และ parse ข้อความ `HN:00123` เก็บ string ตรงตัว.
5. 🟡 **QR สแกนก่อน add friend.** oaMessage จะ prompt add ก่อน แล้ว follow event ยิงตามด้วยข้อความ HN — registration ทำงานได้ไม่ขึ้นกับลำดับ. แต่บาง client อาจ **ไม่ prefill** หลัง add → ใส่ข้อความบนใบ QR: "สแกนแล้วเพิ่มเพื่อน จากนั้นกดส่งข้อความ HN ที่ขึ้นให้ / ถ้าไม่ขึ้นให้พิมพ์ HN:เลขของคุณ".
6. 🟡 **ส่งยืนยันซ้ำ** (cron รันซ้ำ / LINE redeliver). → guard ด้วย `confirm_sent_at` + `confirm_status`: push เฉพาะแถวที่ `confirm_status=''` AND `confirm_sent_at=''` แล้ว stamp ทันที (idempotency แบบเดียวกับ M3 ใน T10).
7. 🟡 **Timezone.** "พรุ่งนี้" ต้องคิดบน **Asia/Bangkok**; `appointment_date` เก็บเป็น local date. Schedule node ตั้ง timezone ให้ตรง ไม่งั้น cron ยิงผิดวัน.
8. 🟢 **opt-out / PDPA.** reminder ถือเป็น transactional (มีความสัมพันธ์คนไข้อยู่แล้ว) ความเสี่ยงต่ำ แต่มี `opt_out` flag ให้เคารพ + ปุ่ม "ไม่รับการแจ้งเตือน" ในนามบัตร.
9. 🟢 **นัดถูกยกเลิก/เลื่อนหลังส่งยืนยันไปแล้ว** — cron ควรอ่านเฉพาะ `status=confirmed`, ข้าม `cancelled`; ถ้าเลื่อน → reset `confirm_status` เพื่อส่งใหม่รอบวันใหม่.
10. 🟢 **คนไข้กด "ขอเลื่อน" นอกเวลาทำการ** — handoff trigger ต้องแจ้ง admin แต่ตั้ง expectation ("เจ้าหน้าที่จะติดต่อกลับในเวลาทำการค่ะ") ไม่ให้คนไข้รอเก้อ.

**สรุป:** งานนี้ **บล็อกอยู่ที่ Appointments schema (structured date + HN)** — Sonnet ต้องทำ prerequisite 0 ก่อน ไม่งั้นสร้าง cron บนทราย. Sonnet execution → **T12 ใน for-sonnet/tasks.md.**

---

## Q8 — Code Review & Recommendations: Alonsi Clinic LINE Bot
**Status:** done (Opus, 2026-07-01) — full review below. Sonnet executes **T10**.

**Context:**
Production LINE chatbot สำหรับคลินิกทันตกรรม Alonsi — รับจองนัดหมายผ่าน LINE 24/7
- n8n workflow ID: `GFdRhaxbgbxvIPjw`
- Local repo: `/Users/alonsi/Desktop/alonsi-clinic-bot/`
- Google Sheet: `1PkKrnezY7HEUKAj1njIl-USsdly4tiKtzgYy0tv8psk` (tabs: State, Appointments, FAQ)
- Admin LINE userId: `Ub0da86b2cf3d51d6b34c42811969c255`

**Architecture (อ่านจาก n8n-workflow.json):**
```
Webhook1 (LINE) → Verify LINE Signature → Parse LINE Message → If (skip?) →
  [booking path] Read State → Build Gemini Request → Gemini API → Parse Gemini Response →
    If1 (booking_complete?) →
      true  → Save State (Google Sheets appendOrUpdate, key: userId, fields: history, updated_at) → Reply to LINE
      false → Append row in Appointments sheet → Delete row from State → Reply to LINE
  [handoff path] Check Handoff Mode → If Normal Mode →
      true  → [booking path above]
      false → If Is Trigger →
          true  → Set Handoff True → Push Notify Admin → Reply Handoff Start
          false → If Is Reset →
              true  → Reset Handoff → Reply Handoff End
              false → [silent drop — คนไข้อยู่ใน active handoff, ส่งข้อความมา → ไม่มี reply]
  [non-booking] Log FAQ Question
```

**LLM:** Gemini 2.5 Flash (ไม่ใช่ Claude) — จัดการ booking conversation + ตีความ intent + output JSON
**System prompt:** ไทย, บอทชื่อ "คุกกี้", มี price list ครบ, ขั้นตอนจองนัด 4 ขั้น (name/surname/phone, procedure, doctor, preferred_time) → return `{"replyText":"...","booking_complete":true/false,"appointment":{...}}`

**Issues ที่ Sonnet เห็นก่อนส่งให้ Opus:**
1. **Security**: LINE Channel Access Token hardcoded plain text ใน 4 nodes (Reply to LINE, Reply Handoff Start, Reply Handoff End, Push Notify Admin) — ถ้า JSON leak → token โดน
2. **Silent drop**: เมื่อ handoff=active แต่ไม่ใช่ trigger/reset → ไม่มี reply (คนไข้พิมพ์ข้อความระหว่างรอหมอ → บอทเงียบ)
3. **Booking complete condition**: `If1` check `booking_complete != "true"` → true branch = Save State (ยังจองไม่เสร็จ), false branch = Append Appointment + Delete State row. ตรรกะถูกแต่ชื่อ branch ทำให้สับสน
4. **State schema drift**: Q6 Opus design ใช้ `line_user_id` แต่ workflow จริงใช้ `userId` — ยังไม่ migrate
5. **No error handling**: ถ้า Gemini API fail → ไม่มี fallback reply คนไข้ไม่รู้ว่าเกิดอะไร
6. **FAQ logging branch**: Log FAQ ทุก message ที่ `skip=false` ก่อน route ไปหา handoff/booking — อาจ log ข้อความ booking ด้วย ซึ่งอาจไม่ใช่เจตนา

**Questions สำหรับ Opus:**
1. Issue ไหนที่ critical และควรแก้ก่อน (ระดับ production risk)?
2. มี issue อื่นที่ Sonnet มองข้ามไปไหม?
3. สำหรับ active handoff silent drop — ควรตอบกลับว่าอะไร? (เช่น "หมอกำลังดูแลอยู่นะคะ") หรือควร silent จริงๆ เพราะหมอ reply ผ่าน LINE OA Manager แทน?
4. ระบบนี้ scale รองรับคลินิกเดียว แต่ถ้า expand เป็น 2-3 สาขาในอนาคต bottleneck อยู่ตรงไหน?
5. วิธีที่ดีที่สุดแก้ security issue ใน n8n (ไม่ใช่ Claude Code env) — น่าจะเป็น n8n credentials หรือ env vars?

### ANSWER (Opus, 2026-07-01)

**สิ่งที่ต้องรู้ก่อน (ตรวจจาก JSON จริง — แก้ความเข้าใจของ Sonnet):**
- **Silent drop ถูกแก้ไปแล้ว.** มี node `Reply Handoff Active` (id `aa00...0010`) ต่อจาก `If Is Reset` → false branch. เมื่อ `mode='active'` คนไข้พิมพ์อะไรมาระหว่าง handoff → บอทตอบ "หมอกำลังดูแลอยู่ค่ะ รอสักครู่นะคะ" + ปุ่ม "จบแล้วค่ะ". ดังนั้น **issue #2 ของ Sonnet ล้าสมัย** — ปัญหากลับด้าน: ตอนนี้บอท **ตอบทุกข้อความ** (spam) ดูข้อ Q3.
- **State schema drift (issue #4)** — เป็น design ของ Q6 (`line_user_id`) ที่ยังไม่ implement ไม่ใช่ bug ของ workflow ปัจจุบัน (ใช้ `userId` สม่ำเสมอทั้ง flow). ตัดออกจาก critical list.

---

**Q8.1 — Critical production risks (เรียงลำดับแก้ก่อน):**

| # | Issue | ระดับ | ทำไม |
|---|-------|------|------|
| C1 | **LINE Access Token hardcoded ใน 4 nodes + commit ลง git** | 🔴 Critical | token โผล่ใน repo แล้ว = ถือว่ารั่วถาวร. ใครได้ไฟล์ → ส่งข้อความในนามคลินิก, ดึง profile คนไข้, push spam. **ต้อง rotate ทันที** ไม่ใช่แค่ย้ายที่เก็บ |
| C2 | **Verify LINE Signature ไม่ enforce** (node คำนวณ hash แต่ mismatch แค่ `console.log` แล้ว return ผ่าน) | 🔴 Critical | webhook URL เป็น public. ตอนนี้ใครก็ POST event ปลอมเข้ามาได้ → จองปลอม, เผา Gemini quota, spam admin push. signature check เป็นแค่ฉาก ไม่ได้กันอะไร |
| C3 | **Gemini API ไม่มี error branch** | 🔴 Critical | try/catch ใน Parse Gemini จับแค่ JSON parse ไม่จับ HTTP fail. ถ้า Gemini timeout/quota/500 → workflow error → **คนไข้ไม่ได้ reply เลย** บอทดูเหมือนพัง (issue #4 ยืนยันจริง) |
| C4 | **Delete State by stale `row_number`** (`$('Read State').first().json['row_number']`) | 🔴 Critical | ลบแถวด้วย index ที่จับไว้ตอน Read. ถ้ามี write/ลบของ user อื่นแทรกกลาง → row เลื่อน → **ลบผิดแถว** = ทำลาย session คนไข้คนอื่น. append-แล้ว-delete-by-index แข่งกับ concurrency = data corruption. นี่คือพี่น้องของบั๊ก Q7 |

**ลำดับแก้:** C1 (rotate ทันที, นาทีนี้) → C2 (ปิดรู forgery) → C3 (กันบอทเงียบ) → C4 (กัน data corruption). C1–C2 คือ security, C3–C4 คือ reliability ของคนไข้จริง.

**Q8.2 — Issues ที่ Sonnet มองข้าม:**

1. 🔴 **Signature check ไม่ enforce** (C2 ข้างบน) — ใหญ่สุดที่ Sonnet ไม่เห็น.
2. 🔴 **Delete-by-stale-row_number race** (C4) — data integrity.
3. 🟡 **`If` node (skip filter) พัง — expression ขาด `=`.** `"leftValue": "{{ $json.userId }}"` ไม่มี `=` นำหน้า → n8n ตีเป็น **string ตรงตัว** ไม่ eval → `notEmpty` เป็น true เสมอ → **skip ไม่เคยทำงาน**. event ที่ไม่ใช่ message (follow/unfollow/postback) ที่ Parse ตั้ง `skip:true, userId:''` จะทะลุเข้า Read State/Gemini/Log FAQ ด้วย userId ว่าง → junk rows + เผา Gemini ฟรี. (เทียบ node อื่นใช้ `"=({{ $json.mode }}"` มี `=` — ยืนยันว่าตัวนี้ลืม).
4. 🟡 **ไม่มี webhook idempotency/dedup.** LINE redeliver event ซ้ำได้ (retry เมื่อไม่ได้ 200 ทัน). ไม่มีการเช็ค `event.message.id`/`webhookEventId` → เสี่ยง **จองซ้ำ 2 แถว**. สำหรับ booking จริงควรกัน.
5. 🟡 **ไม่ validate appointment ก่อน Append.** ถ้า Gemini hallucinate `booking_complete:true` พร้อม field ขาด/มั่ว → append นัดเสีย + ลบ state ทิ้ง. ไม่มี schema check, ไม่ validate เบอร์โทร.
6. 🟡 **Active handoff = spam** (ดู Q3).
7. 🟢 **Gemini API key อยู่ใน URL query string** (`?key=...`) — query string ถูก log ตาม proxy/access log ง่ายกว่า header. ควรย้ายเป็น credential/header เหมือนกัน. (ในไฟล์ commit เป็น placeholder แต่ prod คือ key จริง).
8. 🟢 **FAQ logs ทุกข้อความ** (issue #5 จริง): `If.main[0]` fan-out ไป `Read State` **และ** `Log FAQ Question` พร้อมกันทุก message — FAQ tab เลยกลายเป็น message log ทั้งหมด (รวม booking/handoff) ไม่ใช่ "คำถามที่ตอบไม่ได้" อย่างที่ชื่อสื่อ. `answered:"no"` hardcoded. ถ้าตั้งใจเก็บ log ทั้งหมดก็โอเค แต่ควร rename ให้ตรง หรือกรองเฉพาะข้อความที่ Gemini ตอบไม่ได้.

**Q8.3 — Active handoff: ตอบหรือเงียบ?**

ปัจจุบัน workflow **ตอบทุกข้อความ** ("หมอกำลังดูแลอยู่ค่ะ...") = แย่กว่าเงียบ เพราะคนไข้กำลังคุยกับหมอผ่าน OA Manager แล้วบอทแทรก "หมอกำลังดูแลอยู่" หลังทุกข้อความ → รก, น่ารำคาญ, และทำให้ chat ที่หมอเห็นเต็มไปด้วย bubble ของบอท.

**คำแนะนำ: acknowledge ครั้งเดียวตอนเข้า handoff (Reply Handoff Start ทำอยู่แล้ว) จากนั้น "เงียบ" ระหว่าง active.** เหตุผล: ปุ่ม "จบแล้วค่ะ" + ข้อความ Start ตั้ง expectation ครบแล้ว, หมอเป็นคนคุยจริง, บอทไม่ควรแทรก. → **เอา `Reply Handoff Active` ออก** (ให้ active mode = no-reply/silent) หรือถ้าอยากให้มี safety net ให้ใส่ **throttle**: เก็บ `last_handoff_reply_at` ใน State แล้วตอบซ้ำได้แค่ทุก ~15-30 นาที (กันเคสคนไข้พิมพ์มาหลังเงียบไปนาน). ค่า default ที่แนะนำคือ **เงียบ** — เรียบและไม่กวนหมอ.

**Q8.4 — Bottleneck ถ้าขยาย 2-3 สาขา:**

ระบบนี้เป็น **single-tenant hardcoded** — คอขวดไม่ใช่ throughput แต่คือ **สมมติฐาน "คลินิกเดียว" ฝังอยู่ทุกชั้น**:
1. **System prompt ผูกสาขาเดียว** — ที่อยู่/เบอร์/หมอ 5 คน/price list ทั้งหมด hardcode ใน `Build Gemini Request`. หลายสาขา = ราคา/หมอ/เวลาทำการต่างกัน → prompt เดียวเสิร์ฟไม่ได้ ต้อง parameterize ตาม branch.
2. **State ไม่มี `branch_id`** — แยกไม่ออกว่าคนไข้จองสาขาไหน. Appointments tab ก็ไม่มี dimension สาขา.
3. **Admin push ผูก userId เดียว** (`Ub0da...255`) — แจ้งเตือนไปคนเดียว routing ตามสาขาไม่ได้.
4. **Google Sheet เดียว + write concurrency** — Sheets API มี quota (~60 writes/นาที/user) และ append+delete-by-row-index (C4) จะ **แข่งกันหนักขึ้นมาก** เมื่อ 3 สาขาเขียน sheet เดียวพร้อมกัน. นี่คือคอขวดทางเทคนิคจริงข้อแรกที่จะเจอ.
5. **n8n workflow + webhook เดียว** — ทุกสาขา funnel เข้า execution queue เดียว ไม่มี isolation.

**ทิศทางแก้:** เพิ่มมิติ `branch_id` ใน State+Appointments, ย้าย branch config (ที่อยู่/หมอ/ราคา/admin userId) ออกเป็น **lookup table ใน Sheet หรือ env** แล้ว inject เข้า prompt ตาม branch, route admin notify ตาม branch, และเมื่อ write volume โต → ย้ายจาก Sheet ไป DB จริง (หรืออย่างน้อย Apps Script + LockService ตาม Q6 #3). แต่ละสาขาแยก LINE OA → อาจแยก webhook path ต่อสาขาเพื่อ isolation. **อย่าทำตอนนี้ถ้ายังสาขาเดียว** — overkill; แต่ design `branch_id` เข้า schema ตั้งแต่ T8 จะถูกที่สุด (migration ทีหลังเจ็บ).

**Q8.5 — แก้ security ใน n8n ให้ถูกวิธี: Credentials ชนะ env var.**

**ใช้ n8n Credentials (Header Auth)** สำหรับ LINE token — ดีกว่า env var:
1. ใน LINE Developers console → **rotate Channel Access Token ทันที** (ตัวเก่าถือว่ารั่ว).
2. n8n → Credentials → New → **"Header Auth"** ตั้งชื่อ `LINE Messaging API`: Name=`Authorization`, Value=`Bearer <token-ใหม่>`.
3. ทั้ง 4 HTTP nodes (Reply to LINE, Reply Handoff Start, Reply Handoff End, Reply Handoff Active) + Push Notify Admin → ตั้ง **Authentication = Generic Credential Type → Header Auth → เลือก credential นี้** แล้ว **ลบ header `Authorization` plaintext ออกจาก node**.
4. Gemini key + Channel Secret → ทำแบบเดียวกัน (Gemini: Header Auth `x-goog-api-key` หรือ Query Auth credential แทน key ใน URL).

**ทำไม Credentials > env var:**
- Credentials **เข้ารหัส at rest** (ด้วย `N8N_ENCRYPTION_KEY`) และ **ไม่ถูก export ออกมาใน workflow JSON** → ต่อให้แชร์/commit workflow ก็ไม่หลุด. นี่แก้ root cause ของ C1 ตรงจุด.
- env var (`$env.LINE_...`) บน **n8n Cloud ตั้ง custom env var ไม่ได้/จำกัดตามแพลน**, และค่า env อ่านได้ผ่าน expression โดยใครก็ตามที่แก้ workflow ได้ — ป้องกันน้อยกว่า.
- **ข้อยกเว้น:** Code node ("Verify LINE Signature") ใช้ credential ตรงๆ ไม่ได้ → channel secret ตัวนี้จำเป็นต้องอ่านจาก `$env` (หรือ Cloud variables). นี่เป็นเคสเดียวที่ env var เหมาะกว่า.

**ลำดับ:** rotate token (LINE console) → สร้าง Header Auth credential → สลับ 5 nodes ไปใช้ → ลบ plaintext → ถือว่า token เก่า burned (เพราะอยู่ใน git history แล้ว — `git filter-repo`/BFG ลบ history ได้ แต่ rotate คือสิ่งที่กันจริง).

---


**Status:** pending

**Bug:** chatbot LINE คลินิก Alonsi — บอท reset กลับ step 0 ("สวัสดีค่ะ ยินดีต้อนรับ / ขอทราบชื่อ") ทุกครั้งที่รับข้อความที่ 3 (surname), ทั้งที่ step 1 (name) ทำงานถูกต้อง

**Observed pattern:**
1. ข้อความที่ 1 (ทุก text) → bot: "สวัสดีค่ะ / ขอทราบชื่อ" ✓ (case 0)
2. ข้อความที่ 2 (ชื่อ เช่น "นาส") → bot: "ขอบคุณค่ะ คุณ นาส / ขอทราบนามสกุล" ✓ (case 1)
3. ข้อความที่ 3 (นามสกุล เช่น "วสว") → bot: "สวัสดีค่ะ ยินดีต้อนรับ / ขอทราบชื่อ" ✗ (case 0 ซ้ำ!)

**State Machine logic (JavaScript, n8n Code node):**
```javascript
const prev = $('Read State').first().json || {};
const step = prev.userId ? (Number(prev.step) || 0) : 0;
```
→ case 0 triggered เมื่อ `step === 0` ซึ่งเกิดได้ใน 2 กรณี:
- A. `prev.userId` เป็น falsy (Read State คืนค่าว่าง / ไม่เจอ row)
- B. `prev.userId` มีค่า แต่ `prev.step` = "", null, 0, undefined → `Number(prev.step) || 0 = 0`

**n8n Workflow structure:**
```
Webhook1 → Parse LINE Message → If → Read State → State Machine → If1 → Save State (true) → Reply to LINE
                                                                         → Append row (false) → Delete rows → Reply to LINE
```

**Node configurations (verified):**
- **Read State**: Google Sheets "Get Row(s)", Sheet=State, filter: column=`userId`, value=`{{ $('Parse LINE Message').item.json.userId }}`
- **State Machine**: Code node, output: `{ json: { userId, replyToken, replyText, stateData } }`
- **If1**: `{{ $json.stateData.step }}` NOT equal to `99` (Convert types: ON)
- **Save State**: Google Sheets "Append or Update Row", Sheet=State, Column to match on=`userId`, Values mapped: `userId={{ $json.userId }}`, `step={{ $json.stateData.step }}` (+ อาจมี field อื่น scroll ไม่เห็น)

**State tab schema (Google Sheets):**
`userId | step | name | surname | phone | procedure | doctor | preferred_time | updated_at`

**ที่ทำแล้ว (ไม่ช่วย):**
- ลบ row ขยะใน State tab ออกหมด (เคยมี 13 rows ของ userId เดียว)
- ตั้ง Column to match on = userId ใน Save State ✓
- Save State OUTPUT ก่อนหน้า (execution step=99): แสดง step=99, name=ฟิรฮานา (เขียนได้)

**Hypotheses to evaluate:**
1. Save State appendOrUpdate append new row แทน update → State tab มี 2 rows → Read State คืน row แรก (step=1 เก่า) → case 1 ซ้ำ (แต่ไม่ match เพราะ bot ขึ้น case 0 ไม่ใช่ case 1)
2. Save State update row แต่ไม่ได้เขียน `step` field (field missing ใน mapping) → row มี userId แต่ step="" → `Number("") || 0 = 0` → case 0 ✓ **(likely)**
3. Delete rows node ลบ row ผิด → State tab ไม่มี row สำหรับ userId นี้เลย → Read State empty → prev.userId falsy → case 0 ✓ **(likely)**
4. If node (ก่อน Read State) routing บาง event ผิดทาง

**Question:**
1. Root cause คือข้อไหน? มีวิธี verify อย่างไร?
2. Fix ที่ถูกต้องใน n8n คืออะไร (เขียน step-by-step ให้ Sonnet ทำ)?
3. มี edge case อื่นที่จะทำให้ step reset โดยไม่ตั้งใจไหม?

### ANSWER (Opus, 2026-06-25)

**Root cause (ตัดสาเหตุจากหลักฐาน):** ข้อความที่ 2 บอทตอบ `case 0` ไม่ใช่ `case 2` → ถ้า Save State (case 1) บันทึก `step=2` สำเร็จ ข้อความถัดไปต้องอ่าน step=2 → case 2. การที่ได้ greeting (case 0) พิสูจน์ว่า **`step` ไม่ persist**. เหลือ 2 ทาง:
- **(ก)** appendOrUpdate **append row ซ้ำ** (match `userId` ไม่ติด) → State tab มีหลาย row → `$('Read State').first()` อ่าน row เก่าที่ step ว่าง.
- **(ข)** update row จริงแต่**เขียนช่อง `step` เป็นค่าว่าง**.
ทั้งคู่ → `Number("") || 0 = 0` → case 0. กับดักคือ numeric step ทำให้ "ว่าง/0/ไม่เจอ" ยุบรวมเป็น "user ใหม่" หมด → reset เงียบๆ มองไม่เห็น.

**Verify (decisive, คลิกอย่างเดียว):** reproduce reset แล้วดู 3 จุด — (1) Read State OUTPUT ของข้อความที่ reset: มี row ไหม? `step`=อะไร? (2) Save State OUTPUT ของข้อความก่อนหน้า: updated หรือ appended? step มีค่าไหม? (3) State tab: userId นี้มีกี่ row? 2+ row = (ก); 1 row step ว่าง = (ข); 0 row = userId filter ผิด source.

**Fix → T9 ใน for-sonnet/tasks.md.** Phase 1 = fix ให้ persist (รับมือทั้ง ก/ข). Phase 2 (hardening) = เปลี่ยน step เป็น string label ตาม T8 design เพื่อกำจัดกับดัก numeric ถาวร.

---

## Q5 — Two-tier knowledge index (chapter-level retrieval)
**Status:** done (Opus, 2026-06-24) — design below. Sonnet executes T6. Build AFTER T5's structured-md flow exists; can also run standalone now (AI LI structured md already exists).

**Problem (user, 2026-06-24):** เขาเรียนการลงทุนหลายเรื่อง อยากเก็บเป็นคลังความรู้ แต่ตอนค้นหา **ไม่อยากให้ Claude อ่านเนื้อหาทุกไฟล์ทุกครั้ง** — อยากมี index ที่บอกว่าอันไหนเกี่ยว แล้ว "วาร์ป" ไปอ่านเฉพาะตรงนั้น. Granularity = **ระดับบท** (ยืนยันโดย user).

**Design (firm):**

**2-tier retrieval:**
- Tier 1 = `knowledge/KNOWLEDGE_INDEX.md` (generated, เล็ก, อ่านทุกครั้ง) — routing table ระดับบท.
- Tier 2 = เนื้อหาจริง (`source/<topic>/*_structured.md`, transcript ดิบ) — อ่านเฉพาะแถวที่ index ชี้.

**กุญแจ: index generate จาก header ของเนื้อหาเอง → ไม่มีวันเก่า.**
structured md ทุกไฟล์มี `## บทที่ k — <title> [Slide p.X–Y]` + บรรทัด `**ศัพท์/ตัวชี้วัด:** ...` ซึ่งเป็น keyword สำเร็จรูป. สคริปต์ดึงสองอย่างนี้ทุกไฟล์ → ตาราง. Regenerable, deterministic, ไม่เขียนมือ.

**Schema (1 แถว = 1 บท):**
`| topic | บทที่ | ชื่อบท | keywords (จากบรรทัดศัพท์) | pointer (path#chapter) | raw (transcript path) |`
- pointer = ไฟล์ structured md + เลขบท (วาร์ปไปอ่านเฉพาะบทนั้น)
- raw = transcript ดิบ เผื่อต้องการ verbatim ลึกกว่าสรุป (depth ชั้นสอง)

**2 backend แยกตามชนิดคำถาม (เขียนใน retrieval protocol):**
- คำถามเจาะจง "คอร์สพูดว่าไงเรื่อง X" → KNOWLEDGE_INDEX (local, เร็ว, exact quote)
- คำถามสังเคราะห์/ข้ามคอร์ส "เทียบ X vs Y" → NotebookLM (semantic). index column ยังช่วยบอกว่าไป notebook ไหน (ผูกกับ `knowledge/index.md` ที่ register notebook ID ไว้แล้ว)

**Retrieval protocol (document ใน CLAUDE.md + skill):**
```
คำถามเชิงความรู้การลงทุน →
  1. อ่าน knowledge/KNOWLEDGE_INDEX.md เท่านั้น (ถูก)
  2. จับคู่ keyword/หัวข้อ → เลือกแถวที่เกี่ยว
  3. อ่านเฉพาะ pointer ของแถวนั้น (structured md บทนั้น); ถ้าต้องการ verbatim → raw transcript
  4. ตอบพร้อมอ้างอิง path#บท — ห้ามอ่านทั้งคลัง
```

**Integration:** `/publish-course` (T5) ต้องเรียก `build_knowledge_index.py` ต่อท้ายทุกครั้งที่เพิ่มคอร์ส → index อัปเดตเอง.

**แยกไฟล์ให้ชัด:** `knowledge/index.md` = registry ของ NotebookLM notebooks + insights (เขียนมือ, คงไว้). `knowledge/KNOWLEDGE_INDEX.md` = retrieval map ระดับบท (generated, ห้ามแก้มือ). อย่าปนกัน.

Sonnet steps = **T6 ใน for-sonnet/tasks.md.**

---

## Q4 — Design `/publish-course` skill
**Status:** done (Opus, 2026-06-24) — design below. Sonnet executes T5 in for-sonnet/tasks.md. Needs USER go-ahead first (prerequisite P0 = ย้าย repo ออกจาก /tmp).

**Context:**
ผู้ใช้กำลังสร้าง Investment Knowledge Hub ที่ https://crazyliverpool-web.github.io/alonsi-invest/
โดยทุกครั้งที่เรียนคอร์สใหม่จะต้องทำ pipeline เดิมซ้ำ:
1. วาง source files (transcript + PDF) ใน `source/<topic>/`
2. teacher agent สรุปเนื้อหา
3. สร้างไฟล์ HTML สรุปคอร์ส (format เหมือน `source/AI leading indicator/course_summary.html`)
4. เพิ่ม card ใน `index.html` ของ repo `alonsi-invest` (GitHub Pages)
5. push ขึ้น GitHub → deploy อัตโนมัติ

**สิ่งที่มีอยู่แล้ว:**
- `tools/structure_transcript.py` — align transcript → PDF → chapter markdown (ใช้ Haiku)
- `.claude/agents/teacher.md` — อ่าน source/ แล้วสอน/สรุปเป็นภาษาไทย
- `source/AI leading indicator/course_summary.html` — ตัวอย่าง HTML ที่ต้องการ (dark theme, card layout, scroll reveal)
- `/tmp/alonsi-invest/` — local git repo เชื่อมกับ GitHub Pages (branch: main)
- `gh` CLI พร้อมใช้ (authenticated as crazyliverpool-web)

**คำถามสำหรับ Opus:**
ออกแบบ `/publish-course` skill ให้ Sonnet implement โดยตอบ:

1. **Input spec:** skill รับ argument อะไร? เช่น topic name เท่านั้น หรือต้องระบุ source folder, PDF, transcript ด้วย?
2. **Steps ที่ควรทำ:** ลำดับขั้นตอนที่ชัดเจน พร้อม decision point ที่ต้องให้ user confirm ก่อน
3. **HTML generation:** ควรใช้ template เดิม (hardcoded) หรือให้ LLM generate ใหม่ทุกครั้ง? trade-off คืออะไร?
4. **index.html update:** วิธี add card ใหม่ใน index.html อย่างปลอดภัยโดยไม่ทำลาย card เดิม — parse HTML หรือใช้ marker comment?
5. **Scope ของ skill:** ควรทำทุกขั้นตอนใน skill เดียว หรือแบ่งเป็น sub-commands (เช่น `/publish-course preview` vs `/publish-course push`)?
6. **Error handling:** ถ้า source files ไม่ครบ หรือ structure_transcript.py fail ควรทำอะไร?
7. **Skill file location:** ควรวางใน `~/.claude/skills/` (global) หรือ `studio/.claude/skills/` (project-scoped)?

ถ้า Sonnet ต้องทำอะไรก่อน/หลัง Opus ตอบ ให้เขียนใน `for-sonnet/tasks.md` ด้วย

### ANSWER (Opus, 2026-06-24)

**Verified facts that drive the design:**
- `/tmp/alonsi-invest` คือ git repo จริงที่ push GitHub Pages อยู่ — **แต่อยู่ใน `/tmp` จะหายเมื่อ reboot.** ต้องย้ายเป็นที่ถาวรก่อนทำ skill (prerequisite).
- topic ถัดไปมีจริงแล้ว: `source/claude code 101/` — มีแค่ **mp4 ไฟล์เดียว ไม่มี PDF ไม่มี transcript.** แปลว่า skill ต้องรองรับเคส "ไม่มีสไลด์" (summarize จาก transcript ล้วน ไม่ต้อง page-anchor).
- structured markdown ของ AI LI มีครบแล้ว (`session_*_structured.md`) — HTML ควร generate **จาก structured md** (ground truth) ไม่ใช่อ่าน transcript ดิบใหม่.
- `index.html` ปัจจุบัน **hardcoded**: stat "1 หัวข้อ" + card "เร็วๆ นี้" เขียนมือ — เพิ่ม topic ใหม่แบบ insert string จะเปราะ. ต้องเปลี่ยนเป็น data-driven.

**ดีไซน์ที่สรุป (firm decisions — อย่า re-litigate):**

**1. Input spec:** `/publish-course <topic-folder-name>` รับชื่อโฟลเดอร์ใน `source/` เป็น argument เดียว (เช่น `"AI leading indicator"`). Skill derive: `slug` (kebab-case ascii สำหรับ URL), `title` (ตั้งจาก user หรือ default = ชื่อโฟลเดอร์), source files = ทุกอย่างในโฟลเดอร์นั้น. ไม่ต้องระบุ PDF/transcript แยก — skill ตรวจเอง.

**2. HTML generation = LLM pass คุมด้วย component library (ไม่ใช่ template ตายตัว, ไม่ใช่ free-form).**
เหตุผล: แต่ละคอร์สโครงสร้างต่างกัน (LI มี sector table + workshop; คอร์สอื่นอาจไม่มี) → template ตายตัวไม่พอ. แต่ free-form ทุกครั้ง = สไตล์เพี้ยน. ทางออก: **แยก CSS theme + นิยาม component classes ชัดเจน** แล้วให้ LLM emit เฉพาะ body โดยใช้ class ที่มีอยู่.
- แตก `<style>` ก้อนใหญ่จาก course_summary.html ออกเป็น `assets/theme.css` ที่ root ของ repo. ทั้ง `index.html` และทุก `<slug>/index.html` link มาที่ไฟล์เดียวกัน → restyle ทีหลังแก้ที่เดียว.
- นิยาม **component catalog** (class + ตัวอย่าง snippet): `hero`, `section-header`+`section-icon`, `card`, `grid-2`/`grid-3`, `principle`, `mode-card`, `quote`, `badge-*`, `timeline`, `sector-table`, `warning`, `takeaway-grid`, `version-flow`, `role-card`. เก็บไว้ใน skill เป็น reference.
- **Model = Sonnet** สำหรับ pass นี้ (1 ครั้ง/คอร์ส, หน้าจอ user-facing, ภาษาไทย layout ต้องดี — Haiku เสี่ยง). cost จำกัดอยู่แล้ว 1 pass.
- Grounding: ทุก section ต้อง trace กลับ structured md; ห้ามแต่งตัวเลข (กฎเดียวกับ teacher).

**3. index.html = data-driven จาก `topics.json` (ไม่ใช่ string insert).**
สร้าง `topics.json` ที่ root: array ของ `{slug, title, desc, tags[], meta, status, accent}`. การ์ดในหน้าแรก render จาก json ลงในโซน marker `<!-- TOPICS:START --> ... <!-- TOPICS:END -->`. stat "หัวข้อที่เรียนแล้ว" คำนวณจากจำนวน entry. เขียน `build_index.py` เล็กๆ render การ์ดจาก json → เขียนทับเฉพาะในโซน marker. ปลอดภัยกว่า parse HTML, ลบ placeholder hardcoded ทิ้ง.

**4. Scope = skill เดียว 2 phase + confirm gate บังคับ** (ตรงกับกฎที่เพิ่ง save: plan+confirm ก่อน generate):
- `/publish-course <topic>` → **Phase A: BUILD + PREVIEW local + เปิด browser, ไม่ push** → หยุด แสดงให้ user ดู.
- user อนุมัติ → **Phase B: commit + push.**
- ไม่ push เองโดยไม่ confirm เด็ดขาด. (option `--push` ข้ามได้เฉพาะเมื่อ user สั่งชัด).

**5. Error handling — preflight + atomic:**
- โฟลเดอร์ source ว่าง/ไม่มี → STOP บอก user.
- ไม่มี transcript แต่มี mp4 → เสนอรัน `vad_transcribe.py` ก่อน (งานยาว — ขอ confirm).
- ไม่มี PDF → summarize จาก transcript ล้วน, ข้าม `structure_transcript.py` page-anchoring (เคส claude code 101).
- มี PDF + transcript แต่ยังไม่มี structured md → รัน `structure_transcript.py` ก่อน.
- tool ใด fail → STOP, รายงาน, **ห้ามเขียนไฟล์ครึ่งๆ ลง repo.**

**6. Skill location = project-scoped:** `studio/.claude/skills/publish-course/SKILL.md`. ผูกกับ `source/` ของ studio + repo alonsi-invest → ไม่ควร global (จะรกโปรเจกต์อื่น).

**Pipeline สรุป:**
```
/publish-course "<topic>"
  → preflight: หา transcript/PDF/structured md ในโฟลเดอร์ (เติมส่วนที่ขาด, ขอ confirm ถ้างานยาว)
  → [Sonnet pass] structured md → HTML <main> body (ใช้ component classes, grounded, ไทย)
  → wrap ใน shell (head+theme.css+nav+footer) → web/alonsi-invest/<slug>/index.html
  → update topics.json → build_index.py render การ์ด + stat ในหน้าแรก
  → เปิด browser preview → STOP ขอ user อนุมัติ
  → [อนุมัติ] git add/commit/push → GitHub Pages deploy
```

Sonnet execution steps เขียนไว้ที่ **T5 ใน for-sonnet/tasks.md.**

---

## Q6 — Architecture: Google Sheets ใน Alonsi Clinic chatbot (LINE/n8n)
**Status:** done (Opus, 2026-06-25) — design below. Sonnet executes **T8** in for-sonnet/tasks.md.

**บริบท:** chatbot คลินิกทันตกรรม (production, คนไข้จองนัดผ่าน LINE 24/7) ผ่าน n8n state machine. อยากให้ state persistent + เก็บ appointment จริงใน Google Sheet "Alonsi Clinic Bookings" (tab State + Appointments). เพิ่งเปลี่ยน google-sheets-mcp เป็น HTTP transport แล้วเจอปัญหา "server ต้องรันก่อน Claude Code เปิด + รันตลอด".

### ANSWER (Opus, 2026-06-25)

**หลักตัดสินใจ:** นี่ production chatbot คนไข้จริง ไม่ใช่ tool ส่วนตัว → เลือกจากมุมทนทาน/รันเอง/latency ต่ำ/ไม่เผา token.

**Q6.1 — Access pattern → Option B (n8n เรียก Google Sheets API ตรง) ชนะขาด.**
Booking = deterministic state machine ไม่ต้องใช้ LLM reasoning อ่าน/เขียน Sheet. Option A (n8n→Claude→MCP→Sheet) เอา LLM ที่ช้า/แพง/non-deterministic มาคั่นงานที่ต้องเร็ว+แน่นอน = ผิดหลัก: เผา token ทุก request, เพิ่ม latency หลายวินาที, เพิ่ม 3 process ที่ต้องรันพร้อมกัน (MCP ดับตี 2 = จองไม่ได้). Option C (Apps Script) = escalation เฉพาะตอนต้อง atomic write/Sheet-side logic, ไม่ใช่ default. LLM ใช้เฉพาะ node ตีความภาษาคนไข้ (intent) ไม่ใช่ DB I/O.

**Q6.2 — google-sheets-mcp มีประโยชน์ไหม → แยก 2 use case.**
production chatbot = ไม่ใช้ MCP เลย (Option B). Claude Code อ่าน/วิเคราะห์ booking data เป็นครั้งคราว = มีประโยชน์ แต่ **เลิก HTTP transport** (มันสร้างปัญหา always-on เอง). ใช้แทน: built-in `Google_Drive` MCP ที่มีในนี้อยู่แล้ว (account เดียวกัน ไม่ต้องตั้ง server) หรือ stdio transport (Claude Code spawn/ปิดเอง ไม่มี process ค้าง). ไม่ต้องตั้ง Launch Agent.

**Q6.3 — Schema + concurrency:** State tab key = `line_user_id` (8 cols: line_user_id, step, name, phone, preferred_date, dentist, treatment_type, updated_at). Appointments tab append-only (11 cols, มี appointment_id, status, created_at). Concurrency: (1) update by matching column `line_user_id` ไม่ใช่ row number, (2) serialize/debounce webhook ของ user เดียวกัน, (3) ถ้ายังชน → Apps Script LockService (atomic), (4) TTL cleanup ลบ State เก่า >30 นาที. Google Sheet ทนพอสำหรับคลินิกเดียว — อย่า over-engineer.

**Q6.4 — Sonnet tasks → T8 ใน for-sonnet/tasks.md (schema เต็ม + n8n wiring + concurrency steps + verify).**

---

## Q11 — Facebook Messenger: แยก workflow หรือรวม workflow เดียวกับ LINE?
**Status:** done (Opus, 2026-07-01) — คำตอบด้านล่าง. Sonnet executes **T13**.

**Context:**
- คลินิก Alonsi มี LINE Bot ทำงานอยู่แล้ว (n8n workflow ID: GFdRhaxbgbxvIPjw)
- ต้องการเพิ่ม Facebook Messenger Bot ให้ทำงานเหมือนกัน (Gemini-based booking/FAQ)
- Use case: คนไข้ทักมาเอง (ไม่ต้อง push — ไม่ติด App Review)
- Google Sheets เดิม: State, Appointments, Contacts (กำลังสร้าง P2)
- Gemini system prompt เดิมใช้ร่วมได้

**คำถาม:**
1. แยก workflow vs รวม workflow เดียว — อะไรดีกว่าสำหรับ production คลินิก?
2. ถ้าแยก: share Gemini system prompt ยังไง (copy paste หรือ sub-workflow)?
3. Facebook State ควรใช้ Google Sheets tab เดิม (State) หรือแยก tab?
4. userId ของ Facebook (sender.id) ปนกับ LINE userId ใน Contacts sheet ได้ไหม ควรเพิ่ม column `platform` ไหม?
5. มีข้อควรระวังอะไรเป็นพิเศษสำหรับ Facebook Messenger webhook บน n8n?

### ANSWER (Opus, 2026-07-01)

**กรอบที่ใช้ตัดสิน (ตรวจจาก `n8n-workflow.json` จริง — 24 nodes):** workflow LINE ปัจจุบันเป็น **monolith** ที่เอา "ขอบเฉพาะแพลตฟอร์ม" ห่อ "สมองกลาง" ไว้:
- **ขอบเฉพาะ LINE** (ต้องมีของ FB เวอร์ชันของมันเอง): `Webhook1`, `Verify LINE Signature`, `Parse LINE Message`, `Reply to LINE`, `Push Notify Admin`, `Reply Handoff Start/End/Active`, `Reply Gemini Error` — พวกนี้ผูกกับ event envelope + reply API ของ LINE โดยตรง.
- **สมองกลาง (platform-agnostic เกือบ 100%)**: `Build Gemini Request → Gemini API → Parse Gemini Response`, logic booking (`If1`), และ Sheets I/O ทั้งหมด (`Read State`, `Save State`, `Append row`, `Clear State`, `Log FAQ`, handoff mode). ตรรกะพวกนี้ **เหมือนกันเป๊ะ** ไม่ว่าข้อความมาจาก LINE หรือ FB.

นี่คือ **adapter pattern** แบบตำรา: edge (ต่างกันตามแพลตฟอร์ม) + core (ใช้ร่วม). คำตอบทุกข้อไหลจากตรงนี้.

---

**Q11.1 — แยก workflow ที่ "ขอบ" + ใช้ core sub-workflow ร่วมกันที่ "สมอง". ไม่ใช่แยกสองอันซ้ำทั้งหมด และไม่ใช่ยัดสองแพลตฟอร์มลง workflow เดียว.**

3 ทางเลือก:

| | วิธี | ข้อดี | ข้อเสีย |
|---|---|---|---|
| A | **workflow เดียว 2 webhook (LINE+FB) รวมกลางร่วม** | ไม่ต้อง sub-workflow | graph พันกัน, ปลาย reply ต้อง branch by platform, FB พัง = execution log ปน LINE, แก้ทีเดียวเสี่ยงล้มทั้งสองช่อง |
| B | **2 edge workflows (ช่องละอัน) + 1 core sub-workflow ร่วม** ⭐ | isolation (FB ล่มไม่กระทบ LINE), สมอง = single source of truth, execution log แยกช่อง, deploy/debug แยกกัน | ต้อง refactor สมองออกจาก LINE monolith (งานจริง) + Execute Workflow เพิ่ม latency นิดหน่อย |
| C | **แยกสองอัน copy สมองทั้งก้อน** | ทำเร็ววันแรก | drift แน่นอน — แก้ price list/prompt/บั๊ก C3/C4 ทีต้องแก้ 2 ที่ ลืมที่นึงเมื่อไหร่บอทสองช่องตอบไม่เหมือนกัน. นี่คือคลาสบั๊กเดียวกับ hardcode ที่เราด่าใน Q9 |

**เลือก B.** เหตุผลหลัก: booking brain มี logic ที่กำลังจะแก้อีกเยอะ (M1 skip filter, C3 Gemini fallback, C4 delete race, Q10 confirm flow). ถ้า copy (C) = ต้องแก้ทุกอันสองรอบตลอดไป = รับประกันว่าจะ drift. Sub-workflow ทำให้ **แก้สมองที่เดียว ทั้ง LINE + FB ได้ประโยชน์พร้อมกัน**. สำหรับ production 2 ช่องทาง นี่คือการลงทุนที่ถูกต้อง.

> **สัญญา (contract) ของ core sub-workflow** — edge ส่งเข้า: `{ platform, userId, text, messageId, isAdmin? }` (normalized แล้ว). core ส่งกลับ: `{ replyText, booking_complete, appointment, action }` โดย `action ∈ {reply, handoff_start, handoff_end, error}`. edge เอา `replyText`+`action` ไปยิง API ของแพลตฟอร์มตัวเอง. **core ห้ามรู้จัก LINE/FB API เลย** — แตะแค่ Gemini + Sheets.

**Migration ที่ไม่ทำ LINE พัง (สำคัญ — LINE เป็น production live):**
1. สร้าง core sub-workflow ก่อน (คัด Build Gemini Request→Parse Gemini + Sheets ออกมา).
2. **ทดสอบ core กับ FB ก่อน** (ช่องใหม่ ไม่มีอะไรให้พัง) — FB edge เรียก core.
3. เมื่อ core พิสูจน์แล้วว่านิ่ง → ค่อย refactor LINE ให้เรียก core เดียวกัน แล้วลบสมองซ้ำใน LINE. ทำ LINE **ทีหลัง** เพื่อไม่เสี่ยงกับช่องที่คนไข้ใช้จริงอยู่.

---

**Q11.2 — share Gemini prompt ผ่าน sub-workflow (Execute Workflow) ไม่ใช่ copy-paste.**

Copy-paste system prompt = drift (แก้ price list ที่ LINE ลืมแก้ที่ FB → บอทสองช่องบอกราคาไม่ตรงกัน = หายนะกับคลินิก). วิธี share เรียงตามความดี:
1. ⭐ **prompt อยู่ใน core sub-workflow** (`Build Gemini Request`) — พอใช้ core ร่วม prompt ก็ร่วมอัตโนมัติ ไม่ต้องทำอะไรเพิ่ม. นี่คือผลพลอยได้ของ B.
2. ถ้ายังไม่ refactor core วันนี้ (ทำ C ชั่วคราว): อย่างน้อยเก็บ system prompt ใน **n8n Variable** `$vars.CLINIC_SYSTEM_PROMPT` (Pro upgrade จาก Q9 ปลดล็อกให้แล้ว) ให้ทั้งสอง workflow อ่านตัวเดียวกัน. แก้ที่ Variable ที่เดียว. แต่ Variable share แค่ "string prompt" ไม่ได้ share ตรรกะ booking/parse/state → ยังต้อง maintain สมองซ้ำ. **ด้อยกว่า sub-workflow.**

→ ถ้าทำ B ตามข้อ 1 คำถามนี้หายไปเอง.

---

**Q11.3 — ใช้ State tab เดิม (อันเดียว) แต่เปลี่ยน key เป็น composite `platform:userId`.**

**อย่าแยก tab.** State เป็นข้อมูล ephemeral (เคลียร์ทุกจบ session), volume ต่ำ, มี TTL cleanup job เดียว, schema เดียว. แยก tab = คูณ plumbing สองเท่าโดยไม่ได้อะไร (ต้อง cleanup 2 job, อ่าน 2 ที่).

**แต่มีกับดัก:** ปัจจุบัน `Read State`/`Save State` match แถวด้วยคอลัมน์เดียว `userId`. FB `sender.id` (PSID) กับ LINE userId เป็น **ID คนละ namespace** — โอกาสชนกันต่ำแต่ **ไม่การันตีว่าไม่ชน** และเชิงความหมายมันคนละคน. ทางแก้ที่ทนที่สุด:
- เพิ่มคอลัมน์ `state_key` = `platform + ':' + userId` (เช่น `line:Uxxxx`, `facebook:1234567890`) แล้ว **match appendOrUpdate ด้วย `state_key` คอลัมน์เดียว** — robust กว่า multi-column match ใน n8n (ซึ่งเปราะ).
- (ทางเลือก) เพิ่มคอลัมน์ `platform` แยกไว้ debug/อ่านง่ายด้วยก็ได้ แต่ key ที่ใช้ match คือ `state_key`.

เขียนใน core sub-workflow ที่เดียว → ทั้งสองช่องได้ isolation ของ state ฟรี.

---

**Q11.4 — ปนใน Contacts sheet เดียวได้ แต่ต้องมี `platform` column + generalize `line_user_id` → `user_id`. Contacts composite key = `(hn, platform, user_id)`.**

FB PSID เป็น **page-scoped id** (สเกลตาม Page, ไม่ใช่ FB profile id จริง, และถ้าคลินิกมีหลาย Page คนเดียวได้ PSID คนละตัว) — คนละ namespace กับ LINE userId **ห้ามสมมติว่า unique ข้ามแพลตฟอร์ม**. ปรับ schema Contacts (ที่ Q10.1 ออกแบบไว้):
- rename `line_user_id` → `user_id` (generic)
- เพิ่ม `platform` ∈ `line | facebook`
- composite key จริง = `(hn, platform, user_id)` (ต่อยอดจาก Q10.1 ที่เป็น `(hn, line_user_id)`).

ผลดี: confirmation cron (Q10) lookup ด้วย `hn` → ได้ row กลับมาพร้อมรู้ว่าอยู่ platform ไหน → เลือกยิง push ช่องที่ถูก. Future-proof.

> 🔴 **แต่มีข้อจำกัดใหญ่ที่ต้องรู้ก่อน (กระทบ Q10 cron โดยตรง):** FB Messenger มีกฎ **24-hour window** — ส่งข้อความ freeform หาคนไข้ได้เฉพาะภายใน 24 ชม. หลังคนไข้ทักครั้งล่าสุด. นอกหน้าต่างนี้ต้องใช้ **Message Tag** ที่ได้รับอนุมัติ ซึ่ง **appointment reminder ทั่วไปไม่มี tag ที่ใช้ได้ตรงๆ** (ต่างจาก LINE push ที่ยิงได้ทุกเมื่อในโควตา). **สรุป: confirmation cron ของ Q10 ใช้กับ contact LINE ได้ แต่กับ contact FB มักถูกบล็อกถ้าเกิน 24 ชม.** → cron ต้องเช็ค `platform`: LINE → push ได้; FB → ถ้าเกิน window ให้ตกลง "call list" (โทรเอง) แทน อย่าพยายาม push แล้วเงียบหาย. อย่าออกแบบ cron โดยสมมติว่า FB = LINE.

---

**Q11.5 — ข้อควรระวัง FB Messenger webhook บน n8n (เรียงตามความร้ายแรง):**

1. 🔴 **Echo loop (message_echo).** FB ส่ง event `message_echo` กลับมา**ทุกครั้งที่ Page ส่งข้อความออก** (คือ reply ของบอทเอง). ถ้าไม่กรอง `messaging[].message.is_echo === true` ทิ้ง → บอทประมวลผล reply ตัวเอง → **loop ไม่จบ + เผา Gemini รัว**. นี่คือ M1 (skip filter) เวอร์ชัน FB แต่**อันตรายกว่าเยอะ** เพราะเป็น loop จริง ไม่ใช่แค่ junk row. Parse FB ต้อง drop: echo, `delivery`, `read`, และ event ที่ไม่มี `message.text`. **ห้ามพลาดข้อนี้.**
2. 🔴 **Verify token handshake (GET).** ตอน register webhook FB ยิง **GET** พร้อม `hub.mode`, `hub.verify_token`, `hub.challenge`. n8n ต้องตอบ GET ด้วยการ echo `hub.challenge` เป็น plain text **ถ้า verify_token ตรง**. LINE เป็น POST-only แต่ FB ต้องรับ **ทั้ง GET (verify) และ POST (events)**. n8n webhook node จับ method เดียว → ต้อง**ทำ webhook node แยกสำหรับ GET** (Respond node คืน `hub.challenge`) บน path เดียวกัน หรือใช้ node ที่ตั้งรับหลาย method. ตั้ง "Respond: Using Respond to Webhook node" เพื่อคืน challenge ดิบ.
3. 🔴 **X-Hub-Signature-256 (เทียบเท่า C2 ของ LINE).** FB เซ็น POST body ด้วย **HMAC-SHA256 ด้วย App Secret** ใส่ header `X-Hub-Signature-256: sha256=<hex>`. ต้อง verify (webhook public ใครก็ยิงปลอมได้ = จองปลอม/เผา Gemini/spam admin). ต่างจาก LINE: LINE ใช้ base64 ใน `X-Line-Signature`; **FB ใช้ hex prefix `sha256=`**. เขียน verify node ของ FB เอง อย่า copy ของ LINE ตรงๆ (encoding คนละแบบ).
4. 🟡 **Batching — entry[] มีหลาย messaging[].** FB ส่งได้หลาย event ต่อ 1 POST. Parse FB ต้อง **loop ทุก entry/messaging** ไม่ใช่หยิบ `[0]` แบบ LINE (`events[0]`). ไม่งั้น event ที่ 2+ หาย.
5. 🟡 **Idempotency ด้วย `message.mid`.** FB retry เมื่อไม่ได้ 200 ทัน → เสี่ยงประมวลซ้ำ = จองซ้ำ. dedup ด้วย `message.mid` (เหมือน gap ที่ LINE ก็ยังไม่มี — ทำใน core ทีเดียวได้ทั้งสองช่อง).
6. 🟡 **Page Access Token = credential/Variable เท่านั้น ห้าม hardcode** (บทเรียน C1). Token เป็น per-Page. + Gemini/token ทุกตัวใน FB edge เก็บแบบเดียวกับที่ Q9 สรุป.
7. 🟡 **Send API ต่างจาก LINE reply.** FB ไม่มี `replyToken` — ยิง `POST /me/messages` ด้วย `{recipient:{id: PSID}, message:{text}}` + `PAGE_ACCESS_TOKEN`. ส่งได้ตลอดใน 24h window (ไม่ใช่ one-shot แบบ replyToken). edge FB เขียน reply node ของตัวเอง.
8. 🟠 **App Review / Advanced Access — กับดักที่ user ประเมินต่ำไป.** "คนไข้ทักมาเอง ไม่ต้อง push → ไม่ติด App Review" **จริงแค่ตอนทดสอบกับ admin/tester ของแอป**. พอจะให้ **คนไข้ทั่วไป (ที่ไม่ใช่ role ในแอป)** ทักได้ → ต้องมี **Advanced Access ของ permission `pages_messaging`** ซึ่งต้องผ่าน **App Review + Business Verification**. → **FB serve คนไข้จริงต้องผ่าน App Review อยู่ดี** (แค่ไม่ใช่เพราะ push แต่เพราะ pages_messaging สำหรับ public). ต้องยื่นเรื่องนี้แต่เนิ่นๆ (ใช้เวลาตรวจหลายวัน). อย่าเพิ่ง promise คลินิกว่าเปิดใช้ได้ทันที.
9. 🟢 **ตอบ 200 เร็ว.** FB คาด 200 ในไม่กี่วินาที ไม่งั้น retry. Gemini ช้า → พิจารณาให้ webhook ตอบ 200 ก่อนแล้วประมวลผล async (แต่ n8n sync ก็มักทันถ้า Gemini ไม่ค้าง — ผูกกับ C3 fallback).

**สรุป:** ทำ **B (edge แยก + core sub-workflow ร่วม)**; State tab เดิม + key `platform:userId`; Contacts เพิ่ม `platform` + generalize `user_id`; ระวัง echo-loop / GET-challenge / X-Hub-Signature / App Review / 24h-window เป็นพิเศษ. งานนี้ควรทำ **หลัง** M1+C3 (สมองยังมีบั๊กที่จะ inherit เข้า FB) — ดูลำดับใน T13. Sonnet execution → **T13 ใน for-sonnet/tasks.md.**

---

## Q12 — บอทตอนนี้ (production) แนะนำอะไรเพิ่มไหม? และ n8n + Gemini คุ้มค่าเงินไหม ทำไงให้คุ้มขึ้น?
**Status:** done (Opus, 2026-07-01) — cost หลักคือ n8n Pro (fixed) ไม่ใช่ Gemini (Flash + prompt ~3k token = แทบฟรี); prompt caching ผลตอบต่ำ อย่าเพิ่งทำ; ทำ M3/M4 + ยืนยัน failure rate + เก็บ 3 ตัวเลขก่อนฟันธง. Sonnet executes **T14**.

**คำถามจาก user (2026-07-01, ตรงๆ):**
1. "มีอะไรแนะนำเกี่ยวกับบอทไหม" — มองภาพรวมตอนนี้แล้วมีอะไรควรทำต่อ/ระวังไหม
2. "ตอนนี้ใช้ n8n + Gemini ได้คุ้มค่าไหม" — คุ้มกับเงินที่เสียหรือเปล่า
3. "ทำไงให้คุ้มค่าที่เสียเงิน" — ถ้าไม่คุ้ม/คุ้มไม่เต็มที่ ควรปรับอะไรเพื่อลด cost หรือเพิ่ม value ต่อบาทที่จ่าย

**สถานะบอทล่าสุด (สรุปจากเซสชันนี้ 2026-07-01):**
- Production ทำงานปกติ ✅ (bot: คุกกี้, LINE only, ยังไม่มี FB)
- Fix ที่เสร็จรอบนี้: T10 ทั้งชุด (C1-C4, M1), T11 (Pro plan + Variable), ราคา Mini-Screw, และล่าสุด — **แก้เพศหมอในระบบ prompt** (หมอซี/หมอโฟร์ = ชาย ที่ Gemini เคยเดาผิดว่าเป็นหญิงหมด) ผ่าน n8n API ตรง (PUT workflow) — ยืนยันขึ้น live แล้ว
- Stack: n8n Cloud **Pro plan** (อัปเกรดแล้วตาม Q9) + Gemini 2.5 Flash ผ่าน REST API (`$vars.GEMINI_API_KEY`)
- ค้างอยู่: T12 (ยืนยันนัดอัตโนมัติ, รอ OPD CSV), T13 (Facebook Messenger — design เสร็จแล้วใน Q11 แต่ยังไม่ execute)
- **ไม่มีข้อมูล** ที่ Sonnet เห็นได้ตอนนี้เรื่อง: จำนวนข้อความ/เดือนจริง, ค่า n8n Pro ต่อเดือน, ค่า Gemini API ต่อเดือนจริง, failure rate ปัจจุบัน (ค่าเก่าที่เคยเห็นคือ 45.5% ก่อน fix รอบนี้ — ไม่รู้ตอนนี้เท่าไหร่แล้ว)

**สิ่งที่ Opus น่าจะต้องถาม user เพิ่มก่อนตอบเรื่อง cost:**
- ปริมาณข้อความ/เดือนจริง (n8n execution count ดูได้ใน Overview)
- แผน n8n Pro ราคาเท่าไหร่/เดือน (workflow เท่านี้ใช้ features ของ Pro คุ้มไหม เทียบกับใช้แค่ Variables ฟีเจอร์เดียว)
- Gemini 2.5 Flash cost ต่อ request (prompt ยาวแค่ไหน — ตอนนี้ systemPrompt ทั้งราคา+ทีมแพทย์+สิทธิ/ประกันส่งซ้ำทุกข้อความ ไม่มี caching)

**มุมที่น่าจะคุ้มค่าตรวจสอบ (ข้อสังเกตจาก Sonnet ระหว่างแก้บั๊กรอบนี้ ไม่ใช่คำแนะนำเต็มรูป):**
- ทุกข้อความส่ง systemPrompt เต็ม (ราคา+เวลา+ทีมแพทย์+สิทธิ์+ขั้นตอนจอง ฯลฯ) ซ้ำไปที่ Gemini ทุกครั้ง ไม่มี prompt caching → ถ้าปริมาณข้อความสูง อาจเสีย token cost เกินจำเป็น (Gemini API รองรับ context caching สำหรับ system prompt คงที่)
- ไม่มี monitoring/dashboard ระยะยาวสำหรับ track failure rate หรือ cost ต่อเดือน — เห็นแต่ snapshot ตอนนั้นตอนนี้ใน n8n Overview
- M3 (webhook idempotency), M4 (validate appointment fields) ยังเป็น pending ใน CLAUDE.md ของ repo bot — อาจเกี่ยวกับ "คุ้มค่า" ทางอ้อม (ข้อความซ้ำ = เผา Gemini quota ซ้ำ)

**ขอให้ Opus:**
1. ให้คำแนะนำ 3-5 ข้อ เรื่องบอทตอนนี้ (production-readiness, สิ่งที่ควรทำต่อ, priority)
2. ประเมินว่า n8n Pro + Gemini setup คุ้มค่าไหมเท่าที่มีข้อมูล และระบุชัดว่าข้อมูลไหนยังขาดที่ต้องถาม user เพิ่มก่อนฟันธง
3. เสนอวิธีลด cost / เพิ่ม value ที่ทำได้จริงกับ stack นี้ (เช่น prompt caching, ลด n8n Pro ถ้าไม่คุ้ม, ฯลฯ) พร้อมจัดลำดับความสำคัญ
4. ถ้าคำตอบต้องให้ Sonnet ลงมือทำอะไร → เพิ่ม task ใหม่ใน `for-sonnet/tasks.md`

### ANSWER (Opus, 2026-07-01)

**ข้อค้นพบที่ตรวจจริงจาก workflow (ไม่ใช่เดา):** system prompt ใน `Build Gemini Request` เมื่อ decode แล้ว = **~4,900 ตัวอักษร (Thai ~2,816 ตัว)** ≈ ราว **3,000 token** ของเนื้อหาคงที่ (ข้อมูลคลินิก + ราคา + ทีมแพทย์ + สิทธิ์/ประกัน + ขั้นตอนจอง + JSON schema) ส่งซ้ำ **ทุกข้อความ** ไม่มี caching. ตัวเลขนี้เป็นหัวใจของคำตอบเรื่อง cost ด้านล่าง.

---

**Q12.1 — คำแนะนำเรื่องบอท (จัดลำดับตาม priority):**

| # | สิ่งที่ควรทำ | ทำไม |
|---|---|---|
| 🔴 1 | **M3 — Webhook idempotency (dedup ด้วย `event.message.id`)** | ยัง pending ใน bot CLAUDE.md และ**ไม่มีใน task ไหนเลย**. LINE retry webhook เมื่อไม่ได้ 200 ทัน → ประมวลซ้ำ = **จองซ้ำ + เผา Gemini quota ซ้ำ**. นี่คือทั้ง reliability และ cost win ในตัวเดียว. (Q11 ก็สั่งทำ dedup ใน core อยู่แล้ว — ทำที่ LINE ก่อนได้เลย ไม่ต้องรอ FB) |
| 🔴 2 | **M4 — Validate appointment fields ก่อน Append** | ยัง pending. ตอนนี้ถ้า Gemini คืน field เพี้ยน/ว่าง → เขียนนัดขยะลง Sheet → คนไข้จริงหลุด/หมอสับสน. คลินิกจริงต้องกันข้อมูลเสียก่อนบันทึก |
| 🟡 3 | **ยืนยัน failure rate ปัจจุบัน (หลัง fix รอบนี้)** | ค่า 45.5% เป็นค่า**ก่อน** M1/C3. ต้องเปิด n8n Insights/Executions ดูว่าหลังแก้แล้วดิ่งลงจริงไหม — ถ้ายังสูง = ยังมี root cause อื่น. นี่คือ KPI ว่าที่แก้ไปได้ผล |
| 🟡 4 | **Monitoring รายเดือนแบบเบา** | ตอนนี้เห็นแค่ snapshot. ตั้งนิสัย/routine เช็ค 3 ค่าต่อเดือน: execution count, failure rate, Gemini spend. Pro plan มี Insights อยู่แล้ว (เหตุผลหนึ่งที่ upgrade ตาม Q9) — ใช้มันให้คุ้ม |
| 🟢 5 | **คง git-sync workflow JSON ต่อไป** | ทำอยู่แล้ว (ดี). เป็น backup + versioning ฟรี เผื่อ live พัง rollback ได้ |

> M3 กับ M4 คือ "ของค้างที่ยังไม่มีใครรับ" — T10 จบที่ C1-C4+M1, ส่วน M3/M4 ไม่เคยถูกเขียนเป็น task. **นี่คือ gap จริง** ไม่ใช่ nice-to-have.

---

**Q12.2 — คุ้มค่าไหม? (ประเมินเท่าที่มีข้อมูล + ระบุชัดว่าขาดอะไร)**

**หลักคิดสำคัญ: cost ของระบบนี้แทบทั้งหมดคือ "ค่า n8n Pro รายเดือน (fixed)" ไม่ใช่ค่า Gemini.** เหตุผล:
- Gemini **2.5 Flash** อยู่ tier ถูกที่สุดของ Google + prompt คงที่แค่ ~3k token/ข้อความ. แม้ปริมาณสูง (สมมติ ~3,000 ข้อความ/เดือน × ~3k token ≈ 9M input token/เดือน) ค่า Flash ก็อยู่ระดับ **ไม่กี่ดอลลาร์/เดือน** — เล็กมากเทียบ subscription. (ไม่ระบุตัวเลขเป๊ะเพราะไม่ควรมั่ว pricing — แต่ order of magnitude ชัดว่า Gemini = เศษเงิน)
- ดังนั้น "คุ้มไหม" = คำถามว่า **n8n Pro คุ้มกับราคาที่จ่ายไหม** ล้วนๆ. ซึ่ง Q9 ตอบไว้แล้วว่า **คุ้มบนเหตุผล reliability/security** (Variables เก็บ secret, execution search ไว้ debug 45%, versioning แก้ live ปลอดภัย) — ไม่ใช่คุ้มบนคณิตศาสตร์ token.

**🟡 verdict ยังฟันธงเต็มไม่ได้ ถ้าไม่มี 3 ตัวเลขนี้ (ให้ user ไปดู แล้วบอก Sonnet):**
1. **ราคา n8n Pro/เดือน** — ดูที่ n8n Cloud → Settings → Billing/Plan. (นี่คือ cost ก้อนใหญ่ตัวจริง)
2. **execution count 30 วันล่าสุด** — n8n → Overview/Insights. บอกปริมาณข้อความจริง → ประเมิน Gemini spend + ว่าใกล้ชน limit ของ Pro ไหม
3. **Gemini spend/เดือนจริง** — Google AI Studio / Cloud Console → Billing. (คาดว่าจะเล็กจนน่าตกใจ — ยืนยันสมมติฐานด้านบน)

ถ้า (1) แพงและ execution ต่ำมาก (เช่นวันละไม่กี่สิบข้อความ) → อาจ**ถกได้ว่า Pro overkill**. แต่ security เรื่อง secret (Q9) กับ debugging ยังเป็นเหตุผลให้อยู่ Pro. ถ้า (1) สมเหตุผลและ execution มีปริมาณ → **คุ้มชัดเจน อยู่ต่อ**.

---

**Q12.3 — ลด cost / เพิ่ม value ต่อบาท (จัดลำดับ):**

1. 🟢 **อย่าเพิ่งทำ prompt caching (explicit) ตอนนี้.** เหตุผลตรงๆ:
   - prompt ~3k token บน Flash = ค่า input ถูกอยู่แล้ว. caching จะประหยัด "เศษของเศษเงิน" แต่เพิ่ม complexity (สร้าง cache object, จัดการ TTL, มีค่า storage ของ cache เอง) — **ROI ต่ำที่สเกลคลินิกเดียว**.
   - Gemini **2.5 Flash มี implicit caching อัตโนมัติอยู่แล้ว** สำหรับ prefix ที่ซ้ำ (system prompt วางต้น request = โดน implicit cache พอดี) → **มีโอกาสได้ส่วนลดฟรีอยู่แล้วโดยไม่ต้องแก้อะไร**. explicit caching จะคุ้มก็ต่อเมื่อปริมาณสูงมากและ Gemini bill โตจริง — ให้ดูตัวเลข (3) ก่อน ถ้าบิลยังเล็ก = ปิดประเด็นนี้.
   - **ทางลด token ที่คุ้มกว่า caching ถ้าอยากลดจริง:** ตัด system prompt ให้กระชับ (ราคาเต็มลิสต์อาจย้ายไปเป็น "ถามแล้วดึงเฉพาะที่เกี่ยว" ได้ในอนาคต) — แต่ **เสี่ยงทำบอทตอบผิด/ขาดข้อมูล** จึงยังไม่แนะนำตอนนี้. prompt ที่ครบ = คุณภาพคำตอบ; อย่าแลกคุณภาพเพื่อประหยัดเศษเงิน.
2. 🔴 **M3 idempotency = การลด cost ที่คุ้มสุด** — กันประมวลข้อความซ้ำ = กันเผา Gemini + กันจองซ้ำ. ได้ทั้ง reliability + cost. (ดู Q12.1 #1)
3. 🟡 **เพิ่ม value ต่อบาท n8n Pro = ใช้ features ที่จ่ายไปแล้วให้ครบ** — Insights (monitoring #4), execution search (debug), versioning. จ่ายค่า Pro อยู่แล้ว ถ้าไม่ใช้ = เสียเปล่า. การ "คุ้มขึ้น" ที่แท้จริงคือรีดประโยชน์จาก plan ที่มี ไม่ใช่ไปลด Gemini ที่ถูกอยู่แล้ว.
4. 🟢 **ก่อนเพิ่ม FB (T13)** — จำไว้ว่า FB จะ**เพิ่ม execution** บน n8n (นับรวม quota Pro) แต่ Gemini ยังถูกเหมือนเดิม. ถ้าจะโตหลายช่อง → execution quota ของ Pro คือตัวที่ต้องจับตา ไม่ใช่ Gemini cost.

**สรุป Q12:** ระบบ**คุ้มบนเหตุผลที่ถูกต้องอยู่แล้ว** (Pro = security+reliability, Gemini = ถูกมาก). อย่าไปโฟกัสลด Gemini/ทำ caching (ผลน้อย) — โฟกัส (ก) ปิด gap M3/M4, (ข) ยืนยัน failure rate ดีขึ้นจริง, (ค) เก็บ 3 ตัวเลข cost เพื่อฟันธงขั้นสุดท้าย. Sonnet execution → **T14**.

---

## Q13 — ควรมี agent/ระบบเฝ้าบอทอัตโนมัติไหม?
**Status:** done (Opus, 2026-07-01) — ไม่ต้องมี agent เฝ้าต่อเนื่อง และไม่ต้องมี routine ถาวร; แต่ควรตั้ง **burn-in check ~7 วัน** (มีวันหมดอายุ) หลัง M3/M4 เพิ่งขึ้น แล้วปิดทิ้ง — เช็ค 3 สัญญาณ (ไม่ใช่แค่ error %) เพราะ silent regression ไม่โผล่ในตัวเลข failure. หลังจากนั้นกลับไป on-demand + เหลือบ Insights รายเดือน. Sonnet executes **T15**.

**บริบทตอนนี้ (2026-07-01, T14 Step 3+4 เสร็จแล้ว):**
- M3 (idempotency) + M4 (validation) deploy ขึ้น production แล้ว, ทดสอบ offline ผ่านหมด (17/17 cases)
- เช็ค execution log จริงจาก n8n API: failure rate ดีขึ้นชัดเจนจาก baseline 45.5% → **2% วันนี้ (1 ก.ค., 81 execution จริง)**. Error ที่เหลือ 2 ตัว = C2 signature verify บล็อก request ปลอมถูกต้อง (ไม่ใช่บั๊ก)
- Trend รายวัน: 24 มิ.ย. 40% → 25 มิ.ย. 92% (ช่วง dev) → 30 มิ.ย. 16% → 1 ก.ค. 2%

**คำถามจาก user (ตรงๆ):** "ตอนนี้มี agent ที่คอยดูเรื่องบอทโดยเฉพาะไหม" แล้วต่อด้วย **"คิดว่าควรมี agent ไหม"**

**สิ่งที่มีอยู่แล้ว (on-demand เท่านั้น ไม่มีตัวไหนรันอัตโนมัติ):**
- `line-bot` agent (`.claude/agents/line-bot.md`) — ผู้เชี่ยวชาญแก้ logic/ออกแบบ ต้องเรียกเอง
- `/linebot-check` skill — เช็ค State sheet (ค้าง) + Appointments แล้วรายงาน ต้องเรียกเอง
- n8n Pro เองมี Insights dashboard อยู่แล้ว (จ่ายเงินไปแล้วผ่าน Q9/Q12)

**Sonnet ตอบเบื้องต้นไปแล้ว (ก่อน consult):** ยังไม่จำเป็น เพราะ failure rate ต่ำมากแล้ว + n8n Insights มีอยู่แล้ว, ถ้าจะทำแนะนำ **scheduled check รายสัปดาห์แบบเบา** (ดึง failure rate เทียบ, แจ้งเฉพาะตอนพุ่ง >10%) ไม่ใช่ agent เฝ้าต่อเนื่อง — เพราะ user ระวังเรื่อง usage cost ([[feedback_opus_plans_sonnet_executes]] — user ซีเรียสเรื่อง usage)

**ขอให้ Opus ช่วยตัดสินให้ชัดกว่านี้:**
1. เห็นด้วยกับแนวทาง "scheduled check รายสัปดาห์" ไหม หรือมีมุมที่ Sonnet มองข้าม (เช่น ควรเช็คถี่กว่านั้นช่วงที่เพิ่งเพิ่ม M3/M4 ใหม่ๆ เพื่อยืนยันว่าไม่พังเงียบๆ, หรือ threshold 10% เหมาะไหมเทียบกับ baseline 2% ปัจจุบัน)
2. ถ้าเห็นด้วยว่าควรทำ — ออกแบบให้ชัดว่า: เช็คอะไร (execution status breakdown? เฉพาะ error message ที่ไม่ใช่ signature-block?), ใช้เครื่องมืออะไรของ studio (ดู `/loop` หรือ `/schedule` skill ที่มีอยู่ใน harness — routine ผ่าน cron), แจ้งเตือนยังไง (ไม่ต้อง proactive message รบกวน user ถ้าไม่มีปัญหา)
3. ถ้าไม่เห็นด้วยกับการตั้ง routine ใดๆ เลย (คงแบบ on-demand อย่างเดียว) — บอกเหตุผลตรงๆ ให้ user ตัดสินใจง่าย
4. ถ้าคำตอบต้องให้ Sonnet ไปตั้งค่าอะไร → เพิ่ม task ใหม่ใน `for-sonnet/tasks.md`

### ANSWER (Opus, 2026-07-01)

**Verdict ตรงๆ (ไม่ hedge):**
- 🔴 **agent เฝ้าต่อเนื่อง (continuous) → ไม่ทำ.** overkill สิ้นเชิงที่ volume คลินิกเดียว ~80 exec/วัน. เผา usage ทิ้งเปล่า.
- 🟡 **routine Claude รายสัปดาห์ "ถาวร" → ไม่ทำ.** นี่คือจุดที่ผม **ไม่เห็นด้วยกับ Sonnet**: steady-state อยู่ที่ 2% แล้ว (และ 2% นั้นคือ C2 บล็อก request ปลอม = ทำงานถูก ไม่ใช่บั๊ก) + n8n Insights จ่ายไปแล้วและโชว์ failure-rate trend ให้ฟรีอยู่แล้ว. การจ่าย token Claude ทุกสัปดาห์ตลอดไปเพื่ออ่านซ้ำสิ่งที่ dashboard บอกฟรี = **ขัด cost discipline ของ Q9/Q12 โดยตรง** (Q12 สรุปชัด: "ใช้ features ที่จ่ายไปแล้วให้คุ้ม ไม่ใช่สร้างของใหม่ทับ"). Claude agent ควรทำเฉพาะสิ่งที่ dashboard **ทำไม่ได้** — ไม่ใช่ทำซ้ำ.
- 🟢 **burn-in check ชั่วคราว ~7 วัน หลัง M3/M4 → ทำ (คุ้ม).** เหตุผลเดียวที่ automation มีค่าเหนือ "เหลือบ Insights เอง" ตอนนี้คือ **M3/M4 เพิ่งขึ้น production** และความเสี่ยงคือ **silent regression** ที่ **ไม่โผล่ใน failure rate เลย** (ดูข้อ 1). คุ้มที่จะเฝ้าเฉพาะหน้าต่างเสี่ยง 7 วันแรก แล้ว **auto-delete routine ทิ้ง** — ไม่ใช่ตั้งค้างถาวร.

**สรุปแนวทาง:** `burn-in 7 วัน (มีวันตาย) → หลังจากนั้น on-demand (line-bot + /linebot-check) + เหลือบ Insights รายเดือน (T14 Step 5)`. ไม่มี automation ยืนพื้น.

---

**Q13.1 — เห็นด้วยกับ Sonnet แค่ครึ่งเดียว. แก้ 2 จุดสำคัญ:**

**(ก) "รายสัปดาห์ถาวร" → เปลี่ยนเป็น "รายวัน แต่มีวันหมดอายุ 7 วัน".** ช่วงที่ต้องเฝ้าถี่คือ **ทันทีหลัง deploy** (จับ regression เงียบให้ไว) ไม่ใช่เฝ้าเบาๆ ตลอดกาล. หลัง 7 วันโค้ดพิสูจน์ตัวแล้ว → cadence ที่ถูกคือ **ศูนย์ (เลิก automation)**, ปล่อยให้ Insights + on-demand รับช่วง. นี่ตรงกับที่ user เอง hint ในคำถามข้อ 1 ("ควรเช็คถี่กว่านั้นช่วงเพิ่ง M3/M4 ใหม่ๆ") — ผมยืนยันว่าใช่ และเพิ่มว่า **ต้องตั้งวันตายไว้เลย** ไม่งั้นมันจะกลายเป็น routine ถาวรที่ลืมปิด = เผา usage เรื่อยๆ.

**(ข) threshold 10% เป็นสัญญาณ "ผิดตัว" สำหรับ regression ที่เรากลัว.** M3 (idempotency/dedup) และ M4 (validation) ถ้าพังจะพังแบบ **เงียบ ไม่ใช่แบบ error**:
- M3 dedup แรงเกินไป → **ทิ้งข้อความจริงของคนไข้** → execution ลดลง/ไม่ตอบกลับ แต่ **ไม่ throw** → failure rate ไม่ขึ้น (อาจดู "ดีขึ้น" ด้วยซ้ำ เพราะ execution น้อยลง).
- M4 validate แรงเกินไป → **ปฏิเสธการจองที่ถูกต้อง** → ไม่มี row ใหม่เข้า Appointments แต่ execution จบ status=success.

→ **error-% threshold มองไม่เห็นทั้งสองเคสนี้เลย.** ดังนั้น threshold 10% (หรือเทียบ baseline 2%) ใช้ได้เฉพาะจับ "error ที่ดังจริง" แต่ **พลาดจุดที่เพิ่ง deploy มา**. ต้องเพิ่มสัญญาณ silent ด้วย (ข้อ 2).

---

**Q13.2 — ออกแบบ burn-in check (ถ้าทำ):**

**เครื่องมือ: `/schedule` (cron cloud agent) — ไม่ใช่ `/loop`.**
- `/loop` รันใน session ที่เปิดค้าง + กิน context ต่อเนื่อง → ไม่เหมาะกับ watcher ข้ามวันที่ user ไม่ได้นั่งเฝ้า.
- `/schedule` = cloud routine ตาม cron, รันเองแล้วจบ, เหมาะกับ "วันละครั้ง 7 วันแล้วตาย" พอดี. ตั้ง cheap model (เช่น Haiku) — งานนี้แค่ดึง API + คำนวณ 3 ตัวเลข + เทียบ threshold ไม่ต้องใช้ปัญญาระดับสูง.

**cadence:** วันละ 1 ครั้ง (เช่น 20:00 หลังคลินิกปิด เห็นข้อมูลเต็มวัน) × **7 วัน แล้ว auto-delete routine**.

**เช็ค 3 สัญญาณ (ดึงจาก n8n execution API — ที่ Sonnet ใช้ verify 2% วันนี้ได้อยู่แล้ว):**
| # | สัญญาณ | trip เมื่อ | จับอะไร |
|---|---|---|---|
| 1 | **non-signature error rate** (แยก C2 signature-block ออกก่อนนับ) | error จริง (ไม่ใช่ signature-block) > ~5 ครั้ง/วัน **หรือ** > 10% ของ exec วันนั้น | error ที่ดังจริง (C3 fallback พัง, Sheet เขียนไม่ได้ ฯลฯ) |
| 2 | **execution count ตกฮวบ** | exec/วัน ต่ำกว่าค่าเฉลี่ย 7 วันก่อนหน้าอย่างมีนัย (เช่น < 50%) | 🔑 M3 dedup ทิ้งข้อความจริง (silent) |
| 3 | **Appointments rows ใหม่ = 0 ทั้งวัน ทั้งที่ exec ปกติ** | 0 row ใหม่ แต่ execution count ยังปกติ | 🔑 M4 reject การจองจริง / booking พังเงียบ (silent) |

สัญญาณ 2+3 คือของที่ **Insights dashboard ทำไม่ได้** — นี่คือเหตุผลเดียวที่ Claude agent มีค่าเหนือการเหลือบ dashboard เอง.

**การแจ้งเตือน: silent-unless-tripped.**
- ทุกสัญญาณเขียว → routine **จบเงียบ ไม่ส่ง message รบกวน user** (เคารพ [[feedback_opus_plans_sonnet_executes]] — user ซีเรียส usage/ไม่ชอบถูก nag).
- มีสัญญาณ trip → ส่ง notification สั้นๆ บอกว่าสัญญาณไหน + ตัวเลข + ชี้ว่าน่าจะเป็น M3 หรือ M4 regression → user เรียก `line-bot` / `/linebot-check` มาสางต่อ.

---

**Q13.3 — ถ้า user เลือกไม่ทำอะไรเลย (คง on-demand ล้วน) ก็ยัง "โอเคอย่างมีเหตุผล" — ไม่ใช่ทางเลือกแย่:**
- `line-bot` agent (แก้ logic) + `/linebot-check` skill (เช็ค State/Appointments) + n8n Insights (จ่ายแล้ว, โชว์ failure trend) = ครอบคลุม steady-state ครบ.
- volume ต่ำ (คลินิกเดียว ~80/วัน) + failure rate 2% ที่ตรวจแล้วว่าเป็น C2 ทำงานถูก = ระบบสุขภาพดี ไม่มีไฟไหม้ให้เฝ้า.
- user เหลือบ Insights 30 วิ/สัปดาห์ + รัน `/linebot-check` เมื่อสงสัย = **cost Claude marginal = 0**.

→ ความต่างเดียวระหว่าง "ทำ burn-in" กับ "ไม่ทำ" คือ **ความมั่นใจว่าโค้ดที่เพิ่งขึ้น 7 วันแรกไม่พังเงียบ**. ถ้า user โอเคที่จะสุ่มเช็ค Appointments เองสัก 2-3 วันแรกว่ายังมีนัดเข้าปกติ → **ข้าม burn-in ได้เลย ประหยัดสุด**. ผมเอนไปทาง burn-in เพราะมันถูก (7 run × cheap model) และปิด blind spot ที่ dashboard มองไม่เห็นพอดี — แต่ **นี่เป็น "nice to have ที่ถูก" ไม่ใช่ "ต้องมี"**. user ตัดสินได้สบายๆ.

**Q13.4 — Sonnet execution → T15** (gated: ต้องรอ user ตอบ go/no-go ก่อน ตั้ง; time-boxed 7 วัน + auto-delete; cheap model; silent-unless-tripped).

---

## Q14 — ปรับ `tools/vad_transcribe.py` ยังไงให้ Whisper hallucinate น้อยลง (เจอปัญหาจริงกับคอร์ส Masterclass)
**Status:** done (Opus, 2026-07-05) — แก้ที่ต้นทาง: `large-v3` เต็มสำหรับคอร์สสอน + enrich initial_prompt + flag-ไม่-ลบ-เงียบ. ข้าม chunking + ข้ามลด threshold. 7 ชม. = sleep ปิดเคสได้. Sonnet executes **T16**.

**บริบท:** เครื่องมือ `tools/vad_transcribe.py` (Silero VAD กรอง noise → MLX `whisper-large-v3-turbo` transcribe → regex ลบ token ซ้ำ 5+ ครั้งติดกัน) คือ fix เดิมที่เคยแก้ hallucination ปัญหาแรกไปแล้ว (ดู [[feedback-whisper-vad-hallucination]] — เคยพังกับ FB Live ก่อนหน้านี้) แต่พอเอาไปถอดคอร์ส **Masterclass ลงทุนศาสตร์** (11 ไฟล์ m4a, รวม ~305+373+38 นาที, รันผ่าน pipeline นี้จริงเมื่อ 2026-07-01/02) เจอปัญหาหลุดรอดมาอีกแบบในหลายจุด:

1. **คำเยอรมันหลุดปนกลางประโยคไทย** เช่น "beispielาย" (แปลว่า "example" ในภาษาเยอรมัน) — โผล่**ครั้งเดียวไม่ซ้ำ** เลยรอดจาก regex ที่จับแต่ token ซ้ำ 5+ ครั้ง
2. **คำอังกฤษ "invalid" หลุดซ้ำๆ** แต่บางจุดซ้ำแค่ 3-4 ครั้ง (ไม่ถึง threshold 5) เลยไม่ถูกลบ
3. ผลคือช่วงที่เจอปัญหาพวกนี้ **อ่านไม่ออกเป็นเนื้อหาจริงเลย** — ทำให้เนื้อหาบางเคส (ยืนยันแล้วว่าผู้สอนพูดถึงหุ้น MC/Mc Jeans จริงในสไลด์หน้า 7) หายไปจาก raw transcript ทั้งประโยค ต้องให้ user เล่าย้อนแล้วเพิ่มเข้า lesson_notes.md เองแบบ manual (ไม่ verify จาก transcript ได้)
4. เวลารันจริงช้ากว่าคาดมาก — day1-1 (105 นาทีเสียง) ใช้เวลา 20:52→04:13 (>7 ชม.) ทั้งที่ VAD บอกกรอง speech เหลือ 98% แล้ว (น่าจะเกี่ยวกับ [[feedback-caffeinate-overnight-jobs]] เรื่อง sleep แต่ไม่ยืนยัน)

**ตัวเลือกที่ Sonnet คิดไว้ (ยังไม่ได้ลงมือแก้ rน้ code):**
| ทำอะไร | Effort | หมายเหตุ |
|---|---|---|
| ใส่ `initial_prompt` เจาะจงคอร์สกว่านี้ (รวมชื่อหุ้น/ศัพท์ที่รู้ล่วงหน้า) | ต่ำ | อาจช่วย bias คำศัพท์เฉพาะ แต่ไม่รู้ล่วงหน้าว่าจะพูดถึงหุ้นตัวไหนบ้างเสมอไป |
| ลด threshold ลบคำซ้ำจาก 5 → 3 | ต่ำ | เสี่ยงลบคำที่ตั้งใจพูดซ้ำจริงๆ (เช่น ย้ำคำสอน) ทิ้งไปด้วย |
| เพิ่มตัวกรอง Latin-script token แปลกปลอมกลางประโยคไทย → flag ไว้ให้ review แทนลบทิ้งเงียบๆ | กลาง | ต้องตัดสินใจ threshold/dictionary คำที่ "รู้จัก" (ticker ภาษาอังกฤษ) vs "ไม่รู้จัก" (hallucination) |
| เปลี่ยนจาก `large-v3-turbo` → `large-v3` เต็ม (ไม่ตัดคำ turbo) | กลาง | แม่นขึ้นแต่ช้าลง คุ้มไหมกับความยาว 300+ นาที/คอร์ส |
| แบ่ง audio เป็น chunk สั้นลง (10-15 นาที) ก่อน MLX แทนไฟล์ยาวเดียว | สูง | ลด long-form drift แต่ต้องแก้ pipeline concat/timestamp tracking |

**ขอให้ Opus ช่วย:**
1. วินิจฉัยว่าสาเหตุ #1/#2 (คำหลุดโดดๆ ไม่ซ้ำ, threshold พลาด) ควรแก้ตรงไหนก่อน — คุ้มไหมที่จะแก้ post-processing regex เพิ่ม หรือควรแก้ที่ต้นทาง (โมเดล/chunk size) แทน
2. เห็นด้วยไหมว่าเปลี่ยนเป็น `large-v3` เต็มสำหรับคอร์สสอน (ต่างจาก quick-transcribe ทั่วไปที่ turbo พอ) — เกณฑ์ตัดสินใจควรเป็นอะไร (ความยาวไฟล์? ความสำคัญของเนื้อหา?)
3. เรื่อง #4 (ช้าผิดปกติ 7+ ชม.) ควรสืบเพิ่มไหม หรือถือว่า caffeinate ไม่ได้ผูกไว้ตั้งแต่ต้น (ไม่ยืนยัน) ก็เพียงพอเป็นคำอธิบายแล้วไม่ต้องสืบต่อ
4. ถ้ามีคำแนะนำที่ต้องแก้ code จริง → เพิ่ม task ใหม่ใน `for-sonnet/tasks.md` ให้ Sonnet ไปทำ (ระบุไฟล์/บรรทัดที่เกี่ยวถ้าเป็นไปได้)

### ANSWER (Opus, 2026-07-05)

**กรอบวินิจฉัยที่คุมทุกคำตอบ: post-processing = ซ่อนอาการ, โมเดล = รักษา.**
อาการ #1 (beispiel), #2 (invalid ซ้ำ 3-4x), #3 (MC หาย) **เป็นโรคเดียวกัน** คือ Whisper เจอเสียงถอดยาก (noise/ดนตรี/crosstalk/SNR ต่ำ) แล้ว decoder เดามั่วเป็น garbage. turbo (decoder เหลือ 4 layer จาก 32 ของ large-v3) **เสี่ยงอาการนี้กว่า** เพราะไม่มีความจุพอจะ "รู้ตัวว่าไม่ชัวร์". จุดตายของ #3: **regex เก่งแค่ไหนก็กู้คำที่ผู้สอนพูดกลับมาไม่ได้** — มันหายตั้งแต่ตอนถอดแล้ว. ดังนั้นการไปขยัน regex (option 2/3 แบบลบ) แก้แค่ "ให้อ่านสะอาด" ไม่ได้แก้ "เนื้อหาหาย" ซึ่งคือ harm จริง. **ตัวรักษาอยู่ต้นทาง.**

**Q14.1 — แก้ที่ต้นทางก่อน, post-processing ทำแค่ให้ "มองเห็น" ไม่ใช่ "ลบ".** ลำดับที่ฟันธง:

| option | ทำ? | เหตุผล |
|---|---|---|
| **4. large-v3 เต็ม** | ✅ **อันดับ 1** | leverage สูงสุด. โจมตี #1/#2/#3 พร้อมกันที่ต้นตอ. บนเสียง**ยาก** (ช่วงที่ผลิต invalid/beispiel พอดี) full decoder ทนกว่า turbo ชัด. "cost = ช้า" ไม่ใช่ปัญหาจริง (ดู Q14.3 — 7 ชม.คือ sleep ไม่ใช่โมเดล) |
| **1. enrich initial_prompt** | ✅ ทำคู่กัน (ถูกมาก) | bias decoder ไปทางไทย-การเงิน → ตัดโอกาสคำเยอรมัน/ภาษาอื่นหลุด (#1). ข้อกังวล "ไม่รู้ ticker ล่วงหน้า" overblown — ไม่ต้องรู้ ticker แค่ context ไทย-การเงินก็พอ |
| **3. flag Latin-token / repeat สั้น** | ✅ แต่ **flag ไม่ลบ** | นี่คือ change ที่กันเคส MC ซ้ำ: เคส MC เนียนหายเงียบจน user จับได้จากความจำเอง. pass ที่แทรก `[?ตรวจสอบ]` ตรงช่วง Latin แปลกปลอม/`invalid` ซ้ำ 2-4x จะ**โชว์** ว่า "จุดนี้น่าสงสัย" ให้ไปเทียบสไลด์. ทำให้ง่ายสุด — อย่าสร้าง ticker dictionary (over-engineer สำหรับ tool ส่วนตัว) |
| **2. ลด threshold 5→3** | ❌ | เสี่ยงลบคำย้ำสอนจริง เพื่อผลนิดเดียว + ยัง "ลบเงียบ" อยู่ดี. เคส `invalid` ซ้ำ 3-4x ให้ option 3 จัดการแบบ flag แทน ดีกว่า |
| **5. chunking 10-15 นาที** | ❌ | effort สูง แก้ long-form **drift** ซึ่ง**ไม่ใช่**อาการที่เจอ (อาการนี้เป็น bad-audio เฉพาะจุด ไม่ใช่ drift สะสม). หลักฐานไม่ชี้ทางนี้ — อย่าทำ |

**Q14.2 — เห็นด้วย: `large-v3` เต็มสำหรับคอร์สสอน, คง turbo สำหรับ quick/ทิ้ง. แต่เกณฑ์ไม่ใช่ "ความยาวไฟล์".**
turbo distill โดย prune decoder แต่**เก็บ encoder เต็ม** → บนเสียงสะอาดแม่นพอๆ กัน, ต่างกันตรง**เสียงยาก + ความ hallucinate** ซึ่งคือปัญหานี้เป๊ะ → เป็นจุดที่ turbo→large-v3 คุ้มที่สุด. เกณฑ์ตัดสิน = **"เนื้อหาถาวร/สำคัญแค่ไหน" ไม่ใช่ "ยาวแค่ไหน"**: ถ้าจะเอาไป structure → NotebookLM → สอนย้ำหลายสัปดาห์ (Masterclass, Master of Valuation) → large-v3. ถ้าถอดครั้งเดียวทิ้ง → turbo. (เหตุผลที่ทิ้งเกณฑ์ความยาว: Sonnet เคยคิดว่า 300+ นาที = ช้าเกินไม่คุ้ม — เกณฑ์นั้น**เป็นโมฆะ**แล้วเพราะ speed ไม่ใช่คอขวดจริง). ทำเป็น `--model` flag (default turbo) → tool ยืดหยุ่น, casual use ยังเร็ว.

**Q14.3 — 7+ ชม. = sleep. เพียงพอ ปิดเคส ไม่ต้องสืบต่อ. หลักฐานชัดใน `pipeline.log`:**

| ไฟล์ | ช่วงเวลา | ใช้เวลา |
|---|---|---|
| **day 1-1 (ไฟล์แรก, launch 20:52 เย็น)** | 20:52 → 04:13 | **7h21m ⚠️** |
| day1-2 | 04:13 → 05:04 | 51m |
| day1-3 | 05:04 → 05:14 | 10m |
| day1-4 | 05:14 → 05:57 | 43m |
| day1-5 | 05:57 → 06:09 | 11m |
| day2-1…Rachathewi (อีก 6 ไฟล์) | 06:09 → 08:21 | 14-36m/ไฟล์ |

ไฟล์เดียวที่ช้าคือ**ไฟล์แรกที่คร่อมหน้าต่าง idle ช่วงกลางคืนที่ไม่มีคนเฝ้า** — อีก 10 ไฟล์ (รวมที่ยาวพอกัน) รันปกติ 10-50 นาที. slowdown ~15-40x เฉพาะไฟล์เดียว = sleep-throttle ตำรา ไม่ใช่บั๊กโมเดล/โค้ด. **ไม่คุ้ม token สืบต่อ** — fix เชิง ops คือผูก `caffeinate -imsu` กับ batch ตั้งแต่ต้น (ตรง memory `feedback_caffeinate_overnight_jobs`).

**Q14.4 — Sonnet execution → T16** (แก้ 3 อย่างในไฟล์เดียว `tools/vad_transcribe.py`: `--model` flag, enrich initial_prompt, flag-ไม่-ลบ pass + ops note caffeinate). **ไม่ทำ** chunking, **ไม่ลด** threshold.

---

## Q15 — ควรเพิ่ม timestamp ใน `tools/vad_transcribe.py` ไหม (ต่อยอด/รวมกับ T16)
**Status:** done (Opus, 2026-07-05) — คุ้ม เพราะ marginal effort ≈ 0 (`ts` + `res['segments']` มีอยู่แล้ว) และมันคือตัวที่ทำให้ marker `[?ตรวจสอบ]` ของ T16 "ใช้งานได้จริง". format = ไฟล์ sidecar `.srt` (map speech-time→original-time) โดย `.txt` ยังสะอาดสำหรับ NotebookLM. **Fold รวมเข้า T16 เป็น Change 5** (ไฟล์เดียว รอบทดสอบเดียว) ไม่สร้าง T17. คำตอบด้านล่าง.

**บริบท:** ระหว่างสอน Masterclass ลงทุนศาสตร์ (ดู Q14 ข้างบน) user ถามหาเนื้อหาที่ "day1-1 นาทีที่ 20" — Sonnet ทำได้แค่**ประมาณตำแหน่งจากสัดส่วนความยาวเสียง** (ไม่มี timestamp จริงให้ค้น) แล้วก็เจอว่าช่วงนั้นในไฟล์ raw transcript พังจาก hallucination อยู่ดี (เอาไปพันกับเคส MC ใน Q14) — สรุปคือ **การไม่มี timestamp ทำให้ mapping "เสียงต้นฉบับ ↔ ข้อความที่ถอด" ทำไม่ได้เลยตอนนี้** ไม่ว่าจะหาเนื้อหา หรือหาช่วงที่ต้องกลับไปฟังเทียบ (เช่นตอน QA เจอจุดต้องสงสัยจาก T16's `[?ตรวจสอบ]` marker ใหม่ — ตอนนี้ก็ยังไม่รู้ว่าต้องเปิดไฟล์ต้นฉบับไปฟังนาทีไหน)

**Output format ปัจจุบัน (จาก docstring บรรทัด 1-6 ของ `tools/vad_transcribe.py`):** "Output is clean Thai text for NotebookLM (no timestamps — speech is concatenated)" — ตั้งใจตัด timestamp ออกแต่แรกเพื่อให้ได้ plain text สะอาดป้อน NotebookLM

**ทำไมไม่ใช่แค่เอา timestamp ดิบจาก `mlx_whisper.transcribe()` มาแปะ:** Whisper คืน timestamp เทียบกับไฟล์เสียงที่ป้อนเข้าไป ซึ่งในโค้ดนี้คือ **`tmp_speech`** = ไฟล์เสียงหลังตัด VAD แล้ว (speech-only, ตัดต่อ segment ที่เว้น silence ออกไปแล้ว คั่นด้วย pad 0.2s ต่อ segment ตามบรรทัด ~33-35) ไม่ใช่ไฟล์ต้นฉบับ (`inp`/`tmp_full`) — ถ้าแปะ timestamp ดิบจาก Whisper ตรงๆ จะ**เพี้ยนจากเวลาจริงในไฟล์ต้นฉบับ** เพราะช่วง silence ที่ VAD ตัดออกไม่ได้ถูกนับ เวลาจะยิ่งเหลื่อมมากขึ้นเรื่อยๆ ตามความยาวไฟล์ (ไฟล์ 100+ นาทีอาจเหลื่อมเป็นนาทีได้)

**สิ่งที่มีอยู่แล้วในโค้ดที่ใช้ mapping กลับได้:** ตัวแปร `ts` (บรรทัด ~28-29, ผลจาก `get_speech_timestamps`) คือ list ของ dict `{start, end}` เป็น **sample index ในไฟล์ต้นฉบับ** (`audio`/`tmp_full`) ของแต่ละ speech segment ที่เก็บไว้ — นี่คือข้อมูลที่ต้องใช้สร้าง mapping function: "เวลาใน speech-only audio" → "เวลาในไฟล์ต้นฉบับ" โดยไล่บวกความยาว pad (0.2s) ที่แทรกระหว่าง segment สะสมไปเรื่อยๆ

**ขอให้ Opus ช่วย:**
1. ตัดสินว่าคุ้มไหมที่จะเพิ่ม feature นี้ (เทียบ effort ที่ต้องทำ mapping function ข้างบน กับประโยชน์ที่ได้ — เจอ use case จริงแล้ว 1 ครั้งใน Q14/MC case)
2. ถ้าคุ้ม ออกแบบ output format ให้ชัด — ตัวเลือกที่ Sonnet คิดไว้ (เลือกให้เลยว่าอันไหน หรือเสนออื่น):
   - (ก) แทรก `[MM:SS]` inline ทุกๆ N คำ/ทุก VAD segment ใน text output เดิม (ยังเป็น .txt เดียว อ่าน NotebookLM ได้เหมือนเดิมแค่มี marker ปน)
   - (ข) output แยกไฟล์ที่สอง (เช่น `.srt` หรือ `.json` ที่มี segment+timestamp) แล้วไฟล์ `.txt` เดิมยังสะอาดไม่มี timestamp ปนสำหรับ NotebookLM
   - (ค) อื่นๆ ที่ Opus เห็นว่าเหมาะกว่า
3. ควรรวม implementation เข้าเป็นการแก้ `tools/vad_transcribe.py` **รอบเดียวกับ T16 เลยไหม** (คนละไฟล์เดียวกัน คนละรอบทดสอบ) หรือแยกเป็น task ใหม่ต่างหากดี — ถ้ารวม ให้แก้ T16 ใน `for-sonnet/tasks.md` ตรงๆ เพิ่ม change ใหม่เข้าไปในนั้นเลย (อย่าสร้าง T17 แยกถ้าควรรวม); ถ้าแยก ค่อยสร้าง task ใหม่
4. เขียนคำสั่งที่ Sonnet (fresh session ไม่มี context นี้) รันตามได้เลย ระบุจุดในโค้ด/บรรทัดที่เกี่ยวถ้าเป็นไปได้ เหมือน T16 เดิม

### ANSWER (Opus, 2026-07-05)

**กรอบที่คุมทุกข้อ: feature นี้ไม่ใช่ของแยก — มันคือชิ้นที่ทำให้ T16 "จบ".** T16 เพิ่ง introduce marker `[?ตรวจสอบ]` ไว้ชี้ว่า "ตรงนี้น่าสงสัย" แต่บนไฟล์ 100+ นาทีที่ไม่มี timestamp **คนอ่านก็ยังไม่รู้ว่าต้องเปิดไฟล์ต้นฉบับไปฟังนาทีไหน** → marker ครึ่งใบ. timestamp คือครึ่งที่ขาด. บวกกับ effort ต่ำผิดปกติ (ข้อมูล map มีครบในโค้ดแล้ว) → คำตอบตรงไปตรงมา.

**Q15.1 — คุ้ม ทำ. เหตุผลที่ชี้ขาดคือ effort/value ratio ไม่ใช่จำนวน use case:**

| ปัจจัย | ประเมิน |
|---|---|
| use case ที่เจอจริง | 1 ครั้งตรงๆ ("day1-1 นาทีที่ 20") **+ use case แฝงถาวร**: ทุก `[?ตรวจสอบ]` ที่ T16 จะ generate ตั้งแต่นี้ ต้องมี timestamp ถึงจะไปเทียบต้นฉบับได้ → ยิ่งใช้ tool ยิ่งเกิดบ่อย |
| marginal effort | **≈ 0 ของงานหนัก** — `ts` (sample index ต้นฉบับ) และ `res['segments']` (text+time) ถูกคำนวณไว้แล้วทั้งคู่ ของใหม่มีแค่ piecewise-map ~35 บรรทัด + เขียน .srt |
| risk | ต่ำ — เขียนไฟล์ที่ **สอง** ครอบ try/except, ไม่แตะ `.txt` เลย → NotebookLM + T4 ไม่กระทบ |
| rides same test pass | ใช่ — ไฟล์เดียวกับ T16, ทดสอบรอบเดียว |

ตัวคูณที่ทำให้ "เจอครั้งเดียว" ไม่ใช่เหตุผลข้าม: ราคาที่จ่ายคือ ~35 บรรทัด once, ผลตอบคือ navigation ถาวรของทุก transcript ในอนาคต. ที่ effort ระดับนี้ ไม่ต้องรอ use case ที่สอง.

**Q15.2 — format = (ข) sidecar `.srt` (map แล้ว). ชนะขาดทั้ง (ก) inline และ (ข)-json:**

| format | verdict | เหตุผล |
|---|---|---|
| **(ข) `.srt` sidecar** | ✅ **เลือก** | `.txt` คงสะอาด 100% (NotebookLM + `structure_transcript.py` อ่านเหมือนเดิม = zero regression). `.srt` **โหลดเป็น subtitle ทับ mp4/m4a ต้นฉบับได้ตรงๆ** → scrub ไปนาทีที่ต้องการทันที = use case เป๊ะ. มนุษย์อ่านได้ ดับเบิลคลิกเปิดได้ ไม่ต้องเขียน script แกะ |
| (ข) `.json` sidecar | ❌ | `.txt` สะอาดเหมือนกัน แต่ json ต้องมี script มาอ่านถึงใช้ได้ — สำหรับ personal tool = friction เปล่าๆ ไม่มี upside เหนือ srt |
| (ก) inline `[MM:SS]` ใน .txt | ❌ | ทำ `.txt` เลอะ = ขัดเป้าหมายเดิม (clean text ป้อน NotebookLM) + ทำ T4 structure pipeline ที่ parse .txt งง. เอา timestamp ไปปนกับ text ที่ต้องสะอาด = ผิดที่ |

**ข้อกำกับ format ที่สำคัญ (กัน 2 กับดัก):**
1. **ต้อง map เวลา ไม่แปะดิบ.** Whisper คืน time เทียบ `tmp_speech` (VAD ตัด silence + คั่น pad 0.2s) — เพี้ยนจากต้นฉบับและเหลื่อมสะสมตามความยาว. map กลับด้วย `ts` + pad สะสม (โค้ดใน T16 Change 5). invariant พิสูจน์: **timecode segment สุดท้ายต้อง ≈ `omin` (ยาวต้นฉบับ) ไม่ใช่ `smin` (speech บีบแล้ว)**.
2. **อย่า over-clean บรรทัด .srt.** สร้างจาก `res['segments']` ดิบ (แค่ strip). บรรทัด garbage/`invalid` ใน .srt **คือประโยชน์** — มันบอกว่า "นาทีนี้ต้นฉบับพัง ไปฟังเทียบ". ไม่ต้อง sync marker `[?ตรวจสอบ]` เข้า .srt (over-engineer) — แค่มี timecode ให้ jump พอ.

**Q15.3 — fold เข้า T16 (Change 5). ไม่สร้าง T17.** เกณฑ์ทั้ง 4 ชี้ทางเดียว: (1) ไฟล์เดียวกัน `tools/vad_transcribe.py`, (2) **synergy** — marker ของ T16 ใช้ไม่ได้ถ้าไม่มี timestamp ของ Q15, แยกกันทำ = ครึ่งๆ กลางๆ, (3) test pass เดียวครอบได้ทั้งคู่, (4) cost discipline — Sonnet ลงมือรอบเดียว ไม่ใช่สองรอบ. แยกเป็น T17 จะได้ context ซ้ำ + รอบทดสอบซ้ำโดยไม่มีประโยชน์.

**Q15.4 — execution:** อยู่ใน **T16 Change 5** (`for-sonnet/tasks.md`) แล้ว — โค้ด block เต็ม (piecewise map `speech_to_orig_sec` + เขียน `.srt` แบบ try/except) + invariant test (last timecode ≈ `omin`) + วิธียืนยัน use case "นาทีที่ 20". Sonnet fresh session รันตามได้เลย ไม่ต้องมี context นี้.

**บรรทัดสรุปตรรกะ map (ให้ audit ได้):** speech-timeline sample `sp` → หา segment `i` ที่ `sp` ตกด้วย `bisect` บน `sp_starts` (offset สะสม = ผลรวม `seg_len + pad` ของ segment ก่อนหน้า) → original sample = `ts[i].start + (sp - sp_starts[i])` (clamp ในช่วง segment; ถ้าตกใน pad snap ไปปลาย segment) → `/SR` = วินาทีจริงในไฟล์ต้นฉบับ. เป็น pure-Python deterministic ไม่มี model call เพิ่ม.

---

## Q16 — ออกแบบ "punch-card" orchestrator สำหรับ batch transcribe หลายไฟล์ (checkpoint ทีละไฟล์ ไม่ให้พังยกชุด)
**Status:** done (Opus, 2026-07-05) — instinct ถูก แต่เหตุผลคือ "per-file output ต้องลง disk ทันที" ไม่ใช่ "ต้องมี orchestrator ซับซ้อน". Build เวอร์ชัน lean: **filesystem = checkpoint** (existence-skip, ไม่มี state DB/lock). Sonnet executes **T17** (`tools/batch_transcribe.py` + JSON manifest). คำตอบด้านล่าง.

**บริบท:** ระหว่างคุยเรื่อง Q14/Q15/T16 user เสนอไอเดียเอง (2026-07-05): ตอนรัน pipeline ข้ามคืนถอดเสียงคอร์ส Masterclass (11 ไฟล์ m4a, เห็นใน `pipeline_stdout.log`/`pipeline.log`) — script ที่วน loop เรียก `tools/vad_transcribe.py` ทีละไฟล์แล้วเอาผลมาต่อกันเป็น `transcript_1.txt`/`transcript_2.txt`/`transcript_3.txt` **ไม่เคยถูกเซฟไว้เป็น tool ถาวรใน `tools/` เลย** — เป็น script ชั่วคราวที่เขียนแล้วรันทิ้งไปแล้ว (หาไม่เจอในโค้ดตอนนี้)

**ปัญหาที่ user ชี้ (สมเหตุสมผล ยืนยันจาก log แล้ว):** เช็ค `pipeline_stdout.log` พบว่า `transcript_1.txt` (ผลรวมของ 5 ไฟล์ day1-1..day1-5) โผล่ขึ้นมา**แค่ครั้งเดียวตอนจบ** (บรรทัด `done: .../transcript_1.txt (151618 chars)`) หลังไฟล์ที่ 5 เสร็จ — ไม่มีร่องรอยว่ามีการเขียนผลลัพธ์ราย-ไฟล์ (เช่น `day1-1_transcript.txt`) ลง disk ระหว่างทางเลย ในโฟลเดอร์ผลลัพธ์ก็ไม่มีไฟล์ intermediate แบบนั้นเหลืออยู่ (เช็คจริงจาก `ls` ตอนที่คุยกันเรื่อง Masterclass ก่อนหน้านี้)

**ความเสี่ยงที่ user กังวล (คำพูดตรงๆ ของ user):** "ทำทีละ session ให้เหมือน punch card ไม่งั้น ถ้าผิดพลาด มันจะผิดหมด" — คือถ้าไฟล์ที่ N ล้มกลางคัน (ตัวอย่างจริงที่เจอ: day1-1 ใช้เวลา 7+ ชม.เพราะเครื่อง sleep, ดู Q14) งานของไฟล์ 1 ถึง N-1 ที่เสร็จไปแล้วอาจเสียหายหรือต้องทำใหม่ทั้งหมด เพราะไม่มี checkpoint ราย-ไฟล์

**ขอให้ Opus ออกแบบ orchestrator script ใหม่ (เก็บเป็น tool ถาวรใน `tools/` รอบนี้ ไม่ใช่ script ทิ้งขว้างเหมือนที่ผ่านมา) ที่:**
1. ประมวลผลทีละไฟล์แบบ **"punch card"** — แต่ละไฟล์เป็นหน่วยจบในตัว เขียนผลลัพธ์ (transcript + `.srt` จาก T16 Change 5) ลง disk **ทันทีที่ไฟล์นั้นเสร็จ** ไม่ใช่รอรวมทุกไฟล์เสร็จก่อนค่อยเขียน
2. **Resumable** — ถ้า script ถูกรันซ้ำ (เช่นหลังเครื่อง crash/sleep กลางคัน) ต้อง skip ไฟล์ที่ทำเสร็จแล้ว (มี output อยู่แล้ว) ไม่ทำซ้ำ ไม่เสียเวลา/token โดยไม่จำเป็น
3. ถ้าไฟล์หนึ่งล้มเหลว (exception, timeout, quality gate FAIL จาก `vad_transcribe.py`) — ไฟล์อื่นที่ยังไม่ถึงคิวต้อง**รันต่อได้** ไม่ใช่ script ทั้งก้อนตายไปด้วย และต้อง log ให้ชัดว่าไฟล์ไหนพัง เพื่อให้ user กลับมา rerun เฉพาะไฟล์นั้นได้ทีหลัง
4. การต่อ transcript หลายไฟล์เป็น session เดียว (เช่น day1-1..day1-5 → transcript_1.txt) ควรทำตอนไหน/ยังไงให้สอดคล้องกับหลักการข้อ 1-3 (เช่น concat ทีหลังจาก per-file output ที่เขียนไว้แล้ว แทนที่จะ concat ใน memory ระหว่าง loop)
5. ตัดสินใจว่าจะเขียนเป็น bash script ที่เรียก `vad_transcribe.py` ทีละไฟล์ หรือ python script ใหม่ — และเก็บที่ไหนใน `tools/` ตั้งชื่อว่าอะไร

**ให้ Opus ตอบ:**
1. ยืนยันว่าไอเดีย "punch card" ของ user สมเหตุสมผลไหม มีมุมที่มองข้ามหรือ over-engineer ไปไหมสำหรับ tool ส่วนตัว (single-user, ไม่ใช่ production infra)
2. ออกแบบ schema/format ของ per-file checkpoint (เช่น เขียนไฟล์ output ราย-part ไว้ที่ไหน ตั้งชื่อยังไง ใช้อะไรเป็นสัญญาณ "เสร็จแล้ว" ให้ resume logic เช็คได้)
3. เขียนเป็น task ใหม่ (เช่น T17) ใน `for-sonnet/tasks.md` ให้ Sonnet (fresh session) สร้าง tool นี้ได้เลย ระบุ path ไฟล์ใหม่ที่ควรสร้าง, ต้องเรียก `vad_transcribe.py`/T16's `.srt` logic ยังไง, resume/skip logic ควรเช็คอะไร
4. ถ้าคิดว่า over-engineer เกินไปสำหรับ use case จริง (คอร์สสอนไม่กี่คอร์สต่อเดือน ไม่ใช่ pipeline รันทุกวัน) — บอกตรงๆ และเสนอทางที่ simple กว่าแทน (เช่น แค่เขียน per-file output แยกไว้เสมอ + concat step แยกต่างหากที่รันเองทีหลังได้ ไม่ต้องมี logic ซับซ้อน)

### ANSWER (Opus, 2026-07-05)

**กรอบที่คุมทุกข้อ: instinct ถูก แต่เหตุผลไม่ใช่ "ต้อง orchestrator ซับซ้อน" — เหตุผลคือ "per-file output ต้องลง disk ทันที". ทำข้อเดียวนี้ ความเสี่ยง ~90% หายไป. Build — แต่ให้ filesystem เป็น checkpoint เอง (ห้ามมี state DB/manifest ผลลัพธ์/lockfile).**

Diagnose ว่าทำไม crash ถึงหายนะจริง (ยืนยันจาก `pipeline.log`): script เดิม concat ใน **memory** แล้วเขียน `transcript_N.txt` **ครั้งเดียวตอนจบ session** — log แสดง `done: transcript_1.txt` โผล่หลัง day1-5 เสร็จ ไม่มี intermediate ราย-part ลง disk เลย. ถ้า crash ตอน day1-4 (เคสจริง: day1-1 กิน 7h21m เพราะ sleep) → งาน day1-1..1-3 ที่ค้างใน memory **หายเกลี้ยง**. นั่นคือบั๊กตัวเดียว ไม่ใช่ "ขาด orchestrator".

Key ที่กัน over-engineer: `vad_transcribe.py` **เขียนไฟล์ output ของมันเอง (argv[2]) ทุกครั้งที่ถูกเรียกอยู่แล้ว** + Change 5 เขียน `.srt` ข้างๆ ให้ด้วย. ดังนั้น orchestrator แค่เรียกมันด้วย path ราย-part → ผลลง disk เอง. พอ per-part อยู่บน disk แล้ว **resume + isolation แทบฟรี** (existence-check 1 บรรทัด):

**Q16.1 — instinct สมเหตุสมผล ทุกข้อ แต่ fix ที่ถูกขนาดคือ lean มาก:**

| user worry | สมเหตุสมผล? | fix ที่ถูกขนาด (ไม่เกิน) |
|---|---|---|
| per-file ไม่ลง disk → crash เสียหมด | ✅ ตัวจริง | เรียก `vad_transcribe.py` ด้วย output ราย-part `parts/<stem>.txt` → ลง disk ทันทีเมื่อ part เสร็จ (vad เขียนเอง) |
| resume ต้อง skip ที่เสร็จแล้ว | ✅ คุ้ม เพราะเกือบฟรี | เช็ค `parts/<stem>.txt` มีอยู่ + size>0 = done → skip. **filesystem คือ checkpoint** ไม่ต้องมี state file |
| 1 ไฟล์พังต้องไม่ล้มยกชุด | ✅ | ครอบ subprocess ราย-part, ถือว่า fail ถ้า rc≠0 / `QUALITY: FAIL` / `NO SPEECH` / ไฟล์ว่าง → log, ไปต่อ |
| concat ทีหลังจาก disk | ✅ | concat step แยก อ่าน `parts/*.txt` ที่เขียนแล้ว, gate ว่าครบทุก part ของ session ค่อยเขียน `transcript_N.txt` |

**สิ่งที่ห้ามสร้าง (over-engineer สำหรับ tool ส่วนตัว few-courses/month):** JSON state/manifest ผลลัพธ์, lockfile, retry-with-backoff, progress %, checksum/atomic-write ceremony, merged-across-parts `.srt`. **filesystem existence เพียงพอเป็น source of truth** — crash-mid-`f.write` window แค่ไม่กี่ ไมโครวินาที ยอมรับได้สำหรับ personal tool.

**Q16.2 — checkpoint schema (ตอบข้อ "อะไรคือสัญญาณเสร็จ"):**

| item | ตัดสิน |
|---|---|
| per-part output path | `<course_dir>/parts/<audio_stem>.txt` (+ `.srt` sidecar ที่ vad เขียนข้างๆ ให้เอง จาก Change 5) |
| "done" signal | `parts/<stem>.txt` **exists และ size>0** เท่านั้น. ไม่มี manifest ผลลัพธ์, ไม่มี flag file |
| FAIL handling | rc≠0 / `NO SPEECH` / `QUALITY: FAIL` / ไฟล์ว่าง → **ย้าย** ไฟล์ที่ได้เป็น `parts/<stem>.txt.FAILED` (เก็บไว้ดู) เพื่อ**ไม่ให้มี clean `.txt`** → rerun ครั้งหน้าถอดใหม่เอง. batch ไม่หยุด |
| concat | เมื่อครบทุก part ของ session (clean `.txt` ครบ) → เขียน `<course_dir>/transcript_N.txt` เรียงตาม manifest. ถ้า part ใด missing → **ไม่เขียน**, log `concat SKIP <session>: N part(s) missing` (กัน half-session เนียนดูเหมือนครบ). idempotent + มี `--concat-only` |
| manifest input | JSON เล็กๆ ต่อคอร์ส = "punch-card deck" (mapping session→parts, model, prompt). explicit ดีกว่าเดา session จากชื่อไฟล์ |

การ resume จึงเป็น: วน part, ถ้า clean `.txt` มีอยู่ → skip; part ที่เคย FAILED มีแต่ `.txt.FAILED` (ไม่มี clean `.txt`) → ถอดใหม่. ทั้งหมดคือ existence-check ไม่มี machinery.

**Q16.3 — bash vs python + ที่อยู่:** **Python** — `tools/batch_transcribe.py`. เหตุผล: (1) session→parts เป็น "data" (dict) เขียนใน JSON manifest สะอาดกว่า bash array; (2) ต้อง parse `QUALITY: PASS/FAIL` จาก stdout ของ vad → Python ทำง่าย; (3) concat UTF-8 ไทย + quarantine rename + existence-skip เป็น Python ไม่กี่บรรทัด; (4) `tools/` เดิมเป็น Python ทั้งหมด. โค้ดเต็มอยู่ใน **T17**. Bake `caffeinate -w <pid>` เข้าไปในตัว script เลย (ตรง T16 Change 4 — ผูก caffeinate กับ batch เสมอ) → รันข้ามคืนไม่ sleep โดยไม่ต้องจำ wrap เอง.

**Q16.4 — concat = step แยก อ่านจาก disk (ตามที่ user อยากได้):** ทำหลัง transcribe loop จบ, อ่าน `parts/*.txt` ที่เขียนไว้แล้ว (ไม่ concat ใน memory ระหว่าง loop), gate ด้วยความครบของ session, และ `--concat-only` ให้ re-concat ได้โดยไม่ถอดใหม่. ไม่ทำ merged `.srt` ข้าม part (ต้อง offset เวลาสะสม = over-engineer); per-part `.srt` ใน `parts/` พอแล้วสำหรับ "ไปฟังนาที X ของ part ไหน" เพราะ user รู้ว่า part ไหน.

**Q16.5 — over-engineer ไหม? ไม่ — *ถ้า* build ให้ filesystem เป็น checkpoint.** ทาง "simple กว่า" ที่ user เสนอ (เขียน per-file เสมอ + concat มือ) = แก่นเดียวกันเป๊ะ. ส่วนที่ user กลัวว่าจะซับซ้อน (resume logic) จริงๆ คือ existence-skip **บรรทัดเดียว** เพราะ per-file persistence แบกงานหนักไปหมดแล้ว — ถูกจนไม่มีเหตุผลตัดทิ้ง. failure-isolation ก็แค่ try/รอบ subprocess เดียว. เพราะฉะนั้น **build the lean version** (ไม่ใช่ simplify ลงไปกว่านี้, ไม่ใช่ inflate ขึ้นไปกว่านี้). ขอบเขตที่ห้ามข้าม = ตาราง "สิ่งที่ห้ามสร้าง" ใน Q16.1.

**Dependency:** T17 ต้องรันหลัง **T16** (ใช้ `--model` flag ของ Change 1 + `.srt` ของ Change 5). ถ้ารัน batch ก่อน T16 → `vad_transcribe.py` ไม่รับ `--model` = error. Sonnet ทำ T16 ให้เสร็จก่อน.

---

## Q17 — `large-v3` ยังหลุด hallucinate 26% ของ segment ทั้งไฟล์ (ไม่ใช่แค่ต้นไฟล์) — ต้องแก้ยังไง (ปรึกษา Fable ตามที่ user ขอ)
**Status:** done (Fable, 2026-07-06) — วินิจฉัยจากอ่าน mlx_whisper 0.4.3 source โดยตรง (ไม่เดา): `compression_ratio_threshold`/`logprob_threshold` เป็น **retry trigger เท่านั้น ไม่ใช่ reject/discard filter** — `decode_with_fallback()` คืนค่า decode ผลลัพธ์ล่าสุดเสมอ แม้ครบทุก temperature แล้วยังไม่ผ่าน threshold ก็ตาม (ไม่มี code path ไหน "ทิ้ง segment" เลย). วัด compression ratio จริงจาก 186 bad segment ใน day1-1.srt ได้ median 39.35 — สูงกว่า threshold 2.4 ถึง ~16 เท่า → **threshold ตรวจจับถูกอยู่แล้ว ไม่ใช่ miscalibrate สำหรับภาษาไทย** ปัญหาคือ retry ไม่ช่วยเมื่อเสียงต้นฉบับช่วงนั้นแย่จริง (ไม่ใช่ silence ตาม literal เลยไม่ถูก VAD ตัดออก). `word_timestamps`+`hallucination_silence_threshold` ใช้ไม่ได้ผลกับเคสนี้เพราะกลไกต้องพึ่ง silence gap ซึ่ง VAD ตัดออกไปหมดแล้วก่อนถึง Whisper. ฟันธง: **แก้ post-processing regex ใน `vad_transcribe.py` แทนที่จะแตะ decode parameter** — เจอบั๊กเพิ่มด้วยว่า regex เดิม (`(.{2,8})\1{4,}`) **match เคสนี้ไม่ได้เลยสักครั้ง** (ทดสอบจริงบน day1-1.txt: 0 substitution) เพราะ boundary drift ในลูปทำให้ exact-backreference พลาด. เขียน **T18** ให้ Sonnet แก้.

**บริบท:** T16+T17 เสร็จแล้ว รัน Session 1 จริงของคอร์ส Masterclass ด้วย `--model large-v3` ผ่าน `tools/batch_transcribe.py` สำเร็จครบ 5 ไฟล์ (ดู `for-sonnet/tasks.md` T16/T17 status) ผลเทียบ turbo backup ดีขึ้นชัดเจน (เนื้อหา 2.3 เท่า, `invalid`/`beispiel` hallucination หายหมด) — **แต่** พอ user ให้เปิด `parts/masterclass day 1-1.srt` ไล่อ่านเทียบ timestamp จริง แล้วสแกนทั้งไฟล์แบบ programmatic (regex หา low-character-diversity + short-run repeat ในแต่ละ subtitle block) พบว่า **203 จาก 781 segment (26%)** ยังมี hallucination แบบ "วนคำซ้ำ" (ตัวอย่างเด่นคือคำว่า "อยู่" ซ้ำเป็นสิบๆ ครั้งต่อ segment) **กระจายอยู่ตลอดทั้งไฟล์ 105 นาที** ไม่ใช่กระจุกอยู่ต้นไฟล์อย่างที่ Sonnet เข้าใจผิดตอนแรก (มีทั้งช่วง 0:00-12:00 หนาแน่นสุด และช่วง 1:36-1:44 ใกล้ท้ายไฟล์)

**นี่คือข้อมูลใหม่ที่เปลี่ยนข้อสรุปของ Q14 (Opus เคยฟันธงว่า "เปลี่ยนเป็น large-v3 = แก้ที่ต้นทาง"):** large-v3 ลด hallucination ประเภท "คำต่างประเทศหลุด"/"เนื้อหาหายทั้งประโยค" (เคส MC/beispiel) ได้จริง แต่ **ไม่ได้แก้ hallucination ประเภท "วนคำซ้ำ" (repetition loop) ที่ยังเหลืออยู่มากถึง 1 ใน 4 ของ segment**

**สิ่งที่ Sonnet เช็คมาแล้ว (ข้อมูลจริง ไม่ใช่เดา) — เช็ค signature ของ `mlx_whisper.transcribe` ตรงๆ ผ่าน `inspect.signature`:**
```
audio, path_or_hf_repo='mlx-community/whisper-tiny', verbose=None,
temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
compression_ratio_threshold=2.4, logprob_threshold=-1.0, no_speech_threshold=0.6,
condition_on_previous_text=True, initial_prompt=None, word_timestamps=False,
prepend_punctuations=..., append_punctuations=..., clip_timestamps=0,
hallucination_silence_threshold=None, **decode_options
```
docstring ยืนยันว่า:
- `temperature` เป็น **fallback tuple อยู่แล้ว** — ถ้า decode ล้มเหลว (ชน `compression_ratio_threshold` หรือ `logprob_threshold`) ควรลองใหม่ที่ temperature สูงขึ้นอัตโนมัติ (เป็น mechanism มาตรฐานของ Whisper)
- `compression_ratio_threshold=2.4` — "If the gzip compression ratio is above this value, treat as failed" — ข้อความซ้ำแบบ "อยู่อยู่อยู่..." ควรมี compression ratio สูงมาก (บีบอัดได้ง่ายเพราะซ้ำ) น่าจะเกิน threshold นี้ชัดเจน แต่จากผลจริงดูเหมือนยังหลุดผ่านไม่โดนจับ
- **`hallucination_silence_threshold`** — พารามิเตอร์ที่ออกแบบมาเพื่อกันปัญหานี้**โดยตรงตามชื่อ** แต่ docstring ระบุว่า **"When word_timestamps is True"** ถึงจะทำงาน — ตอนนี้ script (`vad_transcribe.py`) ไม่ได้ตั้ง `word_timestamps=True` เลย (ใช้ default `False`) ฟีเจอร์นี้เลย**ไม่ทำงานอยู่ตอนนี้**
- `condition_on_previous_text=False` (ที่ตั้งไว้แล้วใน `vad_transcribe.py` ปัจจุบัน) — docstring บอกว่าการปิดตัวนี้ "the model becomes less prone to getting stuck in a failure loop, such as repetition looping" — แปลว่า**ตั้งไว้ถูกทางแล้ว** แต่ยังไม่พอ

**คำถามที่ต้องการให้ Fable วิเคราะห์และตัดสิน:**

1. **วินิจฉัยว่าทำไม `compression_ratio_threshold=2.4` (ค่า default ของ mlx_whisper) ไม่จับ "อยู่อยู่อยู่..." ที่ดูเหมือนควรมี compression ratio สูงมาก** — เป็นไปได้ไหมว่า Thai UTF-8 multi-byte character หรือวิธีคำนวณ gzip ratio ของ mlx_whisper ทำให้ threshold นี้ calibrate ผิดสำหรับภาษาไทยโดยเฉพาะ (ต่างจาก English ที่ threshold นี้ถูก tune มาให้)? ถ้าใช่ ควรปรับ `compression_ratio_threshold` ให้เข้มขึ้น (ค่าต่ำลง) สำหรับงานภาษาไทยไหม เท่าไหร่ถึงจะสมเหตุสมผลโดยไม่ทำให้ segment ปกติที่พูดซ้ำจริงๆ (เช่น ผู้สอนย้ำคำสอน) โดนตัดทิ้งผิด
2. **ควรเปิด `word_timestamps=True` + ตั้ง `hallucination_silence_threshold` (เช่น 2.0 วินาที) ไหม** — ชั่งน้ำหนักกับ cost เพิ่ม (word-level timestamp ผ่าน cross-attention + DTW ใช้เวลา/compute เพิ่มขึ้นเท่าไหร่ต่อไฟล์ 100+ นาที) เทียบกับประโยชน์ที่ได้ (กัน "วนคำซ้ำ" ได้จริงไหม เพราะ mechanism นี้ออกแบบมาเพื่อ "silence" ไม่ใช่ "repetition" — silence กับ repetition คนละปัญหากันหรือเปล่า ต้องเช็คให้ชัดว่า parameter นี้ใช้ได้กับเคสนี้จริงไหมก่อนแนะนำให้เปิด)
3. **ทางเลือกอื่นที่ยังไม่ได้ลอง:** ลด `logprob_threshold` ให้เข้มขึ้น (เช่น จาก -1.0 เป็น -0.5) เพื่อ trigger retry ถี่ขึ้น? ปรับ `temperature` ให้เริ่มสูงขึ้นตั้งแต่ต้น (ข้าม temperature=0.0 ที่มักทำให้เกิด repetition loop มากสุด)? หรือปัญหาจริงคือ**คุณภาพเสียงต้นฉบับของไฟล์ day1-1 เฉพาะไฟล์นี้แย่กว่าไฟล์อื่นจริงๆ** (มี noise/echo/เสียงเบา) ซึ่งไม่มี parameter ไหนแก้ได้ ต้องยอมรับแล้วใช้ `[?ตรวจสอบ]` marker (Change 3 เดิม) ช่วยแทน — ถ้าเป็นแบบนี้ควรปรับ Change 3's marker regex ให้จับ pattern สั้นกว่านี้ได้ (ปัจจุบันจับ repeat แค่ 2-4 ครั้งของ token ที่คั่นด้วย whitespace แต่เคสนี้ไม่มี whitespace คั่นเลย ("อยู่อยู่อยู่..." ติดกันไม่มีช่องว่าง) เลยหลุดรอด Change 3 ไปด้วย
4. **ให้ Fable ฟันธง priority การแก้ 3 ทางเลือกข้างต้น (หรือเสนอทางอื่น) พร้อมเหตุผล** แบบเดียวกับที่ Q14 เคยทำ (ตาราง ✅/❌ พร้อมเหตุผลสั้นๆ) — และถ้าต้องแก้โค้ด ให้เขียน task ใหม่ (T18) ใน `for-sonnet/tasks.md` ให้ Sonnet ไปทำต่อได้เลย (fresh session ไม่มี context นี้) ระบุพารามิเตอร์/regex ที่ต้องเปลี่ยนให้ชัดเจน พร้อม test plan ที่ใช้ตรวจสอบกับ `parts/masterclass day 1-1.txt`/`.srt` จริงที่มีอยู่แล้ว (ไม่ต้องรอ transcribe ใหม่ทั้งไฟล์เพื่อทดสอบ ถ้าเป็นไปได้ให้ทดสอบกับ segment สั้นๆ ที่ตัดมาจากช่วงที่รู้ว่าเจอปัญหาแล้ว เช่น 0:00-2:35 หรือ 1:41:56-1:42:32)

**Cost note:** user เจาะจงให้ปรึกษา Fable รอบนี้ (ไม่ใช่ Opus ตามปกติ) เพราะปัญหานี้ต้องการความเข้าใจกลไก decode ของ Whisper ลึกกว่าปกติ — ตอบให้คุ้มกับที่จ่ายแพงกว่า Opus โดยให้การวินิจฉัยที่แม่นและ decisive ไม่ hedge

### ANSWER (Fable, 2026-07-06)

**กรอบที่คุมทุกข้อ: อ่าน source ของ `mlx_whisper` (0.4.3, installed จริง) ตรงๆ แทนการอนุมานจาก docstring — คำตอบเปลี่ยนจากที่ตั้งสมมติฐานไว้ทั้งหมด.** `compression_ratio_threshold`/`logprob_threshold` **ไม่ใช่ quality gate ที่ทิ้ง segment ที่แย่** — มันเป็นแค่ตัวสั่ง **"ลองใหม่ที่ temperature ถัดไป"**. อ่าน `decoding_with_fallback()` ใน `transcribe.py` บรรทัด 207-245 ตรงๆ:

```python
decode_result = None
for t in temperatures:                      # (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    ...
    decode_result = model.decode(segment, options)
    needs_fallback = (compression_ratio_threshold check) or (logprob_threshold check)
    if not needs_fallback:
        break
return decode_result                        # <- คืนค่าครั้งสุดท้ายเสมอ ไม่เช็คซ้ำว่า needs_fallback ยังเป็น True อยู่ไหม
```

ถ้าลองครบทุก temperature แล้ว**ยังไม่ผ่าน**ทั้ง 2 threshold — โค้ดไม่มี branch ไหนทิ้ง/blank segment นั้นเลย มันคืนค่าผลลัพธ์ของความพยายามครั้งสุดท้าย (แย่ที่สุด) ออกไปตรงๆ. นี่คือรากของปัญหาทั้งหมด ไม่ใช่เรื่อง threshold คำนวณผิดสำหรับภาษาไทย.

**Q17.1 — `compression_ratio_threshold=2.4` ไม่ใช่ Thai-miscalibration bug. เป็น red herring ตามที่ user ระแวงไว้ถูกทาง.**

| สมมติฐาน | ตรวจแล้ว | ผล |
|---|---|---|
| Thai UTF-8 multi-byte ทำให้ ratio คำนวณผิดสเกล | วัดจริง: `compression_ratio(text) = len(text.encode('utf-8')) / len(zlib.compress(text_bytes))` (decoding.py บรรทัด 15-17) — เป็น byte-ratio ธรรมดา ไม่มีอะไรพิเศษเกี่ยวกับภาษา | ❌ ไม่ใช่สาเหตุ |
| threshold 2.4 คำนวณแล้วไม่สูงพอจะจับ "อยู่อยู่อยู่..." | วัด compression ratio จริงจาก 186 bad segment ใน `masterclass day 1-1.srt`: **median = 39.35** (สูงกว่า threshold 16 เท่า), มีแค่ 15% ของ bad segment ที่ ratio ≤2.4 | ❌ threshold ตรวจจับถูกแล้ว ratio สูงลิ่วชัดเจน |
| ทั้งที่ threshold "ตรวจจับถูก" ทำไมยังหลุดออกมา | เพราะ `decode_with_fallback` **ไม่มี reject path** — วนครบ 6 temperature แล้วเสียงต้นฉบับช่วงนั้นยังคุยไม่รู้เรื่อง (แย่จริง ไม่ใช่ threshold ผิด) → คืนค่าที่แย่ที่สุดออกมาอยู่ดี | ✅ **นี่คือสาเหตุจริง** |

**คำแนะนำ:** อย่าปรับ `compression_ratio_threshold` เลย (ทั้งขึ้นและลง) — ค่า default ตรวจจับถูกอยู่แล้ว การเข้มขึ้นจะแค่ trigger retry ไวขึ้นแต่ retry ก็วนกลับมาที่ปัญหาเดิม (ไม่มี reject path) จึงไม่มีผลลัพธ์ต่างจากเดิม.

**Q17.2 — `word_timestamps=True` + `hallucination_silence_threshold` — ❌ ไม่ใช้ (verdict เดียว ไม่ hedge).**

อ่านโค้ดจริง (`transcribe.py` บรรทัด 431-490): กลไกนี้ตรวจจับ hallucination จาก 3 เงื่อนไขเท่านั้น — (1) silence gap ระหว่าง word timestamp เกิน threshold, (2) segment ที่ผิดปกติอยู่ติด **ขอบ** ของ 30s window (`< 2.0s` จากขอบ), (3) anomaly score จาก word probability/duration ที่ผิดปกติ (`word_anomaly_score`). เงื่อนไข (1) เป็นตัวหลักที่ออกแบบมาเพื่อ "silence-triggered hallucination" (เช่นเคส "thanks for watching" ตอนเงียบท้ายคลิป) — **แต่ pipeline นี้รัน Silero VAD ตัด silence ออกไปก่อนถึง Whisper แล้ว** (`vad_transcribe.py` เก็บ speech ไว้ 98% ของ day1-1) ดังนั้นในไฟล์ที่ป้อนเข้า Whisper จริงๆ **แทบไม่มี silence gap เหลือให้กลไกนี้ตรวจจับเลย** — มันถูกออกแบบมาสำหรับ pipeline อื่น (raw long-form audio ที่มี pause) ไม่ใช่ pipeline ที่ VAD กรองมาก่อนแบบนี้.

ยืนยันเพิ่มด้วย `ffmpeg volumedetect` บนช่วง bad จริง (0:00-2:35 และ 1:41:56-1:42:32): mean_volume **-28dB / -28dB** เทียบกับช่วงปกติของไฟล์เดียวกัน (30:00, 60:00) ที่ **-27dB / -26.5dB** — **ระดับเสียงใกล้เคียงกันมาก ไม่ใช่ silence** ยืนยันว่านี่คือ**เสียงที่มีพลังงานแบบ speech แต่ถอดยาก** (crosstalk/ambient/เสียงก่อนเข้าเนื้อหาจริงช่วงเปิดคลาส) ไม่ใช่ dead-air. นี่คือ**คนละ failure mode**กับที่ `hallucination_silence_threshold` ถูกออกแบบมาแก้.

| ปัจจัย | ประเมิน |
|---|---|
| ใช้ได้กับ failure mode นี้จริงไหม | ❌ ไม่ตรง — กลไกพึ่ง silence gap ที่ VAD ตัดทิ้งไปแล้วก่อนถึง Whisper |
| cost เพิ่ม (cross-attention + DTW) | จริง มีนัยสำคัญบนไฟล์ 100+ นาที (ต้องคำนวณ word-level alignment ทุก segment) |
| ผลตอบแทนคาดหวัง | ต่ำมาก — เงื่อนไข silence-gap แทบไม่ trigger ในไฟล์ที่ผ่าน VAD แล้ว, เหลือแค่ boundary-heuristic ที่สุ่ม (ขึ้นกับว่า loop บังเอิญอยู่ติดขอบ 30s window หรือเปล่า) |
| **verdict** | **❌ ไม่ทำ** — จ่าย cost จริง แลกกับกลไกที่ mostly เป็น no-op ใน pipeline นี้ |

**Q17.3 — ทางเลือกอื่นที่ user เสนอ:**

| option | ตรวจแล้ว | verdict | เหตุผล |
|---|---|---|---|
| ลด `logprob_threshold` -1.0→-0.5 | อ่านโค้ด `decode_with_fallback` | ❌ | ยังชน "ไม่มี reject path" เดิม — ทำแค่บังคับให้ retry ผ่านทุก temperature เร็วขึ้น/บ่อยขึ้น ไม่ได้เพิ่มกลไกทิ้งผลลัพธ์แย่ ถ้าเสียงช่วงนั้นแย่จริง (ยืนยันจาก compression ratio สูง + volumedetect ใกล้เคียงปกติ = ไม่ใช่ signal อ่อนเกินไปแต่คือ "เสียงพูดที่ถอดยาก") ไม่มี temperature ไหนช่วยได้เพิ่ม แค่เสีย compute วนซ้ำมากขึ้นเปล่าๆ |
| ข้าม temperature=0.0 เริ่มที่ 0.2 | พิจารณา trade-off เชิงสถิติของ greedy vs sampling decode | ❌ | greedy (T=0) คือค่าที่แม่นที่สุดสำหรับเสียงชัด ~74-76% ของไฟล์ที่ไม่มีปัญหาอยู่แล้ว (day1-2 ถึง day1-5 มี loop แค่ 1-6%, ต่างจาก day1-1 ที่ 24%) — เอา T=0 ออกทั้งไฟล์ = เสี่ยง regress ความแม่นของส่วนใหญ่ที่ดีอยู่แล้ว เพื่อแลกกับผลไม่แน่นอนต่อ 24% ที่มีปัญหา (repetition loop เกิดได้ทุก temperature เมื่อ signal สับสนจริง ไม่ใช่แค่ที่ T=0) — asymmetric risk ไม่คุ้ม |
| beam search แทน greedy | เช็ค `decoding.py` บรรทัด 437: `raise NotImplementedError("Beam search decoder is not yet implemented")` | ❌ **ปิดประตูเลย** | mlx_whisper 0.4.3 **ไม่รองรับ beam search** (มีแค่ greedy/sampling) — ไม่ใช่ทางเลือกที่มีอยู่จริงในเวอร์ชันที่ติดตั้ง ไม่ต้องพิจารณาต่อ |
| เสียงต้นฉบับช่วงนั้นแย่จริง → ยอมรับ + ขยาย flag regex | ยืนยันด้วย volumedetect (ไม่ใช่ silence, -28dB ≈ ปกติ) + compression ratio สูงลิ่ว (median 39) + VAD ยังเก็บไว้เป็น speech (98%) | ✅ **นี่คือทางแก้จริง** | ไม่มี decode parameter ไหนแก้ "เสียงถอดยากแต่ไม่ใช่ silence" ได้อย่างน่าเชื่อถือ ทางที่เหลือคือ post-processing ตาม principle ของ Q14 (flag ไม่ลบ) |

**การค้นพบเพิ่มที่สำคัญมาก (ไม่ได้ถูกถามตรงๆ แต่กระทบ fix ที่ต้องทำ):** regex เดิมใน `vad_transcribe.py` (บรรทัด ~85-90, silent-strip ของ Thai character-level repeat `(.{2,8})\1{4,}`) **ไม่เคย match เคสนี้เลยแม้แต่ครั้งเดียว** — ทดสอบจริงบน `parts/masterclass day 1-1.txt` (ไฟล์จริงที่มีอยู่แล้ว): apply regex ซ้ำ 8 รอบได้ length เท่าเดิมเป๊ะ (26,817 ตัวอักษร ทั้งก่อนและหลัง) = **0 substitution**. สาเหตุ: ข้อความจริงมี **boundary drift** ("...อยู่อยู่อย อยู่อยู่อยใคร...") — หน่วยที่ซ้ำไม่ได้เหมือนกันทุกตัวอักษร (มีบางจุดขาด/เกิน 1-2 ตัวอักษรตรงกลาง) ทำให้ exact-backreference regex (`\1` ต้องตรงเป๊ะ) พลาดทั้งหมด. นี่คือช่องโหว่จริงที่ทำให้ 26% หลุดรอดทั้ง silent-strip เดิม และ Change 3's flag pass (ซึ่งจับแค่ Latin-token pattern อยู่แล้ว ไม่ใช่ target ของ Thai glued-repeat).

**Q17.4 — Priority ตัดสินใจสุดท้าย (ตารางเดียวจบ):**

| ทำอะไร | ทำ? | เหตุผลย่อ |
|---|---|---|
| ปรับ `compression_ratio_threshold`/`logprob_threshold` | ❌ | retry-only mechanism, ไม่มี reject path — tuning เท่าไหร่ก็ไม่ช่วย |
| เปิด `word_timestamps` + `hallucination_silence_threshold` | ❌ | VAD ตัด silence ไปแล้วก่อนถึง Whisper → กลไกนี้ mostly no-op ใน pipeline นี้ + cost จริงไม่คุ้ม |
| ข้าม temperature=0.0 | ❌ | เสี่ยง regress 74-76% ของไฟล์ที่ดีอยู่แล้ว เพื่อผลไม่แน่นอนต่อส่วนที่แย่ |
| beam search | ❌ | ไม่มีอยู่จริงใน mlx_whisper 0.4.3 (`NotImplementedError`) |
| **แก้ post-processing regex ให้ครอบคลุม boundary-drift repeat + flag แทนลบเงียบ** | ✅ **ทำ** | root cause จริงคือเสียงถอดยาก (ไม่ใช่ silence) ที่ไม่มี decode-parameter ไหนแก้ได้น่าเชื่อถือ — ทางเดียวที่เหลือคือทำให้คนเห็นจุดที่น่าสงสัย (Q14 principle เดิม) และ regex เดิมมีบั๊กจริงที่พิสูจน์ได้ (0 match) ต้องแก้อยู่แล้ว |

**สรุปเชิงเทคนิค 1 บรรทัด (ตอบคำถามตั้งต้นของ user ตรงๆ):** compression_ratio_threshold **ตรวจจับถูก** ("อยู่อยู่อยู่..." มี ratio สูงกว่า threshold 16 เท่า) แต่ mlx_whisper **ไม่มีกลไกทิ้ง segment ที่ยังตรวจจับได้ว่าแย่หลัง retry ครบ** — มันแค่ retry แล้วคืนค่าที่แย่ที่สุดออกมาถ้าไม่มีอันไหนดีพอ ปัญหาจึงอยู่ที่ "เสียงต้นฉบับช่วงนั้นถอดยากจริง (ไม่ใช่ silence)" ซึ่งไม่มี decode parameter ไหนแก้ได้ — ต้องแก้ที่ post-processing แทน. โค้ด → **T18** (T18 ทำเสร็จแล้ว 2026-07-06, ทดสอบผ่านครบ + apply กับไฟล์เก่าที่มีอยู่แล้วเรียบร้อย).

---

## Q18 — สำรวจ agent/skill/hook/slash command/orchestration/index ทั้งหมดของ studio — ควรปรับอะไรไหม (ปรึกษา Fable ตามที่ user ขอ)
**Status:** done (Fable, 2026-07-06) — 3 ของ 5 observation คือ "ระบบถูกออกแบบมาถูกแล้ว อย่าแตะ", 2 ข้อมีของจริงให้แก้ (เล็ก). เพิ่ม 2 gap ที่ Sonnet ไม่ได้เห็น (teacher.md/learn-session file collision, publish-course preflight ล้าสมัย). เขียน **T19** (4 sub-fix เล็กๆ) ใน `for-sonnet/tasks.md`. ปฏิเสธของใหญ่ทุกอย่าง (dedicated research agent, meta-orchestrator, general hook push, skill merge) เพราะ over-engineer สำหรับ solo tool.

**บริบท:** studio ตอนนี้มีงานหลัก 3 เรื่อง: **(1) วิจัยการลงทุน/หุ้น** (research/, knowledge/, NotebookLM), **(2) ถอดเทปคอร์สสอน** (tools/vad_transcribe.py, tools/batch_transcribe.py, tools/structure_transcript.py, skills/learn-session, skills/publish-course), **(3) บอท LINE คลินิก Alonsi** (agents/line-bot.md, skills/linebot-check, n8n workflow ภายนอก) — ผู้ใช้ต้องการให้สำรวจ **ทุกกลไกที่เกี่ยวกับ agent ecosystem** ว่ามีอะไรซ้ำซ้อน/ขาด/ควรปรับให้เหมาะกับ 3 งานนี้มากขึ้นไหม

**Inventory ปัจจุบัน (สำรวจแล้วจริง ไม่ใช่เดา — เช็คจาก `find`/`ls`/`cat` ตรงๆ):**

**Agents** (`.claude/agents/*.md`):
| ไฟล์ | ขนาด | หน้าที่ |
|---|---|---|
| `teacher.md` | 3.9KB | อ่าน `source/` แล้วสอนหุ้นเป็นภาษาไทย อ้างอิง source เท่านั้น |
| `line-bot.md` | 19.5KB | ผู้เชี่ยวชาญบริหาร/แก้ logic LINE bot คลินิก + n8n |

**Commands** (`.claude/commands/*.md` — custom slash command แยกจาก Skills):
| ไฟล์ | หน้าที่ |
|---|---|
| `download.md` | เลือก cobalt vs yt-dlp ตามประเภทวิดีโอ |
| `yt-session.md` | รัน yt-session-generator server สำหรับ poToken |

**Skills เฉพาะ studio** (`.claude/skills/*/`):
| Skill | หน้าที่ |
|---|---|
| `learn-session` | Minnie + Fact-checker pipeline สอน/สรุปคอร์ส (built 2026-07-01, ผ่าน Opus review, validate แล้ว 2 คอร์ส: AI Leading Indicator + Masterclass ลงทุนศาสตร์) |
| `linebot-check` | เช็ค State sheet + Appointments sheet ของบอทคลินิก |
| `publish-course` | เอาไฟล์จาก `source/<topic>/` ไปขึ้นเว็บ `sites/alonsi-invest/` |

**Skills กลาง (global, ไม่ใช่เฉพาะ studio — มาจาก plugin/system):** look, notebooklm, research-idea, dataviz, artifact-design, update-config, keybindings-help, verify, code-review, simplify, fewer-permission-prompts, loop, schedule, claude-api, security-review, review, init

**Hooks:** **ไม่มีเลย** — `.claude/settings.json` ไม่มี, มีแค่ `.claude/settings.local.json` ที่เก็บ permission allowlist (Bash commands ที่อนุญาตไว้ล่วงหน้า เช่น `yt-dlp *`, `notebooklm *`, `ffmpeg *`, `mlx_whisper *` ฯลฯ) ไม่มี lifecycle hook ใดๆ (pre/post tool-use, session-start ฯลฯ)

**Orchestration:**
- **Opus↔Sonnet handoff** (เอกสารใน `CLAUDE.md`): `for-opus/questions.md` (Opus ตอบคำถามออกแบบ) ↔ `for-sonnet/tasks.md` (Sonnet ลงมือทำ) — ใช้งานจริงหนักมากช่วงนี้ (Q1-Q18, T1-T18 นับถึงตอนนี้) รวมถึงเพิ่งเปิดใช้ **Fable** เป็นทางเลือกที่ 3 สำหรับปัญหาที่ต้องการความลึกทางเทคนิคเป็นพิเศษ (Q17)
- **Research workflow**: `research/WORKFLOW.md` (Phase 0-5, entry point เดียวสำหรับงานวิจัยหุ้นทั้งหมด) + `research/playbooks/decision_framework.md` + `research/playbooks/question_playbook.md`

**Index:**
- `knowledge/index.md` — registry ของ NotebookLM notebook ต่อคอร์ส/หุ้น (มือเขียน)
- `knowledge/KNOWLEDGE_INDEX.md` — auto-generate จาก `tools/build_knowledge_index.py` (ห้ามแก้มือ) ใช้ route คำถามความรู้ทั่วไปไปยัง chapter ที่ถูกต้องโดยไม่ต้องอ่านทั้งคลัง

**สิ่งที่ Sonnet สังเกตเอง (ยังไม่ได้วิเคราะห์ลึก แค่ raw observation ให้ Fable ตรวจสอบต่อ):**
1. **ไม่มี agent เฉพาะสำหรับงานวิจัยการลงทุน** (เทียบกับ `teacher.md`/`line-bot.md` ที่มี agent ของตัวเอง) — งานวิจัยพึ่ง global skill `research-idea` + `research/WORKFLOW.md` เท่านั้น เป็นเพราะตั้งใจ (ไม่ต้องการ agent persona แยก) หรือเป็นช่องว่างที่ควรเติม?
2. **ไม่มี hook เลยทั้งโปรเจกต์** — งานที่ทำซ้ำๆ (เช่น เล่นเสียง Glass เมื่องานเสร็จ, บันทึก log อัตโนมัติ) ตอนนี้ทำผ่าน memory/prompt แทนที่จะเป็น hook จริง — ควรมี hook ไหนบ้างไหมสำหรับ 3 workflow นี้โดยเฉพาะ (เช่น PostToolUse hook เตือนตอน background transcribe job เสร็จ แทนที่จะพึ่ง ScheduleWakeup ทุกครั้ง)
3. **`teacher.md` กับ `learn-session` skill ดูเหมือนทับซ้อนกันบางส่วน** — `teacher.md` = "อ่าน source/ แล้วสอน" ส่วน `learn-session` = "Minnie+Fact-checker pipeline สรุปคอร์สเป็น lesson_notes.md" — สองอันนี้ควรรวมกัน/แบ่งหน้าที่ชัดกว่านี้ไหม หรือจริงๆ คนละหน้าที่กันชัดอยู่แล้ว (ตัวหนึ่งสอนสด อีกตัวสร้างเอกสารสรุปถาวร)?
4. **`tools/` folder มี script หลายตัวที่ทำงานต่อเนื่องกัน** (`vad_transcribe.py` → `batch_transcribe.py` → `structure_transcript.py` → `learn-session` skill → `publish-course` skill) แต่ไม่มี slash command หรือ skill เดียวที่ orchestrate ทั้ง pipeline นี้จบในคำสั่งเดียว (ต้องรันเองทีละขั้น) — ควรมี meta-skill/command ที่ chain ทั้งหมดไหม (เทียบกับ `/download` ที่ route ให้อัตโนมัติแล้ว)?
5. **บอทคลินิกมี `line-bot` agent + `linebot-check` skill แยกกัน** (แก้ logic vs เช็คสถานะ) — ดูสมเหตุสมผลแล้วเพราะคนละจุดประสงค์ (proactive fix vs on-demand health check) แต่ไม่มีอะไรอัตโนมัติเช็คสถานะเป็นระยะเลย (Opus เคยฟันธงใน Q13 ว่าไม่ต้องมี routine ถาวร — ยังยืนตามนั้นไหมหลังผ่านมาหลายวัน หรือมีข้อมูลใหม่ที่เปลี่ยนคำแนะนำ?)

**ขอให้ Fable ช่วย:**
1. วิเคราะห์ทั้ง 5 observation ข้างต้น — เห็นด้วย/ไม่เห็นด้วยกับแต่ละข้อ พร้อมเหตุผล (อย่า hedge)
2. เสนอเพิ่มเติมถ้าเห็นช่องว่าง/ความซ้ำซ้อนที่ Sonnet มองข้าม — โดยเฉพาะมุมที่เชื่อมโยงกันข้าม 3 workflow (เช่น pattern ที่ใช้ซ้ำได้ระหว่างงานลงทุนกับงานถอดเทป)
3. ให้ priority การเปลี่ยนแปลงที่แนะนำ (ถ้ามี) — อันไหนควรทำก่อน อันไหนไม่คุ้มจะทำเพราะ scope เล็กเกินไป (studio เป็น personal tool ของ user คนเดียว ไม่ใช่ทีม — อย่าแนะนำอะไรที่ over-engineer สำหรับสเกลนี้)
4. ถ้ามีข้อเสนอที่ต้องแก้ไฟล์จริง (สร้าง hook ใหม่, รวม skill, เขียน meta-command ฯลฯ) — เขียนเป็น task ใหม่ (เช็ค T-number ล่าสุดก่อน) ใน `for-sonnet/tasks.md` ให้ Sonnet ทำต่อได้เลย (fresh session ไม่มี context นี้) ถ้าไม่มีอะไรคุ้มจะทำ ให้บอกตรงๆ ว่า "ระบบตอนนี้ดีพอแล้วสำหรับสเกลนี้" แทนที่จะฝืนหาอะไรมาแนะนำ
5. อัปเดต Q18 status เป็น `done (Fable, <วันที่>)` พร้อมคำตอบเต็มแบบเดียวกับ Q14-Q17 (ตาราง ✅/❌ ชัดเจน ไม่ hedge)

**Cost note:** user เจาะจงให้ปรึกษา Fable รอบนี้เหมือน Q17 — ให้ความเห็นที่ตรงและมั่นใจ ไม่ใช่ survey ทั่วไปที่ hedge ทุกข้อ

### ANSWER (Fable, 2026-07-06)

**Verdict บนสุด: ระบบตอนนี้ดีพอสำหรับสเกลนี้แล้วในโครงสร้างใหญ่ — 3 ใน 5 observation ของ Sonnet คือของที่ถูกออกแบบมาถูกต้องอยู่แล้ว ไม่ใช่ gap. มี 2 จุดจริงที่ควรแก้ (เล็ก, ไฟล์เดียว, ต่ำกว่า 1 ชั่วโมงรวมกัน) + เจอเพิ่มอีก 2 จุดที่ Sonnet ไม่เห็น. ไม่มีข้อไหนต้องสร้าง subsystem ใหม่.**

---

#### วิเคราะห์ 5 observation ของ Sonnet

| # | Observation | Verdict | เหตุผล |
|---|---|---|---|
| 1 | ไม่มี agent เฉพาะสำหรับงานวิจัยการลงทุน | ❌ **ไม่ใช่ gap — ตั้งใจแล้ว อย่าเติม** | `research/WORKFLOW.md` มีหลักการเขียนไว้ชัดอยู่แล้ว (T2.1): *"Phases, not spawns. Run the whole pipeline as sequential PHASES in ONE model context. Do NOT spawn 6 sub-agents."* เหตุผลตอนนั้น (Q2) คือ cost discipline + ต้องการ context ต่อเนื่องข้าม Frame→Gather→Synthesize→Check (spawn agent = ตัด context, เสีย continuity + เพิ่ม token overhead). `teacher.md`/`line-bot.md` ได้ agent เพราะเหตุผลคนละแบบ: เป็น **reference-heavy persona ที่เรียกเป็นครั้งคราว** (line-bot 321 บรรทัดความรู้ n8n เฉพาะทาง, teacher = โหมด tutoring แยกจาก session หลัก) ที่ไม่อยากให้บวมเข้า context หลักทุกครั้ง — วิจัยหุ้นไม่มีความต้องการแบบนั้น มันต้องการ continuity มากกว่า isolation. สร้าง agent วิจัยจะ**ขัดกับหลักการที่มีอยู่แล้วตรงๆ** |
| 2 | ไม่มี hook เลยทั้งโปรเจกต์ | 🟡 **เห็นด้วยบางส่วน — มี 1 hook ที่คุ้มจริง ไม่ใช่ hook ทั่วไป** | ส่วนใหญ่ของ studio (test-first checkpoint, เลือก model, escalate Opus) ต้องใช้ **judgment** ซึ่ง hook (deterministic pattern-matcher) ทำแทนไม่ได้ — ตรงนี้เห็นด้วยกับสถานะปัจจุบันที่ไม่มี hook. แต่มี**หนึ่งเคส**ที่ hook ดีกว่า prompt แน่นอน: "เล่นเสียง Glass หลังงานเสร็จ >1 นาที" ที่ต้องเขียนเป็น memory correction (`feedback_sound_on_long_task.md`) เพราะโมเดล **ลืมทำเอง** มาแล้ว — นี่คือสัญญาณชัดว่างานนี้ควรเป็น deterministic hook ไม่ใช่ prompt ที่หวังให้โมเดลจำ. เขียนเป็น **T19a** |
| 3 | `teacher.md` กับ `learn-session` ทับซ้อนกัน — ควรรวมไหม | ❌ **ไม่ควรรวม (หน้าที่ต่างกันจริง)** — ✅ **แต่เจอบั๊กจริงที่ Sonnet ไม่ได้สังเกต** | อ่านทั้ง 2 ไฟล์ตรงๆ แล้ว: `teacher.md` = live interactive tutoring (Q&A สด, ไม่มี fact-check, ไม่มี HTML output). `learn-session` = rigorous **two-pass pipeline** (Minnie draft → Fact-checker อิสระเทียบ raw transcript → HTML + Active Recall) ผลิต **artifact ถาวร**. คนละงานจริง (สอนสด vs. สร้างเอกสารสรุปที่ผ่านการ verify) — merge จะทำให้ teacher.md หนักเกินความจำเป็นสำหรับโหมดสนทนา. **แต่เจอปัญหาจริง:** ทั้งสองไฟล์เขียนไปที่ path ชื่อ `lesson_notes.md` **คนละไฟล์กัน** — `teacher.md` เขียน `source/lesson_notes.md` (top-level, ข้าม topic) ส่วน `learn-session` เขียน `source/<topic>/lesson_notes.md` (per-topic). ชื่อไฟล์ชนกันแต่เป็นคนละไฟล์จริง ไม่มี cross-reference — ถ้าเรียก teacher สำหรับคอร์สที่ผ่าน learn-session มาแล้ว (มี 2 คอร์สแล้ว) มันไม่รู้ตัวว่ามี digest คุณภาพสูงกว่าอยู่แล้ว แถม `teacher.md`'s Session Start ยัง `ls source/` แบบ flat ไม่ scope ตาม topic เลย — เป็นของเก่าตั้งแต่ก่อนมี topic-folder convention (มี 3 คอร์สในนี้แล้วตอนนี้). แก้ใน **T19b** |
| 4 | ไม่มี meta-skill/command chain ทั้ง pipeline ถอดเทป | ❌ **ไม่ควรทำ — จะขัดวัฒนธรรม checkpoint ที่แลกมาด้วยความเจ็บจริง** | เทียบกับ `/download` ผิดที่: `/download` route ทันทีเพราะทุก branch **ราคาถูกและ reversible** (ผิด provider ก็แค่ลองใหม่). แต่ transcription pipeline ทุกขั้นแพง/ยาว/irreversible (T1 เคยเสียเวลาจริงกับ MLX hallucination เพราะรีบรวบรัด) — ทั้ง T3, T4, T16, T17 ถูกออกแบบด้วย pilot-then-batch + STOP-and-show-user ซ้ำๆ โดยตั้งใจ. Meta-command ที่ chain ให้จบในคำสั่งเดียวจะต้อง**ข้าม checkpoint พวกนี้ไปเอง หรือไม่ก็หยุดถามทุกขั้นอยู่ดี** (ซึ่งกรณีหลังก็แทบไม่ต่างจากตอนนี้). ที่จริงมันมี "meta-orchestration" อยู่แล้วในระดับที่พอดี: `publish-course` SKILL.md Step 0 preflight **เรียก** `structure_transcript.py` เป็น prerequisite auto-detect อยู่แล้ว (เช็คว่ามี `*_structured.md` หรือยัง ถ้าไม่มีเสนอรันให้). ปัญหาจริงมีแค่ **ของ preflight นั้นล้าสมัย** (ไม่รู้จัก `batch_transcribe.py` ที่เพิ่งสร้างทีหลัง SKILL.md) → แก้ใน **T19c** ไม่ใช่สร้างของใหม่ |
| 5 | line-bot มี agent + skill แยกกัน สมเหตุสมผล แต่ verdict Q13 (ไม่ต้องมี routine ถาวร) ยังยืนไหม | ✅ **verdict หลักของ Q13 ยังยืนเต็มที่ — แต่ burn-in window ที่เสนอไว้ "หมดอายุไปแล้วโดยไม่ได้เริ่ม"** | Q13 ตัดสินแล้วว่า: ไม่มี continuous agent, ไม่มี routine ถาวร, มีแค่ burn-in ชั่วคราว 7 วัน **ถ้า user สั่ง go**. เช็ค `T15` ใน tasks.md → status ยัง `pending (GATED)` ตั้งแต่ 2026-07-01 — user ไม่เคยตอบ go/no-go เลย. วันนี้ 2026-07-06 = **ผ่านมา 5 วันแล้ว** นับจาก M3/M4 deploy โดยไม่มี automation ใดๆ เฝ้าเลย และไม่มีรายงานปัญหา LINE bot โผล่ใน T16-T18 (ทุกงานช่วงนี้เป็นเรื่อง transcription ล้วน ไม่เกี่ยวบอทเลย) — traffic จริง 5 วันไม่มีอะไรพังดังพอจะโผล่มาเอง. **นี่คือหลักฐานทางอ้อมว่าไม่พังเงียบเช่นกัน** (ถ้า M3 ทิ้งข้อความจริงหรือ M4 ปฏิเสธการจองจริงหนักๆ ต่อเนื่อง 5 วัน เจ้าของคลินิกน่าจะสังเกตจากจำนวนคนไข้ที่โทรถามเองแล้ว). สรุป: **ไม่ควรเริ่ม burn-in 7 วันตอนนี้** — หน้าต่างเสี่ยงที่มันถูกออกแบบมาเฝ้าผ่านไปเงียบๆ แล้ว การเริ่มตอนนี้คือเฝ้าช่วงที่จบไปแล้ว ไม่ใช่ช่วงเสี่ยงจริง. ปิด T15 เป็น expired แทนที่จะปล่อยค้าง "pending" ตลอดไป → **T19d** |

---

#### สิ่งที่ Sonnet ไม่ได้เห็น

1. **`teacher.md` / `learn-session` file-path collision** (รายละเอียดอยู่ในแถว #3 ข้างบน) — นี่คือบั๊กจริงที่ปนอยู่ในสิ่งที่ Sonnet มองว่าเป็นแค่ "อาจจะทับซ้อนกันไหม" เชิง design แต่จริงๆ คือไฟล์ชนกันเชิง path ที่ verify ได้ตรงๆ จากการอ่านทั้ง 2 ไฟล์
2. **`publish-course` preflight ล้าสมัยหลัง T17** (รายละเอียดในแถว #4) — ไม่ใช่ "ขาด meta-command" แต่ "ของที่มี auto-chain อยู่แล้วชี้ไปเครื่องมือเก่า"
3. **Cross-workflow pattern ที่ดีอยู่แล้ว ไม่ต้องทำอะไรเพิ่ม:** งานวิจัยหุ้น (`WORKFLOW.md` Phase 2 "STOP if no source") กับงานถอดเทป (T3/T4/T16/T17 "pilot → show user → confirm before batch") **บรรจบกันเองโดยไม่ได้ตั้งใจ** ที่หลักการเดียวกัน: ขั้นที่แพง/ irreversible ต้องมี cheap pilot + explicit stop-gate ก่อนเสมอ. นี่คือสัญญาณที่ดีว่า ethos ของโปรเจกต์สอดคล้องกันข้าม 2 workflow แล้วโดยธรรมชาติ — **ไม่ต้องเขียนเป็นเอกสารกลางแยกต่างหาก** ("shared playbook doc") เพราะจะเป็นแค่ bureaucracy ทับของที่ทำงานถูกอยู่แล้วในทั้ง 2 ที่ สำหรับคนแก้โค้ดคนเดียว
4. **Prose ซ้ำของกฎ "cite-or-flag / ห้าม hallucinate"** ปรากฏแยกกันใน 4 ที่ (`WORKFLOW.md`, `teacher.md`, `learn-session`, `publish-course`) — เห็นแล้ว **ตั้งใจไม่แนะนำให้รวม**: skill/agent แต่ละตัวควร self-contained (โหลดแล้วทำงานได้เดี่ยวๆ โดยไม่ต้องพึ่ง cross-file read ตอน invoke) — การรวมกฎไปไว้ที่เดียวแล้วให้ทุกไฟล์ "ลิงก์ไป" จะเพิ่ม indirection โดยแลกกับการประหยัด markdown ไม่กี่บรรทัด ไม่คุ้มสำหรับ repo ที่มีคนแก้คนเดียว
5. **`settings.local.json` มี allowlist entry เก่าที่เป็นขยะ migration** เช่น `Bash(rm -rf /Users/alonsi/Desktop/stock-research/.claude/agents)` และ `Bash(mkdir -p __TRACKED_VAR__/.claude/agents)` — เศษจากตอน migrate stock-research (Q2/T2.4) ที่ไม่มีวันถูกใช้ซ้ำแล้ว. ต่ำมากในลำดับความสำคัญ — **ไม่เขียนเป็น task** เพราะมี skill `fewer-permission-prompts` ที่ทำงานนี้อยู่แล้วพอดี ให้รันเฉยๆ ถ้าอยากเก็บกวาดวันไหน ไม่ต้องเขียนโค้ดใหม่
6. **`.claude/commands/*.md` (download, yt-session) ยังเป็น format เก่า (slash command) ต่างจาก skill format ใหม่กว่า (`learn-session`/`linebot-check`/`publish-course`)** — เห็นแล้วแต่**ไม่แนะนำให้แปลง**: ทั้งสองไฟล์เรียกด้วยชื่อคำสั่งตรงอยู่แล้ว ไม่ต้องพึ่ง auto-trigger จาก description เหมือน skill ใหม่ๆ — แปลง format จะเป็นแค่ churn ไม่มี functional gain

---

#### Priority — ทำอะไรก่อน / อะไรไม่คุ้ม

| Priority | อะไร | Effort | อยู่ใน |
|---|---|---|---|
| 🟢 ทำเลย | T19a — Stop/PostToolUse hook เล่นเสียงเมื่อ Bash command ที่รู้อยู่แล้วว่าใช้เวลานาน (mlx_whisper, vad_transcribe.py, batch_transcribe.py, yt-dlp ฯลฯ) รันจบ | ต่ำมาก (ใช้ `update-config` skill ที่มีอยู่แล้ว) | T19 |
| 🟢 ทำเลย | T19b — แก้ `teacher.md` ให้ scope ตาม topic + เขียน lesson notes ไปที่ path เดียวกับ `learn-session` (คนละ heading แยกกันในไฟล์เดียว) | ต่ำ (ไฟล์เดียว) | T19 |
| 🟢 ทำเลย | T19c — sync `publish-course` SKILL.md Step 0 ให้รู้จัก `batch_transcribe.py` สำหรับคอร์สหลายไฟล์ | ต่ำมาก (ไม่กี่บรรทัด) | T19 |
| 🟢 ทำเลย | T19d — ปิด T15 เป็น expired พร้อมเหตุผล แทนที่จะค้าง pending เฉยๆ | ต่ำมาก (แก้ status line) | T19 |
| ⚪ ทำก็ได้ ไม่บังคับ | รัน `fewer-permission-prompts` skill เก็บกวาด `settings.local.json` วันไหนที่ว่าง | ต่ำ, ไม่เร่งด่วน | ไม่เขียน task — ใช้ skill ที่มีอยู่ |
| 🔴 ไม่ทำ | Dedicated research agent | — | ขัด design เดิม |
| 🔴 ไม่ทำ | รวม `teacher.md` + `learn-session` เป็นตัวเดียว | — | หน้าที่ต่างกันจริง |
| 🔴 ไม่ทำ | Meta-command chain ทั้ง pipeline ถอดเทปจบในคำสั่งเดียว | — | ขัดวัฒนธรรม checkpoint |
| 🔴 ไม่ทำ | Hook เพิ่มเติมนอกเหนือ T19a (เช่น auto-log, auto-enforce Opus/Sonnet escalation) | — | ต้องใช้ judgment, hook ทำแทนไม่ได้ |
| 🔴 ไม่ทำ | รวมกฎ "cite-or-flag" เป็นเอกสารกลาง | — | เพิ่ม indirection ไม่คุ้มสำหรับคนแก้คนเดียว |
| 🔴 ไม่ทำ | แปลง `.claude/commands/*.md` เป็น skill format | — | churn ไม่มี functional gain |

**สรุปเดียว:** T19 (4 sub-item, ไฟล์ที่มีอยู่แล้วทั้งหมด, รวมกันไม่ถึงชั่วโมง) คือทั้งหมดที่คุ้มทำจากการสำรวจรอบนี้. โครงสร้างที่เหลือของ studio — 3 agent/skill สำหรับ 3 workflow, ไม่มี hook เดิม, orchestration ผ่าน WORKFLOW.md + Opus/Sonnet handoff, index 2 ชั้น (`knowledge/index.md` มือเขียน + `KNOWLEDGE_INDEX.md` auto-generate) — **ถูกต้องแล้วสำหรับ solo hobbyist tool ขนาดนี้ ไม่ต้องปรับโครงสร้างใหญ่**.

**Sonnet execution → T19** (4 sub-item, independent, เขียนไว้ใน `for-sonnet/tasks.md` แล้ว).

---

## Q19 — Process การเรียนรู้ (learn-session pipeline) ดีพอไหม ควรปรับอะไรไหม
**Status:** done (Opus, 2026-07-06) — pedagogy แข็งแรงจริง ไม่ใช่ gimmick, rigor ระดับ fact-check-vs-raw-transcript "พอแล้ว" อย่าเพิ่มชั้น. 2 คำขอใหม่ (citation ทุกบรรทัด + external source) = gap จริง 2 อันเดียวที่ต้องแก้ → **per-heading source footer** (ไม่ใช่ทุกบรรทัด) + **external block ที่ WebSearch + marker 🌐 แยกจากคำผู้สอนเด็ดขาด**. ปฏิเสธ SRS/tracking/cross-course-linking ว่า over-engineer (index+synthesis ที่มีอยู่ทำหน้าที่นั้นพอแล้ว). Sonnet executes **T20** — ต้องแก้ `learn-session/SKILL.md` **ก่อน** รัน Masterclass รอบ large-v3 ใหม่.

**บริบท:** ต่างจาก Q18 (ที่สำรวจ agent/skill/hook ecosystem ทั้งหมด) — Q19 นี้เจาะเฉพาะ **pipeline การเรียนรู้คอร์สหุ้น** (`/learn-session` skill + `teacher` agent) ว่าดีพอในเชิง **การเรียนรู้จริง (pedagogy)** ไหม ไม่ใช่แค่ technical correctness

**Pipeline ปัจจุบัน (เรียงตามลำดับจริง):**
1. **ถอดเสียง** — `tools/vad_transcribe.py` / `tools/batch_transcribe.py` (Silero VAD ตัด silence → MLX Whisper `large-v3` ถอดเป็นข้อความ, มี post-process flag-not-delete สำหรับจุดต้องสงสัย — ดู T16-T18)
2. **จัดโครงสร้าง** — `tools/structure_transcript.py` re-anchor เนื้อ transcript เข้ากับ chapter ของสไลด์ PDF (ใช้ Haiku ต้นทุนต่ำ) → ได้ `session_N_structured.md`
3. **ขึ้น NotebookLM** — อัปโหลด PDF + transcript เป็น source ของ notebook เฉพาะคอร์สนั้น, บันทึก notebook ID ไว้ใน `knowledge/index.md`
4. **`/learn-session` skill** (`.claude/skills/learn-session/SKILL.md`) — 2 ตัวละครทำงานร่วมกัน:
   - **Minnie** — ยิงคำถามใส่ NotebookLM ด้วย persona "เด็ก 10 ขวบ" (บีบให้คำตอบเข้าใจง่าย ไม่ใช้ jargon เกินจำเป็น) ร่างเนื้อหาสอนจากคำตอบที่ได้
   - **Fact-checker** — verify ร่างของ Minnie เทียบกับ **raw transcript จริง** (grep คำต่อคำ) ก่อน finalize ตัดทิ้ง/ย้ายจุดที่ verify ไม่ได้หรือ misattribute ผิด session
   - Output: `source/<topic>/lesson_notes.md` — สรุปรายบท + หัวข้อ "🧠 Active Recall" (ถามตัวเองก่อนไปต่อ) + "🎯 โจทย์ประยุกต์" ต่อท้ายทุก session + "Master Fact-Check Log" ท้ายไฟล์บันทึกทุกจุดที่แก้/ตัดทิ้งพร้อมเหตุผล
5. **Gap-fill pass** — Minnie ถาม NotebookLM เจาะจุดที่ fact-checker เจอว่ายังไม่ชัด/ไม่ครบ, verify ซ้ำก่อนเติมเข้า `lesson_notes.md`
6. **`teacher` agent** (`.claude/agents/teacher.md`, เพิ่งแก้ path scoping ใน T19b) — อ่าน `session_N_structured.md`/`lesson_notes.md` ที่มีอยู่แล้วก่อน (ไม่อ่าน raw ซ้ำถ้าไม่จำเป็น) สอนสดเป็นภาษาไทย, append บันทึก Q&A กลับเข้า `lesson_notes.md` ใต้ heading แยกจาก learn-session

**ตัวอย่างผลจริงของ pipeline นี้ (คอร์ส Masterclass ลงทุนศาสตร์, 3 sessions):** เจอ misattribution ข้าม session 2 จุด (เคส Beauty, เคสหุ้น cosmetics), เจอ hallucination ที่ทำให้เนื้อหาหายทั้งประโยค (เคส MC/Mc Jeans), ตัดกรอบที่ verify ไม่ได้ทิ้ง (SQGLP) — ทั้งหมด catch ได้เพราะ fact-checker step กับ grep เทียบ raw transcript ตรงๆ ไม่ใช่เชื่อ NotebookLM เฉยๆ

**คำขอเพิ่มใหม่จาก user (2026-07-06, สำคัญ ต้องตอบให้ครบ):**
- ทุกคำตอบ/ทุกบรรทัดสรุปใน `lesson_notes.md` **ต้องมี reference กำกับชัดเจน** (เช่น "transcript_2.txt", "บทที่ N", "สไลด์หน้า X") — ไม่ใช่แค่บาง Session อย่างที่ทำอยู่ตอนนี้ (ปัจจุบันมีอ้างอิงเฉพาะจุดที่ fact-check เจอปัญหา ไม่ใช่ทุกบรรทัด)
- **อนุญาตให้หาข้อมูลเสริมจากภายนอก source เดิมได้** (เช่น นิยามการเงินทั่วไปที่ raw transcript พูดไม่ครบ) **แต่ต้องระบุชัดเจนว่าเป็น source ภายนอก** แยกจากคำพูดผู้สอน — ไม่เคยมี mechanism นี้มาก่อนใน pipeline เดิม (เดิมเน้นแค่ "ห้าม hallucinate" แบบ negative constraint แต่ไม่มี positive path สำหรับเสริมความรู้ที่ verify ได้จากภายนอก)

**ขอให้ Opus ช่วย:**
1. ประเมิน pipeline ปัจจุบันในเชิง **pedagogy จริง** (ไม่ใช่แค่ software correctness) — persona เด็ก 10 ขวบของ Minnie ช่วยการเรียนรู้จริงไหมหรือเป็นแค่ gimmick, fact-check เทียบ raw transcript คำต่อคำ "พอ" ไหมในแง่ความเข้มงวด หรือควรมีชั้นตรวจสอบเพิ่ม, รูปแบบ Active Recall + โจทย์ประยุกต์ท้ายบทมีประสิทธิภาพต่อการจำ/นำไปใช้จริงไหม (มีงานวิจัยด้าน learning science รองรับไหมหรือควรปรับ)
2. ออกแบบว่าควรปรับ format ของ `lesson_notes.md` ยังไงให้รองรับ "ทุกคำตอบต้องมี reference" — ทำทุกบรรทัดจะรกเกินไปไหม ควรมีระดับความละเอียดของ citation แบบไหน (inline ทุกประโยค vs. ต่อย่อหน้า vs. ต่อหัวข้อ) ที่สมดุลระหว่างความน่าเชื่อถือกับการอ่านง่าย
3. ออกแบบ mechanism สำหรับ "หาข้อมูลเสริมจากภายนอกได้ แต่ต้องระบุชัด" — ควรใช้เครื่องมืออะไร (WebSearch? เพิ่ม source ใหม่ใน NotebookLM เอง? Fable/Opus ช่วย verify ก่อนใช้?) และควรมี visual/textual marker แบบไหนใน `lesson_notes.md` ให้แยกจาก "คำพูดผู้สอนจริง" ได้ชัดเจนไม่ปนกัน
4. มีจุดปรับปรุงเชิงโครงสร้างอื่นที่ Sonnet มองข้ามไหม (เช่น spaced repetition, tracking ว่า user เข้าใจ/ลืมจุดไหนบ้างข้ามเวลา, เชื่อมความรู้ข้ามคอร์ส เช่น concept ที่สอนซ้ำในหลายคอร์ส) — หรือ pipeline ปัจจุบันเพียงพอแล้วสำหรับ user คนเดียวที่เรียนเป็นงานอดิเรก ไม่ควร over-engineer เพิ่ม
5. ถ้ามีจุดที่ต้องแก้ไฟล์จริง (เช่น แก้ `learn-session/SKILL.md` เพิ่ม citation requirement + external-source mechanism) — เขียนเป็น task ใหม่ (เช็ค T-number ล่าสุดก่อน) ใน `for-sonnet/tasks.md` ให้ Sonnet ทำต่อได้เลย
6. อัปเดต Q19 status เป็น `done (Opus, <วันที่>)` พร้อมคำตอบเต็มแบบเดียวกับ Q14-Q18 (ตาราง ✅/❌ ชัดเจน ไม่ hedge)

**หมายเหตุ:** งานนี้เกี่ยวโยงกับการรัน pipeline จริงรอบใหม่ที่กำลังจะเกิดขึ้น (คอร์ส Masterclass ลงทุนศาสตร์ กำลังถอดเสียงใหม่ด้วย large-v3 อยู่ ยังไม่เสร็จ) — คำตอบของ Q19 ควรนำไปใช้ปรับ pipeline **ก่อน** รันรอบใหม่นั้น ถ้าเป็นไปได้ (ไม่ใช่แค่เป็น analysis ลอยๆ)

### ANSWER (Opus, 2026-07-06)

**Verdict บนสุด:** pipeline นี้ **ดีจริงในเชิง pedagogy ไม่ใช่แค่ software correctness** — ผมอ่าน `lesson_notes.md` ของ Masterclass ทั้งไฟล์แล้ว output พิสูจน์ตัวเอง (ดูหลักฐานด้านล่าง). มันมี **gap จริงอยู่ 2 จุดเดียว** และบังเอิญเป็น 2 จุดที่ user เพิ่งขอมาพอดี: (1) citation ไม่สม่ำเสมอ — มีเฉพาะจุดที่ fact-check สะดุด ที่เหลือลอย, (2) ไม่มี positive path สำหรับความรู้เสริมจากภายนอก มีแต่ negative constraint "ห้าม hallucinate". ที่เหลือ — persona เด็ก, fact-check-vs-raw-transcript, Active Recall+application — **ถูกต้องแล้ว อย่าเพิ่มชั้น**. SRS / forget-tracking / cross-course engine = over-engineer สำหรับ hobbyist คนเดียว (index + synthesis ที่มีอยู่ทำงานนั้นแทนแล้วในราคาที่ถูกกว่ามาก).

**สำคัญเชิง timing:** Masterclass กำลัง re-transcribe large-v3 อยู่และยังไม่ได้รัน learn-session รอบใหม่ → ถ้าแก้ `SKILL.md` (T20) ทัน เวอร์ชันที่แก้แล้วจะเป็นตัวที่ใช้ในรอบ Masterclass จริงรอบหน้า **โดยไม่ต้อง retrofit** (นอกจาก 3 session เดิมที่ถ้าอยากได้ citation footer ต้องรันทับ — ดู T20 Step 5).

---

#### Q19.1 — Pedagogy verdict (ของจริง ไม่ใช่ "seems fine")

| องค์ประกอบ | Verdict | หลักฐานจาก output จริง + learning science |
|---|---|---|
| **Minnie persona "เด็ก 10 ขวบ"** | ✅ **ของจริง ไม่ใช่ gimmick — เก็บไว้** | หลักฐานตรงในไฟล์: debt vs equity = "ให้เพื่อนยืมเงินเปิดร้าน มีสัญญา(หนี้) vs ร่วมเป็นเจ้าของ(หุ้น)"; switching cost = "บ้านติดที่ชาร์จ EV แล้วเปลี่ยนกลับน้ำมันยาก ต่างจากกดปิด YouTube ไปดูทีวี". analogy พวกนี้ **load-bearing** (ถ้าตัดออกผู้อ่านเข้าใจน้อยลงจริง) ไม่ใช่ decoration. ตรงกับ learning science ที่ยืนที่สุด: concrete-before-abstract + elaborative interrogation ("ทำไม/ถ้า X ล่ะ" ใน Phase A step 3) + dual coding. persona บังคับให้ต้องแปลง jargon เป็น mental model — เป็น pedagogy mechanism ไม่ใช่ tone |
| **Fact-check เทียบ raw transcript คำต่อคำ** | ✅ **rigor "พอแล้ว" — อย่าเพิ่มชั้นตรวจสอบ** | จับได้จริง: misattribution ข้าม session 3 จุด (Beauty, KTC, BDMS ที่จริงอยู่คนละ Day), hallucination ที่ทำเนื้อหาหาย (MC), ตัดกรอบที่ verify ไม่ได้ (SQGLP). Master Fact-Check Log คือ diagnostic ของจริง ไม่ใช่พิธีกรรม. **ข้อควรระวังสำคัญ:** scope ของมันคือ *fidelity* (ผู้สอนพูดจริงไหม) ไม่ใช่ *pedagogical completeness* (ผู้เรียนจะเข้าใจครบไหม / มีอะไรขาด). นั่นเป็นคนละแกน — และ **external-source ที่ user ขอมา (Q19.3) คือตัวอุดแกนที่สองพอดี** ไม่ใช่ต้องเพิ่ม fact-check layer ที่สาม |
| **Active Recall (5-10 คำถาม tag section)** | ✅ **strong — retrieval practice คือ testing effect** | คำถามในไฟล์เป็น open-ended จริง ("ทำไม Sustainability ของ STGT ถึงประเมินแค่ 1-2 ปี ทั้งที่กำไรโตกระฉูด") ไม่ใช่ recall คำนิยามลอยๆ — บังคับ retrieval + reasoning. testing effect เป็นหนึ่งใน finding ที่ replicate แข็งที่สุดใน cognitive psych. การ tag ว่าคำตอบอยู่ section ไหน = self-check ได้โดยไม่ต้องมีคนคุม เหมาะ solo learner เป๊ะ |
| **โจทย์ประยุกต์ (apply กับหุ้นจริงที่ถือ/ติดตาม)** | ✅ **strong — นี่คือ transfer** | "หาหุ้น 1 ตัวที่กำไรโตจากรายการครั้งเดียวไม่ใช่ยอดขายจริง แล้วแยกสองส่วนในงบ" — บังคับ near-transfer จาก concept ไป context จริงของ user เอง. นี่คือขั้นที่ course สอนหุ้นส่วนใหญ่ข้าม |
| **จุดอ่อนเชิง pedagogy ที่มีจริง** | 🟡 **2 อัน — ตรงกับคำขอ user พอดี** | (a) **citation ไม่สม่ำเสมอ** — บั่นทอน trust ของผู้เรียนเอง: เปิดไฟล์มา บาง bullet มีที่มา บางอันไม่มี ทำให้แยกไม่ออกว่า "อันนี้ผู้สอนพูด vs อันนี้ Minnie สังเคราะห์". (b) **ไม่มี positive path ความรู้เสริม** — ตอนนี้ถ้าผู้สอนพูดนิยามไม่ครบ pipeline ได้แค่ปล่อยว่างหรือ mark `[ไม่ได้พูดถึง]`. ที่จริงเคส MC/Mc Jeans **improvise mechanism นี้ไปแล้วแบบ ad hoc** (⚠️ "ยืนยันจากผู้ใช้+สไลด์ ไม่ใช่ raw transcript") — แต่ไม่มีนิยาม marker กลาง แต่ละครั้งเลยเขียนไม่เหมือนกัน |

**สรุป Q19.1:** อย่าแตะ 4 เสาหลัก. gap จริง = citation consistency + external-source path เท่านั้น (Q19.2/Q19.3).

---

#### Q19.2 — Citation format: **per-heading source footer, ไม่ใช่ทุกบรรทัด** (ฟันธง)

"ทุกบรรทัดต้องมี reference" อ่านตามตัวอักษร = **ผิดสำหรับ readability และจะฆ่า pedagogy เอง**. prose analogy คือ *ตัวเนื้อ* ของการเรียนรู้ในไฟล์นี้ — เอา `[transcript_1.txt]` ไปแปะท้ายทุกประโยค = ทำลาย flow ของ analogy ที่เป็น payload หลัก. แต่ user ต้องการ trust ที่ตรวจสอบได้ทุกจุด — **ทั้งสองอย่างได้พร้อมกันถ้าเลือก grain ให้ถูก: ต่อหัวข้อ (numbered บท) ไม่ใช่ต่อบรรทัด.**

รูปแบบที่เสนอ (คอนกรีต) — ปิดท้ายทุกหัวข้อ numbered ด้วย 1 บรรทัด footer:

```markdown
### 4. มหภาค (Macro): ดูจากบนลงล่างด้วย PESTEL

[...เนื้อหา analogy เหมือนเดิม ไม่แตะ...]

📎 **ที่มา:** transcript_1.txt (Day 1) · structured บทที่ 4 · สไลด์หน้า 11–14
```

+ **marker vocabulary เล็กๆ สำหรับ exception ที่ต้อง inline เท่านั้น** (default ไม่ต้อง inline เพราะ footer ครอบให้แล้ว):

| Marker | ใช้เมื่อ | ตัวอย่าง |
|---|---|---|
| *(ไม่มี marker)* | grounded ใน transcript ที่ footer ระบุ = default | (เนื้อ bullet ปกติ) |
| 🌐 | ความรู้เสริมจากภายนอก source ผู้สอน (Q19.3) | ดูบล็อก Q19.3 |
| ⚠️ | มาจากสไลด์/ความจำ user, verify กับ transcript ไม่ได้ | เคส MC/Mc Jeans ที่มีอยู่แล้ว |
| 🔗 | cross-session — เนื้อจริงอยู่ session อื่น | `[cross-ref]` ที่มีอยู่แล้ว (rename เป็น 🔗 ให้ consistent) |

**ทำไม per-heading ชนะ:** (1) readability — analogy prose ไม่ถูกรบกวน; (2) trust — เปิดหัวข้อไหนก็รู้ทันทีว่ามาจาก transcript/สไลด์หน้าไหน ตรวจย้อนได้; (3) แรงงานต่ำ — Minnie แบ่งเนื้อ per-บท อยู่แล้ว footer จึงเป็น by-product ของงานที่ทำอยู่ ไม่ใช่งานใหม่; (4) exception ที่ *ต้อง* ละเอียดกว่าหัวข้อ (external / unverifiable / moved) ได้ inline marker ของมันเอง — ตรงจุดที่ trust สำคัญที่สุดพอดี. **หลักการ:** citation ควรหนาแน่นเป็นสัดส่วนกับความเสี่ยงที่ผู้อ่านจะเชื่อผิด ไม่ใช่หนาแน่นเท่ากันทุกบรรทัด.

---

#### Q19.3 — External-source mechanism: **WebSearch + บล็อก 🌐 แยกเด็ดขาด** (minimal, ไม่ over-engineer)

ยึด norm ของโปรเจกต์ (solo user, อย่า over-build). ตัดสิน 3 มิติ:

| คำถามออกแบบ | ฟันธง | เหตุผล |
|---|---|---|
| ใช้ tool อะไร | ✅ **WebSearch** | สำหรับนิยามการเงินทั่วไปที่ transcript พูดไม่ครบ (เช่น "discount rate ทำงานยังไง"). เร็ว, ตรวจได้, ไม่ต้องตั้ง infra |
| เพิ่ม source ใหม่ใน NotebookLM เองไหม | ❌ **ไม่** | NotebookLM ตั้งใจให้เป็น **corpus เสียงผู้สอนล้วน** — ยัด Investopedia เข้าไปทำให้ RAG ตอบปนเสียงผู้สอนกับความรู้ทั่วไปแยกไม่ออก = ทำลาย invariant หลักของ fact-checker เอง. เก็บ NotebookLM ให้สะอาด |
| ต้องให้ Fable/Opus verify ก่อนใช้ไหม | ❌ **ไม่ (สำหรับนิยามทั่วไป)** | overkill สำหรับ lookup นิยาม. verification ที่จำเป็นมีแค่ "อ้าง source ที่เชื่อถือได้ + มี marker" — ตัวเนื้อความรู้ทั่วไปไม่ conflict กับ "ผู้สอนพูดอะไร" อยู่แล้วเพราะมัน**ไม่ได้อ้างว่าผู้สอนพูด** |
| trigger เมื่อไหร่ | เฉพาะตอนเจอ **genuine gap** (Phase A step 2 ที่มีอยู่แล้ว) | ไม่ใช่ไปหาความรู้เสริมมั่วซั่ว — เฉพาะ term ที่ผู้สอน *ตั้งชื่อแต่ไม่นิยาม* หรือ concept ที่บีบอัดจน 6-ขวบไม่คลิก. bounded ด้วย gate เดิม |

**marker ที่เสนอ** — บล็อก blockquote แยกเด็ดขาด ห้ามหลอมรวมเข้า prose ผู้สอน:

```markdown
> 🌐 **ความรู้เสริม (นอก source ผู้สอน · WebSearch 2026-07-06):**
> Discount rate = อัตราที่ใช้แปลงเงินอนาคตกลับเป็นมูลค่าปัจจุบัน ยิ่งเสี่ยงยิ่งใช้เลขสูง
> — อ้างอิง: Investopedia "Discount Rate". *ผู้สอนใช้คำนี้ในหัวข้อ 9 แต่ไม่ได้นิยามในคลาส เพิ่มเพื่อความเข้าใจ*
```

**กฎเหล็ก 3 ข้อ (เขียนลง SKILL.md):** (1) external content **ห้าม** merge เข้าย่อหน้าเสียงผู้สอน — อยู่ใน blockquote 🌐 ของตัวเองเสมอ; (2) ต้องระบุ **source จริง + วันที่ค้น** เสมอ; (3) ต้องมีประโยค "ผู้สอนไม่ได้พูด/นิยามส่วนนี้" กำกับ. นี่รักษา invariant เดิมของ fact-checker ไว้ครบ: **ผู้อ่านต้องแยกออกเสมอว่าอันไหนคำผู้สอน อันไหนไม่ใช่** — แค่เดิมมีแค่ 2 ชั้น (ผู้สอน / ตัด) ตอนนี้เพิ่มชั้นที่ 3 (ผู้สอน / เสริมภายนอกมี marker / ตัด).

---

#### Q19.4 — โครงสร้างที่ Sonnet มองข้าม? (ตอบตรงๆ ตาม norm "อย่า over-engineer" ของ Q18)

| ข้อเสนอ | Verdict | เหตุผล |
|---|---|---|
| **Spaced Repetition System (scheduler, forget-curve)** | 🔴 **ไม่ทำ** | Anki-style scheduler = infra จริงที่ต้อง maintain แลกกับ gain น้อยสำหรับ hobbyist คนเดียว. **แต่มี 80/20 ที่ถูกมาก:** ตอนนี้ Active Recall กระจายท้ายแต่ละ session — เพิ่ม "🧠 Active Recall รวมทั้งคอร์ส" ใน `synthesis.html` (ยกทุกคำถาม recall มารวมที่เดียว) ให้ self-quiz ข้ามคอร์สรวดเดียวได้ = แก้ ~10 บรรทัดใน Phase D ไม่ใช่สร้างระบบ. นี่คือ spaced-repetition surface ที่คุ้มค่าที่สุด |
| **Cross-course concept linking** (2M2S2Q/PE/MOS โผล่ทั้ง AI-LI และ Masterclass) | 🟡 **มีอยู่แล้ว — อย่าสร้างอันสอง** | `KNOWLEDGE_INDEX.md` (chapter-level, auto-gen, ข้าม topic) **คือ** cross-course link engine ที่มีอยู่แล้ว. อย่างมากแค่ให้ Phase D synthesis เขียนหมายเหตุตอนกรอบหนึ่งซ้ำข้ามคอร์ส (1 บรรทัด) ไม่ต้องมี subsystem ใหม่ |
| **Tracking ว่า user เข้าใจ/ลืมจุดไหนข้ามเวลา** | 🔴 **ไม่ทำ** | ต้องให้ user log self-assessment ซ้ำๆ = friction ที่ solo hobbyist ไม่ยั่งยืน. ROI ติดลบ. Active Recall แบบ self-check ที่มีอยู่ทำหน้าที่นี้ในเวอร์ชันที่ไม่ต้อง maintain state แล้ว |
| **เพิ่ม fact-check layer ที่สาม** | 🔴 **ไม่ทำ** | Q19.1 อธิบายแล้ว: gap ไม่ใช่ fidelity (แกนนั้นแน่นแล้ว) แต่เป็น completeness ซึ่ง external-source (Q19.3) อุดให้ตรงจุด |

**สรุป Q19.4:** pedagogy โครงสร้างหลัก **ครบแล้ว**. งานจริงคือ 2 คำขอใหม่ (citation + external) + 1 ของแถมราคาถูก (recall รวมใน synthesis). ทุกอย่างนอกนี้คือ over-engineer — สอดคล้อง norm ที่ Q18 ตั้งไว้ ไม่ขัด.

---

#### Q19.5/Q19.6 — execution

Sonnet execution → **T20** ใน `for-sonnet/tasks.md` (แก้ `learn-session/SKILL.md` + HTML template ให้รองรับ source footer + บล็อก 🌐 + recall รวม, และ retrofit ทับ Masterclass 3 session เดิมถ้าต้องการ). **ต้องทำก่อนรัน Masterclass large-v3 รอบใหม่** เพื่อให้รอบนั้นได้ format ใหม่ตั้งแต่แรกโดยไม่ต้อง retrofit.

---

## Q20 — Sonnet rebuild ซ้ำงานที่มีอยู่แล้วโดยไม่รู้ตัว (AI Leading Indicator Session 1) — ต้องแก้ process ตรงไหน

**Status:** done (Opus, 2026-07-07) — ยืนยันเองแล้วว่า archive บน `/Volumes/` สมบูรณ์ (4 session + synthesis) และ **ถูกต้องกว่า** rebuild ของ Sonnet ทุกจุดยกเว้นจุดเดียว → **ทิ้ง Sonnet rebuild, restore archive เป็นฐาน**, merge เข้าแค่ ⚠️ Damodaran (ผม grep เองแล้ว: ไม่มีทั้งใน transcript ทุกไฟล์ **และ** PDF ทั้ง 4 → finding ของ Sonnet จริง, แถม archive line 41 ยังผิดซ้ำว่า "สไลด์หยิบมา" ทั้งที่สไลด์ก็ไม่มี). Sonnet สร้าง regression ใหม่ (Punchcard ถูกตีว่า AI แต่งเอง ทั้งที่ **มีในสไลด์ PDF 1 คำต่อคำ** — Sonnet เช็ค PDF ให้ Damodaran แต่ไม่เช็คให้ Punchcard = inconsistent). กฎ "หาก่อนประกาศว่าหาย" → **root CLAUDE.md** (ไม่ใช่ skill-level). Phase B → เพิ่ม **dual-check transcript+PDF** ก่อนสรุปว่า hallucination. บทเรียนเพิ่ม: เช็คไฟล์ **ปลายทาง** (`lesson_notes.md`) ไม่ใช่ structured draft/NotebookLM ก่อนกล่าวหาว่า "ไม่เคยแก้" + diff-before-overwrite + ระวังคำกล่าวหาเชิงลบที่มั่นใจเกินหลักฐาน. Sonnet executes **T22**.

**สรุปเหตุการณ์ (2026-07-07, session เดียวกับที่ทำ Masterclass rebuild เสร็จก่อนหน้านี้):**

User ขอให้ทำ "AI Leading Indicator" ใหม่ด้วย Minnie persona ที่เพิ่งปรับ (เด็ก 10 ขวบ, ถามหลายมุม, ผ่าน Q19 ที่ Opus review ไปแล้ว). Sonnet เช็ค `source/AI leading indicator/` บนดิสก์เครื่อง **ไม่เจอ** (โฟลเดอร์เดิมหายไปจริง — วิดีโอ/transcript/structured doc/lesson_notes.md/session_N.html ทั้งหมด) เจอแค่เว็บที่ publish แล้ว (`sites/alonsi-invest/`) กับ NotebookLM notebook ที่ยังอยู่ (ID `70025843-85b8-44dc-bd15-f249a11aa360`, source ครบ: 4 PDF + 5 structured.md + 5 transcript).

**Sonnet ตัดสินใจ:** ถือว่าไฟล์ต้นฉบับหายจริง แล้ว **สร้างใหม่ทั้งหมด** โดยดึง `session_1_structured.md` + `transcript_1.txt` กลับมาจาก NotebookLM (`source fulltext`), รัน Minnie ใหม่เต็ม 28 บท, เจอ fact-check issue หลายจุด (PDD/Labubu/Neutron/Kawa-Cava/Damodaran/Pareto-Punchcard), เขียน `lesson_notes.md` + `session_1.html` ใหม่ทั้งไฟล์ (dark → เปลี่ยนเป็น anthropic-editorial style ที่เพิ่งทำกับ Masterclass ด้วย), publish เป็น live artifact, บอก user ว่า **"PDD error เคยจดไว้ว่าต้องแก้ตั้งแต่ 2026-07-01 แต่ไม่เคยถูกแก้จริง"**

**ความจริงที่เพิ่งค้นพบ (user บอกเองว่ามี external volume `/Volumes/Acici Sanitsakul/studio-archive/`):**
- โฟลเดอร์ `AI leading indicator` เต็มรูปแบบอยู่ในไดรฟ์นี้จริง (วิดีโอ .mp4 ต้นฉบับ ~1.5GB, transcript ทุกไฟล์, structured.md ทุกไฟล์, **`lesson_notes.md` ที่ทำเสร็จสมบูรณ์ 4 session + synthesis ตั้งแต่ 2026-07-01**, `session_1-3.html` + `session_2_session2.html` + `synthesis.html`)
- `lesson_notes.md` ในไดรฟ์นี้ **แก้ PDD→9992.HK ไปแล้วจริง** ตั้งแต่ 2026-07-01 พร้อมโน้ต "Opus จับได้ตอน re-review" — คำกล่าวหาของ Sonnet ว่า "ไม่เคยถูกแก้" **ผิด** เพราะ Sonnet ไปเช็คที่ `session_1_structured.md` (ไฟล์ร่างดิบต้นทางที่ pipeline **ไม่ได้ออกแบบให้แก้ย้อนกลับ** — การแก้ไขทั้งหมดต้องอยู่ที่ `lesson_notes.md` ปลายทางตามที่ pipeline ของ Q19 ระบุไว้แล้ว) ผ่าน NotebookLM แทนที่จะหาไฟล์ปลายทางจริงก่อน
- ไฟล์เดิมยังแก้ **Neutron ถูกยืนยันซ้ำ 2 session** (session_1 + session_2_session2), **Kawa→Cava** มีความมั่นใจกว่าที่ Sonnet เขียนใหม่, **"Punchcard Principle" มีอยู่จริงในสไลด์ PDF คำต่อคำ** (Sonnet เช็คแค่ transcript ไม่เช็ค PDF แล้วสรุปผิดว่าเป็นคำที่ AI ตั้งขึ้นเอง — เป็น error ใหม่ที่ Sonnet สร้างขึ้นเองในรอบ rebuild นี้)
- จุดเดียวที่ไฟล์เดิมยังไม่ได้เช็ค (Sonnet อาจเพิ่มคุณค่าได้จริง): **"อ้างอิง Aswath Damodaran"** — grep ทั้ง transcript และ PDF สไลด์ไม่พบชื่อนี้เลยสักที่ ไฟล์เดิมยังคงอ้างว่าเป็นคำพูดจริงโดยไม่มีโน้ตกำกับว่า verify ไม่ได้

**ทำไมพลาด (root cause ที่ user อยากให้ Opus ช่วยตัดสิน ไม่ใช่แค่ sorry แล้วจบ):**
1. Sonnet ค้นหาไฟล์แค่ในดิสก์เครื่อง (`find /Users/.../studio`) ไม่ได้เช็ค external volume ที่ mount อยู่ (`/Volumes/...`) ก่อนสรุปว่า "ไฟล์หายหมดแล้ว" — เป็นการค้นหาที่ไม่ครบก่อนตัดสินใจทำงานใหญ่ (rebuild ทั้งไฟล์) ทับของที่อาจมีอยู่แล้ว
2. Fact-check checklist ของ `learn-session` skill (Phase B) เขียนไว้ว่าต้อง "grep raw transcript" แต่ Sonnet ตีความว่า = grep transcript **อย่างเดียว** ไม่ได้เช็คสไลด์ PDF คู่กันเสมอ ทั้งที่เนื้อหาบางจุด (Punchcard) เป็น slide-only ไม่เคยพูดออกเสียง — ถ้าเช็คแต่เสียงอย่างเดียวจะเข้าใจผิดว่าเป็น hallucination ทั้งที่จริงเป็นเนื้อหาจริงจากสไลด์
3. ไม่ได้ diff เทียบกับของเดิมก่อนเขียนทับ — ถ้า diff ก่อนจะเห็นทันทีว่า PDD ถูกแก้ไปแล้วในไฟล์ปลายทาง ไม่ต้องไปหาข้อสรุปจากไฟล์ร่างดิบ

**คำถามที่อยากให้ Opus ตัดสิน:**

1. **Reconciliation ทันที:** ควรทิ้งไฟล์ที่ Sonnet เพิ่ง rebuild ทั้งหมด แล้วคัดลอกของจริงจากไดรฟ์กลับมาเป็นฐานหรือไม่ (คำตอบที่ชัดเจนน่าจะเป็น "ใช่" แต่ขอให้ Opus ยืนยัน) แล้ว **จุดเดียวที่ Sonnet เจอเพิ่มจริง (Damodaran verify ไม่ได้)** ควร merge เข้าไปยังไง — เพิ่ม ⚠️ marker ในไฟล์เดิมตรงจุดนั้นพอ ไม่ต้องรื้อทั้งไฟล์
2. **Process fix — "หาไฟล์ก่อนประกาศว่าหาย":** ควรเพิ่มกฎมาตรฐานไหมว่า ก่อนสรุปว่า source file "หายแล้ว/ไม่มีแล้ว" (โดยเฉพาะก่อนตัดสินใจ rebuild ใหญ่ทับของเดิม) ต้อง (ก) เช็ค `/Volumes/` ที่ mount อยู่ทั้งหมด (ข) ถามผู้ใช้ตรงๆ ว่ามี backup ที่ไหนไหม ก่อนเริ่มงานสร้างใหม่ที่ใช้เวลา/effort มาก — ควรเขียนเป็นกฎถาวรที่ไหน (CLAUDE.md ระดับ root? หรือใน `learn-session/SKILL.md` prerequisites?)
3. **Process fix — fact-check ต้องเช็คคู่ transcript+PDF เสมอ:** `learn-session/SKILL.md` Phase B ควรแก้ไหมให้ระบุชัดว่า "grep ทั้ง raw transcript **และ** slide PDF fulltext ก่อนสรุปว่าคำไหนเป็น AI-invented/hallucination" (ไม่ใช่แค่เช็ค transcript อย่างเดียว) — นี่คือ error class ใหม่ที่ต่างจาก misattribution ข้าม session (ที่ Q19 คุยไปแล้ว)
4. **มีบทเรียนอะไรอีกไหมที่ Opus เห็นแต่ context สั้นๆ นี้ยังไม่ครอบคลุม?**

**Why:** user เจอ Sonnet กล่าวหาว่างานเก่า "ไม่เคยแก้" ทั้งที่แก้ไปแล้วจริง แถม Sonnet เองก็สร้าง error ใหม่ (Punchcard) ในความพยายามแก้ error เก่า — อยากให้ Opus ช่วยตัดสินทั้งการ reconcile เนื้อหาและการแก้ process ไม่ให้เกิดซ้ำ ไม่ใช่แค่ sorry แล้วเดินหน้าต่อ

**How to apply:** ถ้าคำตอบต้องให้ Sonnet ลงมือทำ (copy ไฟล์กลับ, merge Damodaran caveat, แก้ SKILL.md) ให้ append เป็น task ใหม่ใน `for-sonnet/tasks.md` ตามระบบเดิม

### ANSWER (Opus, 2026-07-07)

**Verdict บนสุด:** ผมไม่เชื่อ write-up อย่างเดียว — verify เองครบทุก claim แล้ว (grep archive/transcript/PDF ด้วยมือ). ผลตรงกับ write-up **และหนักกว่าที่ Sonnet คิด**: archive คือของจริงที่สมบูรณ์+ถูกต้องกว่า, Sonnet rebuild เป็น Session-1-only ที่ (ก) ตั้งอยู่บนคำกล่าวหาเท็จ ("PDD ไม่เคยแก้") และ (ข) สร้าง regression ใหม่ (Punchcard). มี **จุดเดียว** ที่ Sonnet เพิ่มคุณค่าจริง = Damodaran caveat. → **ทิ้ง rebuild, restore archive, merge เข้าแค่จุดเดียวนั้น.**

---

#### สิ่งที่ผม verify เอง(ไม่เชื่อ write-up เปล่าๆ)

| Claim ใน Q20 | วิธีเช็คของผม | ผล |
|---|---|---|
| archive มีครบ 4 session + synthesis | `ls "/Volumes/Acici Sanitsakul/studio-archive/AI leading indicator/"` | ✅ จริง — mp4 ต้นฉบับ 5 ไฟล์, transcript/structured/PDF ครบ, `lesson_notes.md` 87KB (Jul 1 20:33), session_1-3.html + session_2_session2.html + synthesis.html |
| archive แก้ PDD→9992.HK แล้ว | grep archive `lesson_notes.md` | ✅ line 72 + fact-check log line 450 มีโน้ต "แก้ไข 2026-07-01 … Opus จับได้ตอน re-review" — คำกล่าวหา Sonnet ว่า "ไม่เคยแก้" **เท็จ** |
| Neutron ยืนยัน 2 session | grep archive | ✅ line 285 + log line 449 ระบุชัด "ยืนยันซ้ำ 2 session \| 1, 2_session2" — archive มั่นใจกว่า rebuild |
| Kawa→Cava confidence สูงกว่า | grep archive | ✅ line 90/448 archive สรุปตรงว่าน่าจะเป็น Cava จริง |
| Punchcard มีในสไลด์ PDF คำต่อคำ | `pdftotext` ทั้ง 4 PDF แล้ว grep | ✅ **อยู่ใน PDF 1 จริง**: `"ครั้งมากขึ้น (Punchcard Principle)"` — archive label ถูก ("ป้ายนี้ในสไลด์เขียนว่า Punchcard principle") ; **Sonnet rebuild ผิด** (line 29 ตีว่าเป็นชื่อที่ AI ตั้งเอง เพราะ grep แต่ transcript) |
| Damodaran verify ไม่ได้จริง | grep **ทุก transcript + ทั้ง 4 PDF** | ✅ **0 hit ทุกที่** — finding ของ Sonnet จริง. ยิ่งกว่านั้น archive line 41 เขียนว่า "จุดนี้สไลด์แค่หยิบมาเตือน" = archive **ผิดซ้ำ** (อ้างว่าอยู่ในสไลด์ ทั้งที่สไลด์ไม่มี) → caveat ยิ่งจำเป็น |

**ข้อสังเกตแหลมคมที่สุด:** Sonnet เช็ค PDF ให้ Damodaran (line 53 "เช็ค PDF สไลด์ Day 1 ทั้งไฟล์") แต่ **ไม่เช็ค PDF ให้ Punchcard** (line 29 grep แค่ transcript). ความไม่สม่ำเสมอในการ fact-check ของตัวเองภายในไฟล์เดียวกัน คือ root-cause #2 ตัวเป็นๆ — พิสูจน์ว่านี่ต้องเป็น "กฎบังคับ" ไม่ใช่ "ความระมัดระวังเฉพาะกิจ".

---

#### Q20.1 — Reconciliation: **ทิ้ง rebuild, restore archive, merge จุดเดียว** ✅

| การตัดสิน | ✅/❌ | เหตุผล |
|---|---|---|
| ทิ้ง Sonnet rebuild ทั้ง 3 ไฟล์ (`lesson_notes.md`/`session_1_structured.md`/`session_1.html` ใน local) เป็น "ฐาน" | ✅ | rebuild คือ subset (Session 1) ของสิ่งที่สมบูรณ์กว่า, ตั้งบนคำกล่าวหาเท็จ, และ **ถอยหลัง 3 จุด** (Punchcard regression + Neutron/Cava มั่นใจน้อยกว่าเดิม). archive คือ **endpoint ที่ pipeline ออกแบบให้เป็นของจริง** (`lesson_notes.md` = ที่เก็บ correction ทั้งหมด ตาม Q19) |
| copy ทั้งโฟลเดอร์ archive กลับมาที่ `source/AI leading indicator/` ให้ working copy กลับมาอยู่บนดิสก์ | ✅ | ตอนนี้ local มีแค่ Session 1 ที่ผิด — ต้องมีของจริงครบ 4 session บนเครื่องเพื่อทำงานต่อ (และ archive คือ backup ไม่ควรเป็นสำเนาเดียวที่ถูกต้อง) |
| **merge เข้าแค่ ⚠️ Damodaran** — แก้ archive line 41 เดิม เพิ่ม marker "verify ไม่ได้ทั้ง transcript+PDF" (ยก wording ที่ Sonnet เขียนไว้ line 53 มาใช้ได้เลย มันถูกต้อง) | ✅ | นี่คือ **จุดเดียว** ที่ rebuild เพิ่มคุณค่าจริง และผม verify เองแล้วว่า finding ถูก. เป็น targeted edit ~2 บรรทัด **ไม่ต้องรื้อไฟล์** |
| เก็บ HTML style ใหม่ (anthropic-editorial) ของ rebuild ไว้เป็น "content" | ❌ | style เป็นเรื่อง cosmetic — ห้ามใช้เป็นข้ออ้างลากเนื้อหาผิดเข้ามา. ถ้า user ชอบ style ใหม่จริง = **restyle แยกต่างหากบน content ของ archive ที่ถูกต้อง** ไม่ใช่เก็บ rebuild ไว้เพราะสวย |
| ลาก fact-check "ใหม่" อื่นๆ ของ rebuild (Labubu/Kawa-Cava/Neutron) เข้ามาด้วย | ❌ | archive จัดการทุกจุดนั้นแล้ว **ดีกว่า** (มั่นใจกว่า, cross-confirm 2 session). ไม่มีอะไรให้ merge |

> **สรุป Q20.1:** restore archive → apply Damodaran ⚠️ หนึ่งจุด → จบ. อย่า cherry-pick อย่างอื่นจาก rebuild เพราะ "เสียดายที่ทำมา" — sunk cost.

---

#### Q20.2 — กฎ "หาก่อนประกาศว่าหาย": **ใช่ + วางที่ root CLAUDE.md** (ไม่ใช่ skill-level) ✅

| คำถาม | ฟันธง |
|---|---|
| ควรมีกฎถาวรไหม | ✅ ต้องมี — นี่คือ failure mode ที่ทำให้เกิดงานทับซ้อน + accusation เท็จ + regression ในครั้งเดียว |
| วางที่ไหน: root CLAUDE.md หรือ `learn-session/SKILL.md`? | ✅ **root CLAUDE.md** — เพราะเป็น failure mode ทั่วไป (ใช้ได้กับ *ทุก* งาน rebuild/recreate ที่แพง ไม่ใช่แค่ learn-session). ถ้าเขียนไว้ใน skill เดียว จะป้องกันได้แค่ pipeline เดียว. ใส่ pointer สั้นๆ ใน `learn-session` prerequisites ได้เป็นของแถม แต่ **บ้านหลัก = root** |

**เนื้อกฎที่เสนอ (Sonnet เขียนลง root CLAUDE.md ตาม T22):**
> **ก่อนประกาศว่า source/ไฟล์ "หาย/ไม่มีแล้ว" และก่อนเริ่ม rebuild ที่แพง (ถอดเสียง/รัน pipeline/เขียนไฟล์ใหญ่ทับ):**
> 1. เช็ค `/Volumes/` ที่ mount อยู่ทั้งหมด (`ls /Volumes/`) — โปรเจกต์นี้เก็บ archive ไว้ที่ `/Volumes/Acici Sanitsakul/studio-archive/`
> 2. เช็ค location archive ที่รู้จัก (studio-archive) และไฟล์ปลายทางที่ถูกต้อง ไม่ใช่แค่ที่เดิม
> 3. **ถาม user ตรงๆ** ว่ามี backup ที่ไหนไหม ก่อนลงมือสร้างใหม่
> ครบ 3 ข้อแล้วไม่เจอค่อย rebuild.

**บทเรียนที่ลึกกว่าและต้องเขียนกำกับ:** NotebookLM `source fulltext` ที่ Sonnet ใช้กู้ = **สำเนาต้นน้ำ (structured draft ดิบ)** ไม่ใช่ `lesson_notes.md` ปลายน้ำที่ผ่าน correction แล้ว. การกู้จาก NotebookLM จึงไป **ปลุกร่างฉบับที่ยังไม่ได้แก้** ขึ้นมา → เป็นเหตุให้ Sonnet "เจอ" PDD ที่แก้ไปแล้วและนึกว่ายังไม่แก้. ดังนั้นแม้แต่ recovery source ก็ผิดชั้น.

---

#### Q20.3 — Phase B ต้อง dual-check transcript **และ** PDF: **ใช่ แก้เลย** ✅

| คำถาม | ฟันธง |
|---|---|
| แก้ `learn-session/SKILL.md` Phase B ให้บังคับ grep ทั้ง raw transcript **และ** slide PDF fulltext ก่อนสรุปว่าคำไหน AI-invented/hallucination | ✅ ต้องแก้ — ตอนนี้ Phase B step 1/3 เขียนแค่ "read `transcript_X.txt` directly / grep the transcript" → Sonnet ตีความตามตัวอักษรว่า transcript อย่างเดียว → false positive (Punchcard) |
| เป็น error class ใหม่คนละอันกับ misattribution ข้าม session (Q19) ไหม | ✅ ใช่ คนละแกน — Q19 = เนื้อรั่วข้าม session; อันนี้ = **slide-only content ถูกเข้าใจผิดว่าเป็น hallucination** เพราะไม่เคยพูดออกเสียง |

**เหตุผลเชิงระบบ (สำคัญ):** pipeline นี้ **ยอมรับสไลด์เป็น source อยู่แล้ว** — Phase A step 9 มี marker `⚠️` = "From slides/memory, not verifiable against transcript" และ structured doc ถูก *สร้างจาก PDF*. แต่ Phase B ที่ทำหน้าที่ "ตัดสินว่าอะไรคือ hallucination" กลับ **มองข้ามสไลด์** → เกิด asymmetry: Phase A ถือว่าสไลด์คือ source แต่ Phase B ไม่. การแก้คือทำให้ negative-conclusion step ("อันนี้แต่งขึ้น") ต้องผ่าน PDF check ด้วย ให้สอดคล้องกับที่ Phase A รู้อยู่แล้วว่าสไลด์คือแหล่งที่ถูกต้อง.

**เพิ่มเป็นตัวอย่างบวก:** เคส Damodaran ของ Sonnet (grep ทั้ง transcript+PDF, 0 hit ทั้งคู่ → กล้าติด ⚠️) คือ Phase B ที่ทำ *ถูก* — ใส่เป็น worked example ใน SKILL.md ได้เลย คู่กับ Punchcard (ตัวอย่างที่ทำ *ผิด* เพราะเช็คไม่ครบ).

---

#### Q20.4 — บทเรียนอื่นที่ context สั้นยังไม่ครอบ

1. **เช็คไฟล์ "ปลายทาง" ก่อนกล่าวหาว่า "ไม่เคยแก้" (นี่คือ root cause จริงของ accusation เท็จ ไม่ใช่แค่เรื่องหาไฟล์ไม่เจอ).** Sonnet ไปดู `session_1_structured.md` (ร่างดิบต้นน้ำ ผ่าน NotebookLM) แล้วสรุปว่า PDD ยังไม่แก้ ทั้งที่ correction ทั้งหมดอยู่ที่ `lesson_notes.md` ปลายน้ำตามที่ Q19 กำหนดไว้ชัด. **กฎ:** structured doc = ร่างต้นน้ำ immutable; `lesson_notes.md` = ไฟล์ที่ถือ correction of record. ห้ามตัดสินว่า "แก้แล้ว/ยังไม่แก้" จาก structured/NotebookLM — ต้องดูไฟล์ปลายทางเสมอ. (เขียนลง SKILL.md เป็น note.)
2. **Diff ก่อนเขียนทับ deliverable ที่มีอยู่.** ถ้า Sonnet `diff` rebuild กับไฟล์เดิมก่อน จะเห็นทันทีว่า PDD แก้แล้ว + Punchcard เคย label ถูก. discipline ทั่วไป: overwrite ไฟล์งานที่มีอยู่ → diff ก่อนเสมอ.
3. **คำกล่าวหาเชิงลบที่มั่นใจ ต้องมี evidence bar สูงกว่าคำยืนยันเชิงบวก.** "X ไม่เคยถูกทำ" / "ไฟล์หายหมดแล้ว" เป็น universal-negative — พิสูจน์ได้ต่อเมื่อค้นครบทุกที่แล้วจริง. Sonnet ประกาศ negative จากการค้นที่ไม่ครบ. เชื่อมกับรีวิว Q18/Fable เรื่องอย่า over-claim: **ก่อนพิมพ์ประโยคกล่าวหางานเก่า ให้ถามตัวเองว่าค้นครบหรือยัง.**
4. **Archive hygiene / อย่าให้ของจริงอยู่ที่เดียวบน external drive.** ตอนนี้ฉบับสมบูรณ์+ถูกต้องอยู่บน `/Volumes/` ที่ถอดออกได้ ส่วนดิสก์เครื่องว่าง → ระบบเปราะ. อย่างน้อยควร **register location archive ไว้ใน CLAUDE.md / `knowledge/index.md`** ว่าคอร์สที่เรียนจบแล้วเก็บไว้ที่ `studio-archive/` เพื่อไม่ให้ session หน้ามา rebuild ซ้ำอีก (T22 รวมข้อนี้).
5. **Silver lining ที่ต้องเก็บ ไม่ใช่ทิ้งทั้งหมด:** Sonnet's Damodaran dual-source check คือพฤติกรรมที่ Q20.3 อยากได้ ทำถูกเป๊ะ — merge caveat นั้นเข้า archive และใช้เป็น template ของ Phase B ที่ถูกต้อง. (อย่าลงโทษ pipeline จนทิ้งของดีจุดนี้ไปด้วย.)

---

## Q21 — BUG T21: `tools/structure_transcript.py` hangs/fails on nested `claude -p` — root cause + fix direction, before attempting on AI Leading Indicator Session 5/6

**Status:** done (Opus, 2026-07-07) — nested-session contention is a **red herring**; the failure travels with the prompt content (transcript+PDF combo through the `claude -p` CLI path), not with "another session is active." Empty-stdout-exit-1 is a crash/failure-to-emit, not a contention symptom; isolated test #3 reproduced it via a direct pipe. **Do NOT burn another multi-hour standalone retry.** Recommendation = **(b) switch `structure_transcript.py` to a direct Anthropic API call** (removes the entire CLI-subprocess failure surface + gives real error messages instead of swallowed stderr). Scoped, small change (swap ~10 lines). Side effects flagged: no `ANTHROPIC_API_KEY` exists in this project yet (Sonnet must check `ant auth status` / add a key), `anthropic` pkg not installed (`pip3 install anthropic`), metered billing — but Haiku cost is **~$0.15–0.20/session = negligible**, not a blocker. **Yes**, add a standing root-`CLAUDE.md` rule: scripted/programmatic LLM calls in this repo use the API, never `claude -p`. Sonnet executes **T23**.

**Context:** Same blocking bug as T21 in `for-sonnet/tasks.md` (discovered 2026-07-07 during Masterclass ลงทุนศาสตร์ re-transcribe work, not yet root-caused). User now wants to run `/learn-session` for AI Leading Indicator Session 5 and 6 (just reconciled/renumbered today per Q20/T22) — next step is `tools/structure_transcript.py` to build `session_5_structured.md`/`session_6_structured.md` from the new `transcript_5.txt`/`transcript_6.txt`, and this is the exact script that's blocked. User said "consult opus" before attempting it again, rather than risk re-hitting the same multi-hour hang.

**Symptoms observed (reproduced 3 times, 2 distinct failure modes) — full detail already in `for-sonnet/tasks.md` T21, summarized here:**
1. `claude -p --model haiku` subprocess (called from inside `structure_transcript.py`, itself run inside an active/busy Claude Code session doing background Bash/Agent work) → returned almost immediately with exit code 1, empty stdout AND empty stderr.
2. Same setup, different session file → the `claude -p` child process hung for 2h11m at 0% CPU (confirmed via `ps -o etime,pcpu`), had to `kill -9`.
3. Isolated test: piping the exact same real prompt (167,694 chars: transcript + 195-page PDF slide text) directly to `claude -p --model haiku` via `subprocess.run(timeout=120)` → `TimeoutExpired`.
4. Controls that worked fine: (a) 170,000 literal `'x'` chars piped to `claude -p --model haiku` → fast normal reply. (b) the real transcript ALONE (123K chars, no PDF text) piped to `claude -p --model haiku` → also fast normal reply.
5. This same tool worked fine on 2026-07-02 (produced the session structured docs currently on disk) — so it's not fundamentally broken.

**What this rules in/out (from the T21 writeup):**
- Not a raw prompt-size limit (170K synthetic chars worked).
- Not the transcript content alone (worked fine standalone).
- Leading hypothesis: something about invoking a **second/nested `claude -p` CLI session from inside an already-active, busy Claude Code session** — inconsistent failure mode (instant exit-1 vs multi-hour hang) points toward session/resource contention (e.g. a local auth/session lock file, single-instance constraint) rather than a pure content/length problem. Not confirmed.

**Recommended next steps already drafted (not yet acted on), from T21:**
1. Retry standalone, outside any active/busy Claude Code session, to directly test the resource-contention hypothesis.
2. If it still fails standalone: chunk the prompt (structure per ~half the PDF, or drop content-free `[สไลด์ภาพ/กราฟ ไม่มีข้อความ]` slide pages first) to rule out a soft length/complexity ceiling specific to the `claude -p` CLI path.
3. Consider switching `structure_transcript.py` from shelling out to the `claude` CLI binary to calling the Anthropic API directly (`claude-api` skill's Python SDK pattern) — removes the nested-session variable entirely, at the cost of managing an API key instead of reusing the logged-in CLI session.

**What's needed now (this is what's actually being asked of Opus, not just a status copy):**
1. **Root cause judgment call:** given the evidence above, is the nested-session-contention hypothesis (option 1) worth spending time re-testing standalone, or does the evidence already point strongly enough at something else (e.g. CLI-specific prompt/context handling distinct from the raw API, unrelated to "another session is active") that testing standalone would just waste another multi-hour cycle for a result that's already inferable?
2. **Concrete recommendation for right now:** the user has two fresh, real transcripts ready (`transcript_5.txt` 98,623 chars, `transcript_6.txt` 122,649 chars, both plus their PDF slide decks) sitting in `source/AI leading indicator/` waiting on this exact script. Should Sonnet (a) just retry `structure_transcript.py` as-is and see what happens, (b) go straight to option 3 (direct API call instead of CLI subprocess) since it removes the suspected variable entirely, (c) do the chunking workaround, or (d) something else — pick one and say why, don't hedge across all four.
3. If the fix is "call the API directly instead of shelling out to `claude -p`" — is this a small, scoped change to `structure_transcript.py` (swap the subprocess call for an SDK call, keep everything else) or does it have side effects worth flagging (e.g. needing to manage/store an API key that doesn't currently exist in this project's env, cost-tracking differences between CLI-included-usage vs metered API billing)?
4. Anything about this failure pattern that suggests a fix belongs in a different layer (e.g. a general project rule about never shelling out to `claude -p` from within an active session, similar in spirit to the "search before declaring lost" rule just added to root `CLAUDE.md` in Q20) rather than a one-off patch to this one script?

**Why:** user explicitly asked to consult Opus before re-attempting this script, given the multi-hour hang already burned real time/cost once. Wants a decisive recommendation to execute on, not another round of "try it and see."

### ANSWER (Opus, 2026-07-07)

**Verdict บนสุด:** หยุดไล่สมมติฐาน "nested session แย่งทรัพยากร" — มันคือ red herring. หลักฐานชี้ชัดว่าปัญหา **ติดมากับเนื้อ prompt (transcript+PDF) ที่วิ่งผ่าน path `claude -p` CLI** ไม่ใช่เพราะมี session อื่นเปิดอยู่. อย่าเสียเวลาอีกรอบกับ "ลองรัน standalone แล้วดู". **ฟันธง: เปลี่ยน `structure_transcript.py` ไปเรียก Anthropic API ตรงๆ (ตัวเลือก b)** — ตัดตัวแปร CLI-subprocess ทิ้งทั้งก้อน แถมได้ error message จริงแทน stderr เปล่าๆ.

---

#### 1. Root cause — ทำไม "nested contention" ผิดทาง

ผมอ่าน code จริง (`tools/structure_transcript.py` บรรทัด 209-213: `subprocess.run(['claude','-p','--model',model], input=prompt, capture_output=True, text=True, timeout=600)`) แล้วเทียบกับหลักฐาน 3 อย่างที่ contention **อธิบายไม่ได้**:

| หลักฐาน | contention ทำนายว่า | ที่เกิดจริง | สรุป |
|---|---|---|---|
| Mode 1: exit-1, **stdout ว่าง + stderr ว่าง** ทันที | ช้า/ค้าง (แย่งทรัพยากร = รอ ไม่ใช่จบเร็ว) | จบทันที ไม่มี output เลย | ✗ นี่คือ crash/ล้มก่อนพ่น output ไม่ใช่อาการ contention |
| Test #3: pipe prompt จริง (167,694 ตัว) เข้า `claude -p` **ตรงๆ** → TimeoutExpired | ถ้าเป็น contention ควรผ่านเมื่อไม่มี session อื่น | ยัง fail แม้ pipe ตรง | ✗ trigger เดินทางมากับ **เนื้อ prompt** ไม่ใช่ "มี session อื่น" |
| Control: 170K ตัว `'x'` ผ่าน / transcript เปล่า 123K ผ่าน / transcript+PDF ~168K ไม่ผ่าน | contention ไม่สนเนื้อหา (content-agnostic) | fail เฉพาะ combo transcript+PDF | ✗ discriminator อยู่ที่ **เนื้อหาเฉพาะ** ที่วิ่งผ่าน CLI |

"เคยรันได้ 2026-07-02" ไม่ได้แปลว่า contention คือเหตุ — แปลแค่ว่า path `claude -p` CLI มันเปราะ/ไม่ deterministic กับ prompt ใหญ่ผสม (transcript ไทย token เยอะ + PDF fulltext) ใกล้ threshold ภายในบางอย่างของ CLI. **`claude -p` คือ interactive agent harness ไม่ใช่ batch text-transform endpoint** — มันแบก session/MCP/tool bookkeeping ที่เป็นภาระเปล่าๆ และมันกลืน stderr (Mode 1 ให้ **ศูนย์** ข้อมูล debug — นี่อย่างเดียวก็พอเป็นเหตุให้เลิกใช้แล้ว).

---

#### 2. ฟันธงว่าให้ Sonnet ทำอะไรตอนนี้ (transcript_5/6 ที่รออยู่)

**ตัวเลือก (b): เรียก Anthropic API ตรงผ่าน `anthropic` Python SDK.** ไม่ hedge.

| ตัวเลือก | ตัดสิน | เหตุผล |
|---|---|---|
| (a) retry as-is | ❌ | user บอกชัด "ไม่เอา try-and-see" อีกแล้ว; content-dependence พิสูจน์แล้วว่ามันจะ fail ซ้ำกับ combo แบบเดิม |
| (b) direct API | ✅ **เลือกนี้** | ตัด failure surface ทั้งก้อน (stdin pipe, CLI packaging, swallowed stderr); ได้ structured error จริง; token-count ล่วงหน้าได้; API คือเครื่องมือที่ถูกต้องสำหรับ scripted transform |
| (c) chunk prompt | ❌ | เป็นการแก้อาการโดยยังอยู่บน path CLI ที่พังอยู่ดี; เพิ่มความซับซ้อน (ต้อง merge chapter ข้าม chunk + เสี่ยง page-anchor เพี้ยน). ทำเฉพาะ**ถ้า**ย้ายไป API แล้วยังชน context limit — ซึ่งจะไม่ชน (ดูข้อ 3) |

---

#### 3. Scope ของการแก้ + side effects ที่ต้อง flag (ไม่แนะนำมั่ว — ผมเช็คมาแล้ว)

**เป็น change เล็ก isolated** — สลับแค่ block subprocess (บรรทัด 208-218) เป็น SDK call. `build_prompt`, `reanchor_chapters`, การเขียนไฟล์ ทั้งหมด **คงเดิม**.

Side effects (ผม grep เองแล้วทุกจุด):
1. **ไม่มี `ANTHROPIC_API_KEY` ในโปรเจกต์เลย** — เช็คแล้ว: ไม่มีใน env, ไม่มีใน `~/.zshrc`/`~/.zprofile`/`~/.bash_profile`/`~/.profile`, `api/.env` มีแค่ `API_URL`/`COOKIE_PATH`, ไม่มี tool ไหนใน `tools/` ใช้ `anthropic` SDK เลย. → **ก่อนแก้ Sonnet ต้องรัน `ant auth status`**; ถ้ามี OAuth profile active (จาก `claude`/`ant` login) SDK ตัวเปล่า `anthropic.Anthropic()` อาจใช้ได้เลย. ถ้าไม่มี → บอก user ไปสร้าง key ที่ console.anthropic.com แล้ว `export ANTHROPIC_API_KEY`.
2. **`anthropic` pkg ยังไม่ติดตั้ง** (`pip3 show anthropic` = ว่าง) → `pip3 install anthropic`.
3. **Cost model ต่างกัน — แต่ไม่ใช่ blocker.** CLI usage รวมอยู่ใน subscription; API คิดตาม token. **แต่** ราคา Haiku 4.5 = $1/M input, $5/M output (ยืนยันจาก claude-api skill). Prompt ~50-90K input tokens (transcript ไทย token หนัก) + output ~10-15K → **~$0.15-0.20 ต่อ session**. สอง session (5+6) ~$0.30-0.40. **น้อยจนไม่ต้องคิด** — cost ไม่ใช่เหตุให้เลี่ยง API ในงานนี้ (แม้ user จะซีเรียสเรื่อง usage — จำนวนเงินจริงมันเศษสตางค์). บอก user ให้รู้ตัวเลข ไม่ต้องขออนุมัติ.

Model mapping: alias `haiku` → `claude-haiku-4-5`, `sonnet` → `claude-sonnet-4-6` (ยืนยัน model id จาก claude-api skill). Prompt ~90K tokens << 200K context ของ Haiku → **ไม่ชน context limit, ไม่ต้อง chunk**. แนะนำ token-count ก่อนด้วย `client.messages.count_tokens(...)` เพื่อยืนยัน. ใช้ **streaming** (`client.messages.stream(...)` + `.get_final_message()`) กับ `max_tokens=32000` เพราะ output structured ต่อ session อาจเกิน 16K tokens (session_2 structured เดิมยาว) — non-streaming กับ max_tokens สูงเสี่ยง HTTP timeout.

---

#### 4. กฎถาวรที่ต้องเพิ่ม (root CLAUDE.md) — **ใช่**

นี่ไม่ใช่ bug ของ script เดียว มันคือ **design mistake ทั้ง class**: T4 เดิมเลือก `claude -p` เพราะตอนนั้นไม่มี API key และอยากใช้ auth ที่ login ไว้ + ไม่กิน subscription meter. เหตุผลนั้น **สมเหตุสมผลตอนนั้น** แต่พังแล้ว 2 แบบ (crash + hang 2h11m) และ CLI กลืน error จน debug ไม่ได้. → เพิ่มกฎ style เดียวกับ Q20/T22 (`## ก่อนประกาศว่าไฟล์...`):

> **การเรียก LLM แบบ scripted/programmatic ในโปรเจกต์นี้ (ใน tool/สคริปต์ `tools/*.py`) ให้เรียก Anthropic API ตรงผ่าน `anthropic` SDK — อย่า shell out ไป `claude -p`.** `claude -p` คือ interactive agent harness ไม่ใช่ batch endpoint: มันเปราะกับ prompt ใหญ่ผสม, กลืน stderr (debug ไม่ได้), และแบก session/MCP bookkeeping ที่ไม่จำเป็น. API ให้ error จริง, token-count ล่วงหน้าได้, deterministic กว่า. (บทเรียนจาก T21: `structure_transcript.py` crash/ค้าง 2h เพราะ path นี้.)

รายละเอียด effort ต่ำ — ดู T23.

---

## Q22 — Architecture: automate daily YouTube channel summary → Google Sheet, given cloud-routine sandbox has no local cookies and no Sheets connector

**Status:** done (Opus, 2026-07-07) — (1) **Membership = C (ฟันธง)**: routine ทำ public-only, member videos catch-up จาก local session ตอน user เปิด Sonnet ครั้งหน้า. **ไม่ ship cookies (B)** — secret อายุ ~2 สัปดาห์ฝังใน remote config = พังเงียบไม่มีทาง re-auth + blast radius เกินเหตุ. **สำคัญกว่านั้น: RSS สาธารณะไม่โชว์ member videos เลย** → sandbox ไม่มี auth มัน *มองไม่เห็น* member upload ด้วยซ้ำ ต่อให้อยากทำก็ทำไม่ได้ → C ไม่ใช่ตัวเลือก มันคือ*ข้อเท็จจริงเชิงสถาปัตยกรรม*. (2) **Sheets = E (ฟันธง)**: บอก user เชื่อม Google Sheets connector ครั้งเดียว (2 นาที) เขียนลง Sheet เดิมที่สร้างคืนนี้ = single source of truth. **ปฏิเสธ F (Notion fork)** = แตก log สองที่ ผิด norm. ถ้า user ไม่ยอมเชื่อม → fallback = **Gmail notify** (เชื่อมอยู่แล้ว, ไม่ fork database) ไม่ใช่ Notion. (3) **Cadence = daily fixed cron + idempotent no-op**: อ่าน Sheet เป็น state, dedup ด้วย video-ID, catch-up ได้หลายคลิปต่อรอบ, ไม่มีคลิปใหม่ = ออกเงียบ. ไม่ต้อง "ฉลาด" เดาวันโพสต์. (4) **Over-engineering check: ทำ — แต่เฉพาะครึ่งที่ถูกและถูกเงินเท่านั้น** (public-only routine). ครึ่งที่ over-engineer คือ B (ship cookies) ซึ่งตัดทิ้งแล้ว. Member ปล่อยเป็น ad-hoc แบบคืนนี้ = altitude ที่ถูก. Sonnet execute **T24**.

---

### ANSWER (Opus, 2026-07-07)

**Verdict บนสุด:** สร้าง routine ได้ **แต่ลดสเกลเหลือครึ่งที่ทั้งถูกและทน** — cloud ทำ public-only (RSS + yt-dlp ไม่ต้อง auth), member videos ยังเป็นงาน local ad-hoc แบบคืนนี้. เหตุผลที่เด็ดขาด ไม่ใช่แค่ "cookies เปราะ" แต่คือ **public RSS feed ไม่มี member videos อยู่ในนั้นตั้งแต่แรก** — sandbox ที่ไม่มี auth จึงมองไม่เห็น member upload เลย ต่อให้ยอมแบก security risk ก็ยังทำไม่ได้อยู่ดี. เรื่องนี้ทำให้คำถามข้อ 1 (B vs C) จบเองโดยไม่ต้องชั่งน้ำหนัก.

---

#### 1. Membership handling — **C ฟันธง** (B ตกทั้งด้วยเหตุผลเชิงหลักการ *และ* เชิงข้อเท็จจริง)

| หลักฐาน (จาก session คืนนี้) | B (ship cookies) แพ้ตรงไหน |
|---|---|
| **RSS สาธารณะไม่ list member-only videos** | ต่อให้ฝัง cookie สำเร็จ routine ก็ยังต้องเลิกใช้ RSS แล้วไป scrape channel videos-tab แบบ authenticated — เพิ่ม fragile surface อีกชั้น. แต่ถ้ายังใช้ RSS (ซึ่งควร) มันจะ**ไม่เห็น member upload อยู่ดี** → B แก้ปัญหาที่ตัวเองสร้างไม่ครบ |
| cookies หมุน/หมดอายุ ~2 สัปดาห์ (เห็น 2 ครั้งคืนนี้: `yt_cookies.txt` จาก 2026-06-23 ใช้ไม่ได้แล้ว) | secret ฝังใน remote config จะเริ่ม fail เงียบ ~2 สัปดาห์หลังสร้าง — ตอนที่ user ลืมไปแล้วว่ามีมัน. sandbox headless **ไม่มีทาง re-auth เอง** |
| member video ยังต้อง `--remote-components ejs:github` (JS challenge solver โหลดจาก GitHub runtime) | อีก 1 moving part ที่พังได้ใน headless env — GitHub เปลี่ยน/anti-bot อัปเดตเมื่อไหร่ก็จบ |
| blast radius | เก็บ near-full-account YouTube session ไว้บน remote job config แลกกับ bot ที่ต้องการแค่ read member captions = คุ้มค่าความเสี่ยงต่ำมาก |

**"ตัวเลือกที่ 4" ที่ถามหา — มีไหม?** มี แต่ไม่ใช่ automation เต็ม: **local member-catch-up helper** (script ที่ user รันเองตอนเปิด Mac ไม่ใช่ scheduled job) ที่ list member videos ที่โพสต์หลัง last-check-date แล้วสรุปรวดเดียว. นี่คือ **การขัด C ให้ friction ต่ำลง** ไม่ใช่ตัวเลือกใหม่ — เพราะ member content โดยธรรมชาติต้องการ live authenticated browser ซึ่ง**มีแต่ local session เท่านั้น**ที่มี. ปล่อยส่วนนี้ให้ local คือการวางงานถูกชั้น ไม่ใช่การยอมแพ้.

---

#### 2. Sheets destination — **E ฟันธง** (Gmail = fallback ถ้า user ไม่เชื่อม, **ไม่ใช่ F**)

| ตัวเลือก | ตัดสิน | เหตุผล |
|---|---|---|
| **E** — user เชื่อม Google Sheets connector ครั้งเดียว → routine เขียน Sheet เดิม | ✅ **เลือกนี้** | single source of truth = Sheet ที่สร้างคืนนี้ (columns ครบ, มี 2 rows แล้ว). user action = ครั้งเดียว ~2 นาทีที่ `claude.ai/customize/connectors`. รูปแบบ log ดีที่สุด (sort/filter ได้) |
| **F** — route ไป Notion (เชื่อมอยู่แล้ว) | ❌ | fork log เป็น 2 ที่ (2 rows ใน Sheets + ที่เหลือใน Notion) — ผิด norm "อย่าแตก log" ตรงๆ. ประหยัด setup แต่สร้างหนี้ consolidate |
| **Gmail notify** — routine อีเมลสรุปหา user | 🟡 **fallback เท่านั้น** | ถ้า user ไม่อยากเชื่อม connector. Gmail เชื่อมอยู่แล้ว = zero setup, และ**ไม่**สร้าง database คู่แข่ง (อีเมล = notification ไม่ใช่ log คู่แข่ง) จึง fork น้อยกว่า Notion. Sheet คงเป็น manual artifact ที่ user อัปเดตเองเวลาว่าง |
| Drive file + local merge | ❌ | reintroduce local reconciliation step + แยก formatting responsibility = moving parts เพิ่มโดยไม่จำเป็น |

**Flag สำคัญสำหรับ Sonnet:** ต้อง**เช็คก่อน**ว่า claude.ai *มี* Google Sheets connector ให้เพิ่มจริงไหม (Q22 ระบุว่าตอนนี้เชื่อมแค่ Notion/Drive/Calendar/Gmail — ยังไม่รู้ว่า Sheets connector *เพิ่มได้*ไหม). Drive connector ที่เชื่อมอยู่**อ่าน** Sheet ได้แต่ **append row แบบ structured ไม่สวย** → ไม่นับเป็น E. ถ้าไม่มี Sheets connector ให้เพิ่ม → ตก Gmail fallback ทันที ไม่ต้องถาม user ให้เสียเวลา.

---

#### 3. Cron cadence / prompt design — **daily fixed cron + idempotent no-op** (อย่า "ฉลาด")

- **Cadence: daily, เวลาคงที่ (เช่น 08:00 Asia/Bangkok).** อย่าพยายามเดาว่าวันไหนจะมีคลิป (ทำไม่ได้ + เปราะ). empty run = fetch RSS + เทียบ + ออก = ถูกมาก (วินาทีเดียวของ model เล็ก) → ไม่คุ้มที่จะ optimize ให้รันห่าง. daily = ไม่มีวันพลาด + prompt ง่ายสุด. (ถ้า user อยากลด run: every-2-days ก็ได้เพราะ catch-up logic รับหลายคลิปต่อรอบอยู่แล้ว — แต่ default = daily)
- **Idempotency คือหัวใจ (sandbox ไม่มี state ข้ามรอบ):**
  1. อ่าน rows ที่มีอยู่ใน Sheet ก่อน → เก็บ set ของ video-ID/URL ที่ log แล้ว (Sheet = state store แทน local file)
  2. ดึง public RSS `https://www.youtube.com/feeds/videos.xml?channel_id=UCELVTxN2RQM-JnKs6uG_5xg`
  3. หา video ที่**ยังไม่อยู่ใน**set → ถ้าไม่มี **ออกเงียบ ไม่เขียนอะไร ไม่ noise**
  4. ถ้ามี (อาจ**หลายคลิป** — ต้อง loop ทุกอันที่ยังไม่เห็น ไม่ใช่สมมติว่ามีแค่ 1): ดึง caption (`yt-dlp --write-auto-sub --sub-lang th`), clean VTT karaoke inline, สรุปไทย, append row
- **Dedup key = video ID** (ทน URL format ต่าง). อย่าใช้ "วันที่" เป็น key (มิสได้ถ้าโพสต์ 2 คลิปวันเดียว)

---

#### 4. Over-engineering check (norm เดียวกับ Q19.4)

| ส่วนประกอบ | Verdict | เหตุผล |
|---|---|---|
| **Public-only cloud routine** (RSS + zero-auth yt-dlp + dedup-via-Sheet) | 🟢 **ทำ — ผ่าน bar** | maintenance ~ศูนย์ (harness รันเอง ไม่มี VPS/server), failure mode ต่ำ (RSS เสถียร, public caption ไม่ต้อง auth, dedup stateless). ให้ value จริง "ไม่ต้องจำว่าต้องเช็ค". นี่ไม่ใช่ infra ที่ต้องเลี้ยง — มันคือ cron ที่ตั้งแล้วลืมได้ |
| **Ship-cookies member automation (B)** | 🔴 **ไม่ทำ** | นี่คือส่วนที่ over-engineer จริง: fragile secret + JS solver + re-auth ไม่ได้ แลกกับ member subset ที่ RSS มองไม่เห็นอยู่แล้ว. cost/ความเสี่ยงสูง, robustness ต่ำ = ตรงข้าม norm |
| **Sheet + routine โดยรวม vs. ad-hoc แบบคืนนี้** | 🟢 **คุ้ม (เมื่อ scope ลงเหลือ public-only)** | คืนนี้ ad-hoc work ดี — แต่ต้องอาศัย user *จำ*ว่าจะเปิดถาม. routine ตัดภาระความจำสำหรับ public bulk. member (high-value, ต้อง live browser) ยัง ad-hoc = ถูกชั้น. ไม่ใช่ over-engineer เพราะไม่มีอะไรต้อง maintain |
| **บันทึก inline VTT-cleaner เป็น `tools/clean_vtt.py`** | 🟡 **optional, low-pri** | routine (cloud) ใช้ไม่ได้ (sandbox เข้าถึง `tools/` ไม่ได้ → ต้อง inline logic ใน prompt อยู่ดี). script มีค่าแค่กับ **local member-catch-up** path. ทำถ้าจะทำ member-catch-up helper พร้อมกัน ไม่งั้นข้ามได้ |

**สรุปข้อ 4:** ความจริงที่ต้องพูดตรงๆ — routine นี้จะครอบเฉพาะ public content ซึ่งเป็นครึ่งที่ user (BILLIONAIRE-tier member) น่าจะสนใจ*น้อยกว่า* member content. นั่น**ไม่ใช่**เหตุผลให้ไม่ทำ (public bulk ก็ยังคุ้มที่จะ auto-log) แต่**ต้องบอก user ให้รู้ตัว**ว่า automation จะไม่แตะ member videos เลย และ member ยังต้องพึ่ง local ad-hoc — เพื่อไม่ให้ user เข้าใจผิดว่า "ตั้ง routine แล้วครบ".

---


**Goal (user request, tonight 2026-07-07):** User wants a recurring "check this YouTube channel daily, summarize any new video, log it" pipeline — inspired by a video they had Sonnet summarize about building a 24hr AI secretary on a rented VPS. User does NOT want to rent a VPS/manually wire Discord — this project's harness already exposes a built-in cloud scheduling primitive (`/schedule` skill, backed by a `RemoteTrigger` tool that creates recurring "routines" = isolated cloud Claude Code sessions on a cron schedule), and the user correctly wants to use that instead of reinventing the video's approach.

**Channel:** "ลงทุน Diary" (channel ID `UCELVTxN2RQM-JnKs6uG_5xg`). User is a paid Member (highest tier "BILLIONAIRE") of this channel, so some videos are public and some are members-only.

**Already done tonight, working:**
- Manually summarized 2 videos from this channel (one public, one members-only) by hand this session, in Thai, and confirmed it works well.
- Created a Google Sheet ("YouTube สรุปรายวัน - ลงทุน Diary", spreadsheetId `1vhbxCtukyLrqhLId3A0SsgIZOAA_LmsSLmba7d31ziY`, sheet tab "สรุปวิดีโอ") via the `google-sheets-mcp` MCP tools available in *this* (local) Claude Code session, and appended both summaries as rows (columns: วันที่ตรวจ, ช่อง, ชื่อคลิป, ลิงก์, ความยาว, สรุป).
- Confirmed the technical recipe for pulling a transcript from this channel's videos:
  - Public video: plain `yt-dlp --write-auto-sub --write-sub --sub-lang th --sub-format vtt` works with zero auth.
  - Members-only video: requires `yt-dlp --cookies-from-browser chrome --js-runtimes node --remote-components ejs:github ...` — i.e. (a) a real, currently-logged-in-with-active-membership Chrome browser session on this Mac to pull cookies from, AND (b) a JS challenge-solver component (downloaded from GitHub via `--remote-components ejs:github`) to get past YouTube's anti-bot check. A pre-exported static cookie file (`yt_cookies.txt`, originally exported 2026-06-23) turned out to be already invalid tonight ("cookies are no longer valid... rotated as a security measure") and had to be freshly re-exported via `--cookies-from-browser chrome` at the moment of use — this is the second time in recent project history a static cookie export went stale fast (see `feedback_download_audio` / `feedback_facebook_group_download` memory precedent for the same pattern with other platforms).
  - Then dedupe/clean the karaoke-style auto-caption VTT into plain text (Sonnet wrote a small inline Python cleaner tonight, not yet saved as a reusable tool).

**The blocker — invoked `/schedule` skill, it surfaced two hard constraints not obvious before starting:**
1. **Cloud routines are fully isolated sandboxes** — per the skill's own instructions: "they cannot access local files, local services, or local environment variables." This means a routine **cannot** use this Mac's live Chrome session/cookies, and cannot read `tools/.env` or any other local secret. Whatever it needs, it either (a) doesn't need auth for (public videos, RSS feed detection — RSS needs no API key), or (b) needs the credential shipped into the routine's config at creation time (baked into the prompt or an env var attached to the job), which means **a static, rotating-soon copy of the user's full YouTube account session cookies would have to be committed into a cloud-hosted routine's config** for membership access to work at all.
2. **Google Sheets is not among the claude.ai MCP connectors currently available to attach to a routine** — the `/schedule` skill enumerated only Notion, Google Drive, Google Calendar, and Gmail as connected connectors eligible for routine `mcp_connections`. (Note: this is a *different* Sheets access path than the `google-sheets-mcp` tool available in the interactive local session right now — that one is apparently connected some other way, not visible/available to the isolated cloud routine environment.) So even if auth weren't an issue, the routine could not write directly into the Sheet already created tonight without either connecting a dedicated Sheets connector first (user action, one-time, at `claude.ai/customize/connectors`) or writing somewhere else (Notion database, a Drive file, or an email via Gmail) and having a human/local step reconcile it into the Sheet later.

**Options weighed so far (Sonnet, not yet decided):**
| # | Option | Note |
|---|---|---|
| A | YouTube Data API v3 key for new-video detection | Solves nothing re: membership content (captions still need cookies regardless of using an API for the "is there a new video" check) — RSS already does the detection part for free without a key, so an API key adds cost/complexity for zero marginal benefit on the actual blocker. |
| B | Ship the user's live browser cookies into the cloud routine config | Works technically (routine's prompt/env could embed a cookie string) but (a) cookies already proven to rotate/expire within ~2 weeks in this exact account's history, so a static copy baked into a routine would silently start failing soon after creation with no easy re-auth path from inside a headless cloud sandbox: b) it means storing a near-full-account YouTube session credential in a remote job config — meaningfully larger blast radius than a local file, for a bot that only needs read access to member captions. |
| C | Cloud routine automates PUBLIC videos only (no cookie needed at all — this is the actual bulk of the channel's output); user manually pings Sonnet (as done tonight) for member-only videos, which inherently require a live, freshly-authenticated local browser session anyway | Sidesteps the cookie-rotation and blast-radius problem entirely, at the cost of "not fully automatic" for the members-only subset. |
| D | Local scheduling instead (macOS `launchd`/cron running a script with full access to local cookies + `google-sheets-mcp`) | Has access to everything needed, but requires the Mac to be on/awake to fire — which is the exact problem the source video (and this whole feature request) was about *avoiding*. Reintroducing that dependency undercuts the stated goal. |
| E | Sheets destination: user connects a dedicated Google Sheets connector to their claude.ai account first (one-time action at the connectors page), then the routine can write directly into the existing Sheet | Cleanest long-term fix for the Sheets-connector gap specifically, but requires a user action outside this session before automation can start. |
| F | Sheets destination (no new connector needed): route the routine's output to Notion instead (already connected) as a database, and treat the Sheet as this session's one-off/manual artifact | Works today with zero new setup, but forks the "log" into two different places (tonight's 2 rows in Sheets, everything after in Notion) unless someone consolidates later. |

**What's actually being asked of Opus:**
1. **Membership handling:** commit to option B or C (don't hedge) — is shipping rotating session cookies into a cloud routine config an acceptable trade for this user's use case, or is C (public-only automation + manual membership catch-up) simply the correct call given the cookie-rotation history already observed twice tonight? Is there a fourth option Sonnet is missing (e.g., some other mechanism to keep member-content access working without embedding a fragile secret in a remote config)?
2. **Sheets destination:** commit to E, F, or something else — should the user be told to go connect a Sheets connector before this is worth building (E), should Sonnet just point the routine at Notion instead and reconcile the fork later (F), or is there a reason to prefer a different destination entirely (e.g., a Drive file the local session periodically pulls into the Sheet, splitting responsibility cleanly between "cloud does capture" and "local does formatting/merge")?
3. **Cron cadence / prompt content:** given the channel posts roughly every 2-3 days per the videos seen tonight (dated 09/11/16/18/23/25 June, 03/04 July) rather than strictly daily, should the routine's prompt be written to just no-op cleanly on days with nothing new (cheap, simple) rather than trying to be "smart" about only running on days something's expected?
4. **Anything about this whole automation idea that's over-engineering for a solo hobbyist user** (mirroring the norm already established in Q18/Q19 discussions about this project — don't build infrastructure that isn't worth its maintenance cost for a one-person use case) — e.g. is a Sheet + routine even worth it here vs. Sonnet just being asked ad-hoc like tonight whenever the user wants a summary?

**Why:** user explicitly asked to consult Opus rather than have Sonnet guess at an architecture with real security (cookie exposure) and reliability (Sheets connector gap, cookie rotation) trade-offs baked in, following the same pattern already used successfully tonight for Q20/Q21.

---

## Q23 — Review a Codex-authored YouTube-digest architecture spec the user found, and reconcile it against the just-decided T24 plan

**Status:** done (Opus, 2026-07-08) — **Verdict: spec is genuinely well-engineered แต่ wrong-fit สำหรับ user คนนี้/งานนี้** — วิศวกรรมเกรด A (security model, adapter abstraction, state machine, idempotency ถูกหมด) แต่ผิดฐาน 3 ชั้น: (i) **Windows-only + local machine = dispositive** — user อยู่ Mac และคืนนี้เพิ่งเลือก cloud routine (T24) *เพื่อไม่ต้องเปิดเครื่องทิ้ง* โดยเฉพาะ; spec §22 ยอมรับเองว่า "เครื่องปิด = ส่งไม่ได้" → ขัดเป้าหมายคืนนี้ตรงๆ. (ii) **Gemini แทน Claude** = artifact ของ Codex default ล้วนๆ ไม่มีเหตุผลจริง (Claude ทำงานนี้ได้เอง demo 2 ครั้งคืนนี้ + เพิ่งตั้ง API path ใน T23). (iii) **สเกลเกิน 1 order** — 10-phase production app (SQLite+migrations, 12-state machine, MCP layer, full test suite) สำหรับ "บอกทีว่า ลงทุน Diary โพสต์อะไรใหม่". **Reconciliation = (d) cherry-pick ฟันธง** — เก็บ T24 (cloud, เบา) เป็นตัวหลัก, ขโมย 4 ไอเดียดี (prompt-injection framing, video-ID dedup, watch-recommendation+relevance score, formula-injection prefix) ทิ้งสถาปัตยกรรมที่เหลือ. **(b) build-this-instead ตก** เพราะผิด OS + ขัด cloud goal; **(c) run-both ตก** = fork log + double maintenance ผิด norm เดิม (Q18/Q22). **Windows question (ข้อ 3) = ใช่ ถามก่อน แต่ถาม *เจตนา* ไม่ใช่แค่ "มี Windows ไหม"** (always-on tool จริง? / เรียน TypeScript+Codex? / หรือแค่ draft ซ้ำที่ยอมพับเข้า T24?) — คำตอบ gate ทุกอย่าง. **ข้อ 4 = ใช่ retrofit T24 ทันทีไม่ว่าผลเป็นไง**: prompt-injection defense (title/desc/transcript = untrusted data) + spreadsheet formula-injection prefix (`=+-@`) เป็น gap จริงที่ T24 ยังไม่มี. Sonnet executes **T25**.

**Context:** Same night as Q22/T24 (2026-07-07/08). While Sonnet was mid-flight on other work, the user surfaced two files they'd received via AirDrop (quarantine flag confirmed the transfer path) into `/Users/alonsi/Downloads/youtube-digest-codex-spec/`:
- `AGENTS.md` (3151 bytes) — a short "read this first" pointer file for OpenAI Codex.
- `YOUTUBE_DIGEST_MCP_ARCHITECTURE.md` (37,850 bytes) — the full architecture spec these Codex instructions point to.

The user's own words: *"สองไฟล์นี้ คือผมวางแผนจะให้ ai สรุป yt ให้ผมทุกเช้า อยากให้ opus ช่วยวิจารณ์ให้หน่อย ว่าเป็นอย่างไรบ้าง มีข้อเสนอแนะอะไร"* — i.e. this is the user's own separate plan (probably drafted with/by Codex before or in parallel with tonight's Q22/T24 work in this Claude Code session) for the exact same underlying goal ("summarize YouTube for me every morning"), and the user wants Opus's critique + recommendations on it — most importantly, **how it should be reconciled with the T24 plan Opus itself just committed to** (public-only cloud routine → Google Sheet, channel "ลงทุน Diary" `UCELVTxN2RQM-JnKs6uG_5xg`, existing Sheet `1vhbxCtukyLrqhLId3A0SsgIZOAA_LmsSLmba7d31ziY`).

**Read the full spec yourself** at `/Users/alonsi/Downloads/youtube-digest-codex-spec/YOUTUBE_DIGEST_MCP_ARCHITECTURE.md` (32 numbered sections, very detailed) — summarizing the shape here so you know what you're looking at, but read the real file for exact wording before critiquing:

- **What it proposes:** a full local-first TypeScript/Node.js 22 application (`youtube-digest-mcp`), NOT a cloud routine. Watches 5–10 YouTube channels via **YouTube Data API v3** (`channels.list` + `playlistItems.list`, explicitly avoiding `search.list` for quota reasons), processes ≤10 new videos/run, pulls public transcripts through a pluggable `TranscriptProvider` interface (explicitly: never bypass login/membership/age/region restrictions, never download video/audio), summarizes in Thai via **Gemini API** (`gemini-3.5-flash` default) with a Zod-validated structured-output schema (one-line summary, executive summary, key points with timestamps, facts, actionable ideas, topics, relevance/confidence scores, watch recommendation), writes to a **Google Sheet** via 3 worksheets (`Channels` config, `Video Summaries`, `Run Logs`), sends one **Gmail** HTML digest per run to a single allowlisted recipient, persists all state in **SQLite** (channels/videos/transcripts/summaries/runs/deliveries tables, explicit state machine with 12 states, idempotency via video-ID keys), runs on a **Windows Task Scheduler** trigger at 06:30 Asia/Bangkok daily, and separately exposes an **MCP stdio server** (read-only tools + a few gated write tools like `digest_run` defaulting to `dryRun=true`) so Codex can inspect/troubleshoot the same underlying service layer interactively — with an explicit architectural principle that "MCP is not the scheduler," both entry points share one service layer.
- **Security posture is unusually thorough for a personal project:** treats all video text (title/description/transcript/sheet notes) as untrusted/prompt-injection surface with an explicit system-prompt instruction never to follow embedded instructions; HTML-escapes email content; prefixes spreadsheet cells starting with `=`/`+`/`-`/`@` to prevent formula injection; least-privilege OAuth scopes (`spreadsheets` + `gmail.send` only, no Drive-wide/Gmail-read/YouTube-account access); hardcoded allowlisted email recipient that no MCP tool argument can override; no arbitrary SQL/shell/filesystem tools exposed via MCP; credentials/DB/logs gitignored.
- **Explicit non-goals:** web dashboard, mobile app, cloud deployment, multi-user, video/audio download, comments analysis, Shorts-specific handling, vector DB/embeddings, more than one concurrent pipeline run.
- **Test discipline:** unit + integration tests with mocked external APIs required for every behavior change, contract fixtures for every external API response shape, no live API calls in CI.
- **10-phase implementation order** (scaffold → persistence → Google auth → YouTube discovery → transcript provider → Gemini → reporting → orchestrator/CLI → MCP → Windows automation/hardening), each phase gated on tests+typecheck+lint+"summarize what changed"+"state remaining risks," explicitly forbidding claiming live API success without real credentials tested.

**Things Sonnet already noticed that seem worth your judgment (not exhaustive — form your own view from the actual file):**

1. **Windows Task Scheduler + "local Windows computer" vs. this user's actual machine is a Mac.** Everything in this session so far has run on macOS (`/Users/alonsi/Desktop/studio`, this is a MacBook/Mac). The spec is unambiguously Windows-only (PowerShell registration scripts, Task Scheduler, `C:\\absolute\\path\\...` in the Codex MCP config example). Sonnet does not know whether the user has a separate physical/virtual Windows machine in mind for this, or whether this spec was drafted generically/wrongly without knowing the target OS. If there's no real Windows box, this whole plan can't run as written on this user's actual hardware — worth flagging as the first, most basic compatibility question before any other critique matters.
2. **This reintroduces exactly the dependency the whole Q22/T24 conversation was trying to avoid.** The original ask tonight ("ผมอยากให้คุณไปสรุป yt ให้ผมทุกวัน" → the video that inspired this was literally about NOT needing to keep a local machine on) led directly to choosing a cloud routine (T24) specifically so nothing has to stay powered on. This Codex spec is the opposite: a local app requiring **the Windows machine to be powered on or wake successfully** every morning (the spec's own §22 admits this: "If the machine is fully shut down, delivery waits until the next available run"). Worth a direct opinion on whether the user has silently re-adopted the "keep a machine on" tradeoff, or drifted into it without noticing the tension with tonight's earlier reasoning.
3. **Scale of engineering vs. the actual use case.** This is a 10-phase production-grade app (SQLite schema + migrations, explicit 12-state state machine, retry/backoff/timeout policy per operation type, structured JSON logging with 30-day rotation, full test suite with mocked fixtures for every external API, an MCP server with its own resources/prompts/tool-contract layer separate from the CLI) for what is, per tonight's actual use case, "tell me every morning if ลงทุน Diary (and maybe a few more channels) posted something new." This project's established house norm (see Q18/Q19.4 in this same file — over-engineering verdicts for a solo hobbyist's course-learning pipeline) leans hard against building infrastructure whose maintenance cost exceeds what a one-person hobby project needs. Is this spec over-engineered for that norm, appropriately rigorous because it's meant to be a durable personal tool the user actually maintains long-term, or does it depend entirely on unstated intent (e.g. is the user actually trying to learn TypeScript/Codex workflows here, in which case the "over-engineering" framing doesn't apply the same way)?
4. **Gemini API instead of Claude.** The user's entire existing toolkit in this project (this Claude Code session, `tools/structure_transcript.py` after tonight's T23 fix, the `claude-api` skill) is Anthropic-centric. This spec requires a brand-new Gemini API key/billing relationship for a task Claude could just as easily do (as demonstrated twice tonight, doing exactly this kind of Thai video summarization by hand). Is there a real reason to prefer Gemini here (cost? a specific structured-output feature? something in Codex's own defaults?) or is this just an artifact of whoever/whatever drafted the spec defaulting to Gemini without considering the user's actual existing stack?
5. **Transcript strategy overlaps with what Sonnet already learned hands-on tonight.** The spec's `PublicYouTubeTranscriptProvider` (a third-party library reading YouTube's public watch-page captions) is functionally similar to what Sonnet did manually via `yt-dlp --write-auto-sub` tonight — same public-only constraint, same "skip if no transcript" fallback. Sonnet does NOT think this changes any of Q22's committed decisions about membership content (still requires a live authenticated browser session regardless of which app does it) — but flag if you see it differently.
6. **Genuinely good ideas in this spec worth stealing regardless of the verdict on the whole architecture** — Sonnet's own read, for you to confirm/reject: (a) the prompt-injection framing (treating transcript/title/description as untrusted data, never let the model call tools based on embedded instructions) is a real gap in tonight's T24 plan, which never considered a hostile video title/description trying to manipulate the summarizer; (b) `Video ID` as the dedup key (not date) is more correct than T24's looser wording; (c) explicit "watch recommendation" (MUST_WATCH / SKIM / SUMMARY_ONLY) + relevance/confidence scores would make a daily digest much more skimmable than tonight's plain-prose summaries; (d) spreadsheet formula-injection prevention (prefixing cells starting with `=`/`+`/`-`/`@`) is a real, currently-unaddressed risk in T24's Sheet-writing plan given video titles are attacker-controlled text written into cells.

**What's actually being asked of Opus:**
1. **Overall verdict on the spec itself** — is this a well-designed architecture for what it's trying to do, over-engineered, or right-sized, and why (ground this in the actual file, not just Sonnet's framing above)?
2. **Reconciliation with T24:** should the user (a) abandon this Codex/Windows spec entirely and stick with T24's cloud routine, (b) abandon T24 and build this instead (if they do have/plan a Windows box), (c) run both for different purposes (e.g. this handles a broader personal news/interest digest across many channels the user actively maintains as a real tool, while T24 stays a narrow "ลงทุน Diary" specific add-on), or (d) cherry-pick specific ideas from this spec (see item 6 above) into T24's much lighter design rather than adopt the whole architecture? Commit to one, don't hedge across all four.
3. **The Windows question specifically** — should Sonnet ask the user directly whether they have a Windows machine in mind before saying anything else about this spec, since it may make most of the rest of the critique moot?
4. **Anything in the security/prompt-injection framing (item 6a, spreadsheet formula injection 6d) that should retroactively be added to T24** regardless of what happens to this Codex spec, since prompt-injection-via-video-content and formula-injection-via-video-title are real risks T24 currently doesn't address at all.

Write your answer into `for-opus/questions.md` under Q23, and if it requires Sonnet to act (e.g., ask the user about the Windows machine, retrofit T24's routine prompt with injection/formula-injection defenses before building it, or something else), append a task to `for-sonnet/tasks.md` (next number after T24, i.e. T25) following the existing conventions.

**Why:** user explicitly asked for Opus's critique of this specific document, not Sonnet's — and it has direct bearing on whether T24 (which hasn't been built yet — Sonnet was about to start T24 when this surfaced) should proceed as designed, get modified, or get shelved in favor of this alternative.

---

## Q24 — Same Codex spec, now macOS-adapted — does fixing the OS mismatch change the Q23 verdict?

**Status:** done (Opus, 2026-07-08) — **Verdict unchanged; the OS swap fixed the *shallow* half of objection (i) only.** "Wrong OS" was never the real problem — the real problem is **always-on-local-machine vs. the cloud-routine goal**, and §22.5 admits verbatim it's untouched ("Mac must be awake… cannot run while fully shut down… keep the Mac charged/connected to power"). Objections (ii) Gemini-not-Claude and (iii) 10-phase/SQLite/MCP overkill are **byte-identical → fully standing**. So 2.5 of 3 objections survive. **BUT** — the revision does change one thing: the user is now iterating seriously (2 rounds, 2nd responding to real feedback), which converts the local-machine issue from a *defect* into a **fork the user must choose explicitly**: either (A) tonight's narrow ask → **T24 cloud stays primary, cherry-pick 4 ideas, shelve the rest** (= Q23, unchanged), or (B) the user genuinely wants a durable, general-purpose, multi-channel personal digest tool → then a LaunchAgent is a *legitimate, even correct* architecture (the Q22 "cloud avoids a machine-on" framing was scoped to the single-channel add-on, not to whatever this broader tool wants to be), and the right build is a **descoped spec: keep LaunchAgent, swap Gemini→Claude API (reuse the T23 `structure_transcript.py` pattern), drop YouTube-Data-API-v3+SQLite+MCP-server for a single-file script** — a real "download-sized" complementary tool, NOT the full 10-phase app and NOT a replacement for T24. **Which of A/B is live is the user's call, not ours to guess** — so the action is: Sonnet asks the one gating intent question, then proceeds. T25 already had to ask the Windows-intent question for Q23; Q24 just sharpens that same question (drop "Windows"; it's now "narrow-ask-done vs. durable-always-on-local-tool") and adds the concrete descoped-spec option as the answer to give if the user picks B. **No new task** — folded into T25's existing gating question.

**Context:** Direct follow-on to Q23 (same night, 2026-07-08). After your Q23 answer was written (verdict: spec is well-engineered but wrong-fit — Windows/local-machine mismatch was one of three dispositive objections, alongside Gemini-vs-Claude and 10-phase scale being overkill for the actual use case), the user sent Sonnet a **new zip**: `/Users/alonsi/Downloads/youtube-digest-codex-spec-macos.zip`, saying "นี่อันใหม่ ให้ opus วิเคราะห์หน่อย" (this is the new one, have Opus analyze it).

Sonnet extracted it and diffed it against the original spec Q23 already reviewed. **The only substantive changes are OS-related:**
- §1 "runs on the user's personal Windows computer" → "runs on the user's personal Mac."
- §2 fixed-decisions table: `Scheduler: Windows Task Scheduler` → `Scheduler: macOS launchd / LaunchAgent`.
- §5 gained a new "macOS local prerequisites" subsection (Homebrew/Node/corepack/pnpm setup commands, a note that `launchd` doesn't inherit a shell `PATH` so scripts need absolute paths / an explicit safe `PATH`).
- §6 repo layout: `scripts/register-windows-task.ps1` / `unregister-windows-task.ps1` → `scripts/install-launchagent.sh` / `uninstall-launchagent.sh` / `run-digest.sh` / a `.plist.example`.
- §22 fully rewritten from "Windows scheduling" to "macOS scheduling": LaunchAgent label `com.chatgptprivate.youtube-digest`, install path `~/Library/LaunchAgents/...`, `StartCalendarInterval` plist example, `launchctl load/unload`, an install script that resolves the absolute `pnpm` path since `launchd` won't have it on `PATH`.
- §22.5 "macOS limitations to document" replaces the old Windows equivalent — **critically, it still says the same underlying thing**: *"The Mac must be awake or able to wake at the scheduled time... A LaunchAgent cannot run while the Mac is fully shut down... For laptops, advise keeping the Mac charged or connected to power if reliable morning delivery matters."*
- §26 acceptance criterion #11 and §30 known-limitations wording swapped "Windows task" → "macOS task" / "LaunchAgent" accordingly.
- **Every other section is byte-identical** to what you already reviewed for Q23: still TypeScript/Node 22/pnpm, still YouTube Data API v3 discovery, still **Gemini API** (`gemini-3.5-flash`) for summarization, still the full SQLite 6-table schema + 12-state machine, still the same MCP stdio server with the same tool contracts, still the same 10-phase implementation order, still the same security model (prompt-injection framing, formula-injection prefixing, least-privilege OAuth) — none of that changed at all.

**The question this raises, which is exactly what's being asked of you now:** the macOS swap fixes objection (i) from your Q23 verdict in the narrow sense — it's no longer the wrong OS for this user's actual machine. But it does **not** fix what was arguably the deeper part of that same objection: **this still requires a physical machine to be powered on/awake at the scheduled time**, which is precisely the constraint tonight's earlier decision (T24 — a cloud routine, not a local scheduled process) was chosen specifically to avoid. The spec's own §22.5 admits this plainly for laptops. Your two other Q23 objections (Gemini-vs-Claude as an unmotivated Codex default; 10-phase/SQLite/MCP-server engineering scale being roughly an order of magnitude more than "tell me when ลงทุน Diary posts something new" actually requires) are completely untouched by this revision.

**What's actually being asked of you:**
1. Does swapping Windows→macOS meaningfully change your Q23 reconciliation verdict, or was "wrong OS" always the *shallow* symptom of a *deeper* objection (always-on-local-machine vs. the cloud-routine goal) that this revision doesn't actually address? Be explicit about which of these two framings is correct — don't let "OS fixed" read as "objection resolved" if the real objection was one level down.
2. Given the user is now iterating on this spec seriously (two rounds already, second one clearly responding to real feedback), is there a real decision point disguised in this pattern — e.g. does the user actually want a durable, general-purpose, always-on personal digest tool as a real side project (in which case a local LaunchAgent is a perfectly reasonable, even correct, architecture choice — the "cloud avoids needing a machine on" framing from Q22 was scoped to a narrow single-channel add-on, not necessarily to whatever this broader tool is meant to become), versus still just trying to solve tonight's original narrow ask and drifting into over-scoping via a spec that was hard to hand-edit down? If the former, your Q23 "wrong-fit" framing may need updating; if the latter, restate it more sharply now that the superficial objection is gone and only the substantive ones remain.
3. Restate your reconciliation call for *this* version specifically: same as Q23 (T24 stays primary, cherry-pick 4 ideas, shelve the rest), or does anything change now that OS is no longer an excuse to dismiss it quickly?
4. Is there a version of this Codex spec that Sonnet should recommend the user descope it *to* — e.g. "keep everything except: swap Gemini→Claude API (reuse the T23 pattern already built tonight for `structure_transcript.py`), swap YouTube-Data-API-v3+SQLite+MCP-server for a much smaller single-file script, keep the LaunchAgent scheduling since the user is apparently fine running things locally when they want a fuller tool" — i.e. is there a legitimate "download-sized" version of this spec worth actually building as a *separate, complementary* tool to T24, or is that still solving a problem nobody asked for?

**Why:** user explicitly asked for a fresh Opus read of this specific updated file, following the same pattern as Q23 — this is not a request to redo Q23 from scratch, it's a request to judge whether this specific revision changes anything about that verdict.

---

### ANSWER (Opus, 2026-07-08)

Spot-checked the real file (`/tmp/yt-digest-macos-spec/…§22.5`) — Sonnet's diff is exact. §22.5 verbatim: "The Mac must be awake… A LaunchAgent cannot run while the Mac is fully shut down… For laptops, advise keeping the Mac charged or connected to power if reliable morning delivery matters." Every non-scheduling section is unchanged.

**1. Does Windows→macOS change the verdict? No — "wrong OS" was the shallow symptom; "always-on local machine" is the deeper objection, and it is untouched.**
Objection (i) in Q23 was really two claims stacked: (i-a) *this literally can't run on the user's actual machine* (wrong OS), and (i-b) *this needs a physical box powered on/awake every morning, which is the exact dependency tonight's cloud decision (T24) was chosen to escape.* The macOS swap resolves (i-a) completely and (i-b) **not at all** — §22.5 concedes (i-b) in the spec's own words. The tension I flagged in Q23 ("has the user silently re-adopted the keep-a-machine-on tradeoff?") is 100% intact. Do not let "OS fixed" read as "objection (i) resolved" — only its cosmetic half was.

And objections **(ii) Gemini-instead-of-Claude** and **(iii) 10-phase / SQLite+migrations / 12-state machine / MCP-server scale ≈ one order of magnitude past the actual use case** are byte-identical to what I reviewed for Q23. Nothing in this revision touches them. So the substantive core of Q23 stands entirely.

**2. Is there a real decision point disguised here? Yes — and it's the whole point of the revision.**
Two serious iterations, the second responding to real feedback, is a signal that this may no longer be "tonight's narrow ask, over-scoped." There's a genuine fork, and it turns on **user intent that we do not have and must not guess**:
- **Fork A — still the narrow ask** ("tell me when ลงทุน Diary posts"): then everything in Q23 holds unchanged. A LaunchAgent that needs the Mac awake at 06:30 is strictly worse than T24's cloud routine for this, and the 10-phase app is overkill. → T24 primary, cherry-pick, shelve.
- **Fork B — the user actually wants a durable, general-purpose, multi-channel morning digest as a real side project they'll maintain:** then my Q23 "wrong-fit" framing needs *narrowing*. The Q22 premise ("cloud avoids needing a machine on") was scoped to a single-channel add-on; it does **not** automatically bind a broader tool. For a tool the user runs deliberately and maintains, **a local LaunchAgent is a reasonable, even correct, choice** — and the always-on constraint (i-b) becomes an accepted tradeoff, not a defect. In Fork B, only objections (ii) and (iii) survive, and both are *fixable by descoping* rather than fatal.

We can't tell A from B from the files. The disciplined move is to ask, not assume.

**3. Reconciliation call for THIS version.**
- **Default / Fork A: unchanged from Q23** — T24 (cloud, light) stays primary; cherry-pick the 4 good ideas (prompt-injection framing, video-ID dedup, watch-recommendation + relevance score, formula-injection prefix); shelve the full architecture.
- **Fork B: reconciliation shifts to "build a descoped sibling"** (see #4). Still not the full 10-phase app; still not a replacement for T24 unless the user explicitly wants to retire the cloud routine (I'd advise against — keep the near-zero-maintenance cloud job for the one channel that matters).
The OS fix does **not**, on its own, upgrade the spec from "shelve" to "build." Only a Fork-B intent answer does that.

**4. Is there a legitimate "download-sized" version worth building? Yes — but only under Fork B, and it's a different tool from the full spec.**
If the user picks B, the right recommendation is **not** "build the spec as written." It's a right-sized rewrite that keeps the spec's genuinely good bones and drops the enterprise scaffolding:
- **Keep:** LaunchAgent scheduling (user is fine running locally when they want a fuller tool); the security posture (prompt-injection framing, formula-injection prefix, least-privilege OAuth, allowlisted recipient); Google Sheet + Gmail sinks; video-ID dedup; watch-recommendation + relevance score.
- **Swap Gemini → Claude API** — reuse the exact pattern T23 just built for `structure_transcript.py` tonight. No new billing relationship, stays in the user's Anthropic-centric stack. (This directly answers Q23 objection ii.)
- **Drop:** the 6-table SQLite schema + migrations + 12-state machine + separate MCP stdio server + 10-phase gated rollout. For "≤10 new videos across a handful of channels once a morning," a **single-file TypeScript (or even Python) script** with a tiny JSON/flat-file "seen video IDs" store is sufficient. State machine and MCP layer are solving problems this workload doesn't have. (This answers objection iii.)
That descoped tool is a **legitimate, complementary** build — a broader local digest for many channels — sitting alongside T24's narrow, always-available cloud job for the one channel the user cares most about. Building the *full* spec, though, is still solving a problem nobody stated.

**Bottom line:** verdict unchanged; the revision fixed a cosmetic objection and left both substantive ones standing, but it also surfaced a real A/B intent fork that only the user can resolve. Sonnet's job is to ask that one question (folded into T25) and hand the user the two concrete paths — not to build either yet.

---

## Q25 — BCH stock research: skip transcription entirely, upload video/audio straight into NotebookLM and let Minnie query it directly — good trade, given this project's own documented NotebookLM contamination failure?

**Status:** done (Opus, 2026-07-10) — **ไม่ใช่ all-or-nothing. Tier ตามน้ำหนักหลักฐาน:** สัมภาษณ์ CEO (~10-14 คลิป = ที่ "คำสัญญา" อยู่ และไม่มี primary source อื่น) → **ถอดเสียงก่อน non-negotiable** (VAD+large-v3 → `.txt` → อัป `.txt` นั้นเข้า NotebookLM แทน video → ได้ทั้ง source คุณภาพคุมได้ + ground truth ให้ Fact-checker grep จากการถอดครั้งเดียว); Oppday รายไตรมาส (~17-21 คลิป = ตัวเลขล้วน ซึ่ง**มีใน filing/บทวิเคราะห์อยู่แล้ว**) → อัป **native เข้า NotebookLM ได้เลย ไม่ต้องถอด** แต่ห้ามเชื่อตัวเลขจาก NotebookLM-native ตรงๆ ต้อง cross-check กับ filing. ประหยัดเวลา ~55-60% (ถอด ~13 ไม่ใช่ 31 + ข้าม structure ทุกไฟล์) โดยไม่รื้อ contamination-guard ตรงจุดที่ use case ทนพลาดไม่ได้. Native audio เปลี่ยนสมการ 2 ทิศสวนกัน: **ดีขึ้น**เรื่อง attribution (per-source citation ถ้าแต่ละคลิปเป็น source แยกที่ตั้งชื่อด้วยวันที่) แต่**แย่ลง**เรื่อง fidelity (NotebookLM ถอดไทยเองด้วย engine ที่คุมไม่ได้ ไม่มี VAD/initial_prompt/hallucination-gate ที่โปรเจกต์นี้สร้างมาเพราะ Whisper การันเสียงชุดนี้พัง — และไม่เหลือ `.txt` ให้ grep). Sonnet executes **T26**.

### ANSWER (Opus, 2026-07-10)

**หมายเหตุก่อน:** BCH = Bangkok Chain Hospital = เครือ**เกษมราษฎร์** (Kasemrad/World Medical/Karunvej) — **ไม่ใช่** จุฬารัตน์ (นั่นคือ CHG คนละบริษัท). ตามที่ context เตือน อย่าเผลอสลับซ้ำ.

**กรอบที่ต้องยึด:** คำถามนี้ไม่ใช่ "ถอด vs. ไม่ถอด" แบบ binary. มันคือ "คลิปไหนแบกหลักฐานอะไร และหลักฐานนั้นมี primary source สำรองไหม" — เพราะ 31 คลิปไม่ได้มีน้ำหนัก evidentiary เท่ากัน:
- **สัมภาษณ์ CEO/ผู้ก่อตั้ง** (Money Chat, MONEY TALK) = ที่ **"คำสัญญาเชิงคุณภาพ"** อยู่ ("จะเปิด รพ. อีก X แห่ง", "margin จะฟื้นครึ่งปีหลัง", "คนไข้จีน/ต่างชาติจะกลับ"). พวกนี้ **ไม่มีที่ไหนบันทึกไว้เป็นทางการ** — ถ้าคำพูดเพี้ยน ก็ไม่มีอะไร cross-check. นี่คือ ground truth ของ workflow promise-tracking ทั้งอัน.
- **Oppday รายไตรมาส** = **ตัวเลขล้วน** (รายได้ margin จำนวนเตียง occupancy) ซึ่งทุกตัว**มีใน MD&A / 56-1 / บทวิเคราะห์อยู่แล้ว**. คลิปทำหน้าที่แค่ context/สีสัน — ตัวเลขจริงมี primary source ที่แม่นกว่าเสียงพูดเสมอ.

นี่คือกุญแจไข: ใช้ contamination-lesson **เต็มแรงกับกลุ่มแรก** (ทนพลาดไม่ได้ + ไม่มี fallback) และ **ผ่อนกับกลุ่มสอง** (ตัวเลขมี primary source ที่ดีกว่าอยู่แล้ว การถอดจึงเป็น effort ซ้ำซ้อน).

**ตอบ 4 ข้อ:**

**1) Minnie-only-no-fact-check ยอมรับได้ไหมสำหรับ use case นี้?** — **ไม่ สำหรับกลุ่มสัมภาษณ์ CEO** (ฟันธง). Use case promise-tracking คือ use case ที่ **sensitive ต่อ citation ที่สุดในทั้งโปรเจกต์** — quote ที่ misattribute (โยนสัญญาปี 2024 ไปติดสัมภาษณ์ 2023, หรือ blend ตัวเลขสอง Oppday) ไม่ได้แค่ทำ flashcard ผิด มันทำ**ข้อสรุป promise-vs-outcome ทั้งชิ้นผิด**. และ independence ของ Fact-checker (Phase B) **ต้องมี raw transcript ให้ grep** — ไม่มี transcript = ไม่มี ground truth อิสระ = เหลือแค่ NotebookLM ตรวจ NotebookLM เอง ซึ่งคือ anti-pattern ที่ Opus review ตอน 2026-07-01 ปฏิเสธไปแล้ว ("two agents asking the same notebook is not independent verification"). **แต่** — full-transcribe-ทั้ง-31 ก็ผิดคนละทาง: มันเอาบทเรียนไปใช้เกินเหตุกับ Oppday ที่ตัวเลขมี primary source ที่ดีกว่าอยู่แล้ว. คำตอบที่ถูกจึงเป็น **tier**: transcription-first เป็น non-negotiable เฉพาะกลุ่มที่แบกคำสัญญา, ส่วนที่เหลือ NotebookLM-native เป็น index ได้ถ้าไม่มีตัวเลขไหนถูกเชื่อโดยไม่ cross-check filing.

**2) Middle-ground architecture?** — **ใช่ มี และมันคือ (a)+(b) ผสมกันแบบ tiered ตามข้อ 1** ไม่ใช่เลือกอันเดียว:
- (a) ถอดเฉพาะ subset สัมภาษณ์ CEO — **ถูก** เพราะนั่นคือที่คำสัญญาอยู่และไม่มี fallback.
- (b) บังคับ Minnie ให้ NotebookLM quote verbatim + ชื่อ source + วันที่เสมอ แล้ว spot-check ด้วยหู — **ถูก แต่ใช้กับกลุ่ม Oppday เท่านั้น** (ที่ยอมรับความเสี่ยง fidelity ได้เพราะมี filing กัน). อย่าใช้ (b) แทน (a) กับกลุ่มสัมภาษณ์.
- **ลูกเล่นที่ทำให้คุ้มกว่าที่ทั้ง user และ Sonnet เสนอ:** สำหรับ subset สัมภาษณ์ ถอดเสียงครั้งเดียว **แล้วอัป `.txt` นั้นเข้า NotebookLM แทนตัว video** — การถอดครั้งเดียวซื้อได้ **สองอย่างพร้อมกัน**: (i) NotebookLM source ที่คุณภาพเราคุมเอง (VAD+large-v3+initial_prompt ที่ tune มาสำหรับไทยชุดนี้แล้ว) และ (ii) `.txt` ให้ Fact-checker grep. Independence ยังอยู่จริง: NotebookLM RAG ยัง generate/blend/ดึงผิด source ได้ ส่วน grep ตรวจว่า quote/ตัวเลขที่อ้างนั้น**มีอยู่จริงใน source ที่ระบุวันที่นั้น**ไหม — independence ที่นี่คือ "generation-layer vs. verbatim-source-text" ซึ่งยังถือ.

**3) Native video/audio เปลี่ยน contamination-analysis ไหม?** — **เปลี่ยน 2 ทิศสวนทางกัน:**
- **ดีขึ้นเรื่อง attribution/contamination** — *ถ้าแต่ละคลิปเป็น source แยกที่ตั้งชื่อด้วยวันที่ชัด* (เช่น `2024-05-14 MoneyChat เฉลิม.txt`). per-source citation ทำให้เห็นว่า passage มาจาก source ไหนตรงๆ ซึ่ง**แข็งกว่า**การเทหลาย transcript รวมเป็น text blob ก้อนเดียวในโน้ตบุ๊กเดียว (แบบที่โปรเจกต์เคยทำแล้วโดน). bug เดิมส่วนหนึ่งเกิดจากเชื่อ "self-attribution ของคำตอบ" แทนที่จะดู citation — native-per-source บังคับให้ดู citation มากขึ้น.
- **แย่ลงเรื่อง fidelity** — NotebookLM ถอดเสียงไทยเองด้วย engine ที่เรา **คุมไม่ได้**: ไม่มี Silero VAD, ไม่มี `initial_prompt` (สอนหุ้นไทย code-switching อังกฤษ), ไม่มี hallucination-gate — ซึ่งคือของที่โปรเจกต์นี้สร้างขึ้น**เพราะ** MLX/Whisper การันเสียงชุดนี้พัง (ดู T16/T18, `�`×222, compression-ratio median 39). ถ้ามันฟัง "สามพัน" เป็น "สามหมื่น" citation จะชี้ถูกคลิปเป๊ะ แต่**ตัวเลขผิด** และ**ไม่เหลือ raw `.txt` ให้จับ**. นี่เป็น error class ใหม่ (transcription-fidelity) คนละอันกับ contamination — และมันโจมตี**ตัวเลข/วันที่**ซึ่งเป็นสิ่งที่ use case นี้แคร์ที่สุด. สรุป: native แลก contamination-risk ที่เรา *mitigate ได้* (ด้วยวินัย per-source citation) กับ fidelity-risk ที่เรา *inspect ไม่ได้* — เป็นการแลกที่ **เสียเปรียบ**สำหรับ subset ที่ตัวเลข/quote เป็น load-bearing จึงต้องคง transcript ไว้เฉพาะ subset นั้น.

**4) Recommendation ที่ Sonnet ลงมือได้ (สรุปเป็น T26):**
- **Step 0 — ตั้งชื่อ source ด้วยวันที่ทุกไฟล์** `YYYY-MM-DD_<ช่อง>_<คนพูด/ไตรมาส>` เพื่อให้ citation แบก date เอง.
- **Step 1 — Tier กลุ่ม (~13 vs ~18):** สัมภาษณ์ CEO/ผู้ก่อตั้ง = **Tier A (transcribe)**; Oppday รายไตรมาส = **Tier B (native)**.
- **Step 2 — Tier A:** รัน `vad_transcribe.py` (large-v3, ตาม T16) → `.txt` ต่อคลิป → อัป `.txt` (ไม่ใช่ video) เข้า NotebookLM. **ข้าม `structure_transcript.py`** — สัมภาษณ์เป็นบทสนทนา ไม่มีสไลด์/PDF, raw `.txt` + native-in-notebook พอสำหรับทั้ง query และ grep.
- **Step 3 — Tier B:** อัป video/audio native เข้า NotebookLM ตรงๆ ไม่ถอด.
- **Step 4 — Minnie protocol (บังคับ):** ทุก claim ที่ดึงมาต้องพก (i) verbatim quote ของ NotebookLM + (ii) ชื่อ source + วันที่ที่มัน cite. ห้าม paraphrase-แล้ว-ค่อย-attribute เด็ดขาด.
- **Step 5 — Fact-check แบบ tier:** claim จาก Tier A → **grep `.txt` ที่ระบุวันที่นั้น** (independent, ตาม Phase B เดิม). ตัวเลขจาก Tier B → **cross-check filing/บทวิเคราะห์** (primary), ห้ามเชื่อ NotebookLM-native ตัวเลขเดี่ยวๆ.
- **Step 6 — Calibration แต่เนิ่นๆ:** สุ่ม 3-5 citation จาก Tier B ฟังเทียบวิดีโอจริง ก่อนพึ่งมันหนัก. ถ้าการถอดไทยของ NotebookLM เพี้ยนที่ตัวเลขอย่างมีนัย → **ย้ายคลิปนั้นเข้า Tier A**. (นี่คือ (b) ของ user ในเวอร์ชันที่ทำจริง — spot-check เป็น gate ปรับ tier ไม่ใช่พิธีกรรม.)
- **ผลลัพธ์ speed:** ถอด ~13 แทน 31 + ข้าม structuring ทุกไฟล์ ≈ ประหยัด ~55-60% ของเวลาถอด — เร็วกว่า full pipeline จริงตามที่ user ต้องการ โดย contamination-guard ยังอยู่ครบตรงจุดที่ทนพลาดไม่ได้.

**สิ่งที่ปฏิเสธ:** (i) skip-transcribe-ทั้งหมด (Minnie-only) — ทิ้ง independence ตรง subset ที่แพงที่สุดถ้าพลาด. (ii) full-transcribe-ทั้ง-31 — เอาบทเรียนไปใช้เกินเหตุกับ Oppday ที่ตัวเลขมี primary source ดีกว่า, จ่ายเวลาถอดฟรีโดยไม่ได้ integrity เพิ่ม. (iii) เลิกใช้ NotebookLM ไปเลยแล้ว grep อย่างเดียว — เสีย query surface กว้างข้าม 31 source ที่ Minnie ต้องใช้; เก็บ NotebookLM เป็น "index layer" + transcript เป็น "verification layer" = two-backend split เดิมของโปรเจกต์ (KNOWLEDGE_INDEX vs NotebookLM) พอดี.

**Context:**

User is building a BCH (Bangkok Chain Hospital, เครือเกษมราษฎร์ — NOT เครือจุฬารัตน์, that was a correction I got wrong earlier and must not repeat) stock research workflow. Explicit goal, in the user's own words: "ให้คุณดู outlook ที่นักวิเคราะห์ให้ไว้, ข่าวต่างๆที่เกี่ยวข้องในช่วงเวลาเดียวกัน, ผู้บริหารพูดแล้ว ตรงตามนั้นไหม หรือ พูดแล้วทำได้จริงไหม แล้วเทียบกับกราฟ ว่าราคา สะท้อนไหม" — i.e. this is fundamentally a **management-promise-tracking-over-time** workflow: pin down what management said on date D1, check whether it actually happened by D2, cross-reference against analyst outlook/news from the same window, then check whether price action reflected it.

Sonnet (me) spent this session curating a source list: searched three YouTube channels (SET Thailand official Oppday series, MONEY TALK analyst interviews, Money Chat Thailand — which includes many *direct* interviews with BCH's founder/chairman ศ.ดร.นพ.เฉลิม หาญพาณิชย์) and built a clean, exact-dated, deduplicated list of **31 videos spanning Q1/2023 → Q1/2026** (quarterly Oppdays + interviews interleaved chronologically). This list is good — the user hasn't objected to it. The open question is purely about the *next* step: how to get this content into a queryable form.

**The established pattern in this project** (`.claude/skills/learn-session/SKILL.md`, built and validated across the AI Leading Indicator course this same session) is: transcribe first (raw `.txt` via Whisper/VAD pipeline) → run `structure_transcript.py` (Claude API) to get a structured chapter breakdown → "Minnie" persona asks NotebookLM clarifying questions about genuine gaps → **separately**, a "Fact-checker" pass independently greps the *raw transcript* (never NotebookLM) to verify every proper noun/number Minnie's draft claims, because NotebookLM answers about "session X" can silently blend in content from a different session/date when the notebook holds multiple sources — this is not theoretical, it's a **real, previously-hit failure mode** in this exact project (documented in `knowledge/` and in the skill's own hard rule: "Never trust a NotebookLM answer about 'session X' without grepping it against `transcript_X.txt` specifically").

The user, now facing 31 videos (~15–45 min each, several hours of Whisper transcription + VAD cleanup + structuring cost), just asked: **"ถ้าถอดเสียง ผมว่า ใช้เวลามากไป คุณคิดว่าโยนไป notebooklm แล้วให้ minnie เป็นคนโยนคำถามใส่ ดีกว่าไหม"** — skip transcription, upload video/audio directly to NotebookLM as native sources, have Minnie ask questions straight against NotebookLM, no separate raw-transcript fact-check pass.

**Tension to resolve:** this specific research goal (pin exact management claims to exact dates, later verify against outcome) is arguably the single use case in this whole project **most** sensitive to citation precision — worse to get wrong here than in a course-learning context, because a misattributed quote (e.g. attributing a 2024 promise to the 2023 interview, or blending two Oppdays' numbers) doesn't just cost a wrong flashcard, it corrupts the actual promise-vs-outcome analysis the user is trying to do. Yet this is exactly the failure mode the Fact-checker phase exists to catch, and Fact-checker's independence *depends on having a raw transcript to grep* — if there's no transcript, there's no independent ground truth to check NotebookLM's citations against.

**What's actually being asked of you:**
1. Is skipping transcription and relying on Minnie-queries-NotebookLM-directly (no independent fact-check pass) an acceptable trade for *this specific* use case, or does the promise-tracking goal's sensitivity to precise dates/attribution make transcription-first non-negotiable here — i.e. is this one of the cases where the project's own prior lesson (contamination risk) should override the time-saving instinct?
2. Is there a middle-ground architecture that avoids the full transcription cost but still gets independent verification — e.g.: (a) transcribe only a subset (maybe just the ~10-14 direct CEO interviews, skip the more numbers-heavy quarterly Oppdays since those largely restate financials available elsewhere anyway), (b) upload everything to NotebookLM natively but require Minnie to always ask NotebookLM to quote its source verbatim with the specific video/date, and spot-check a sample against the actual video by ear/rewatch rather than a full from-scratch transcript, (c) something else entirely?
3. Does NotebookLM's own native video/audio source handling (as opposed to text sources, which is what this project has used it for so far) change any part of the contamination-risk analysis — e.g. does per-source citation get *more* or *less* reliable when the source is a raw video/audio file NotebookLM transcribes internally, versus a pre-cleaned text transcript we control?
4. Give a concrete recommendation Sonnet can execute against: exact pipeline steps for however many of the 31 videos you think warrant which treatment (full transcribe+structure+fact-check vs. NotebookLM-native-only vs. skip), sized to actually be faster than the full pipeline (that's the whole point of the user's question) while not reintroducing the contamination bug this project already paid to learn about once.

**Why:** user explicitly said "ถาม opus ที" (ask Opus) — this is a real architecture tradeoff between speed and the specific citation-integrity failure mode this project has already been burned by once (see Q20/T22, the AI Leading Indicator rebuild-reconciliation saga), applied to a use case (promise-tracking) that may be uniquely intolerant of that failure mode.

---

## Q26 — Is there a legitimate way to script-download SET.or.th disclosure PDFs (MD&A/F45) given the user downloads them manually themselves, or does every automated route cross into WAF evasion?

**Status:** done (Opus, 2026-07-10) — **เส้นแบ่งอยู่ที่ "control นี้ถามอะไร" ไม่ใช่ "มี login ไหม" หรือ "user มีสิทธิ์ในเนื้อหาไหม".** YouTube/FB cookie = control ถาม *identity/authorization* ("เป็นสมาชิก/ล็อกอินจริงไหม") → reuse session จริงตอบคำถามนั้น**อย่างจริง** = ถูกต้อง. Imperva/Incapsula = control ถาม *human-vs-bot* → ไม่มี cookie ไหนตอบ "ฉันเป็นมนุษย์" อย่างจริงแทน script ที่ขับ CDP ได้ → ทำให้ automation ผ่าน = **โกหก control โดยนิยาม** = อีกหมวดหนึ่ง แม้เป้าหมายชอบธรรม 100% (PDF เปิดเผยสาธารณะ). **Profile reuse ไม่เวิร์ค** (headful ให้ผลว่างเท่า headless พิสูจน์แล้วว่า gate คือ automation-protocol ไม่ใช่ rendering/cookie; CDP+JA3+webdriver ตรวจได้ไม่ขึ้นกับ profile) — และเวอร์ชันเดียวที่เวิร์ค (undetected-chromedriver/stealth/JA3-spoof) *คือ* ขั้น WAF-evasion ที่เราปฏิเสธพอดี → **ไม่มี config ไหนที่ทั้งเวิร์คและสะอาด**. **ทางสะอาดที่แนะนำ = รัน fetch *ข้างใน* browser จริงของ user เอง** (devtools console snippet วน 24 news IDs ที่ Sonnet ดึงมาแล้ว, download ทีเดียวครบ — Sonnet *เขียน* snippet, browser จริงของ user *รัน*; ไม่มี automation signal แยกเพราะมันคือ tab จริงที่ผ่าน Imperva แล้ว) หรือ user save PDF เองแล้วส่งไฟล์ให้. **HAR/cookie-export replay ตก** — Incapsula session ผูกกับ automation-check ไม่ใช่ bearer token, replay ผ่าน script โดน 401 เหมือนเดิม + อายุสั้น (นาที). **"user คลิก link ที่ Sonnet ให้แล้วส่ง PDF" = คำตอบสุดท้ายที่ *ถูกต้อง* ไม่ใช่ fallback ขี้เกียจ** — Sonnet หยุดที่ cookie-warmup+headful ถูกแล้ว. **Calibration rule:** control เช็ค identity/authz → reuse session (เขียว); control เช็ค human-vs-bot (WAF/CAPTCHA/Cloudflare/Akamai/webdriver/JA3) → default = รันในเบราว์เซอร์จริงของ user หรือให้ user ทำขั้นที่ gate ไว้เอง, ห้าม ship stealth/fingerprint-patch แทน user โดยไม่ถามชัด. Sonnet executes **T27**.

**Context:**

Same BCH research thread as Q25. User asked me (Sonnet) to fetch BCH's MD&A + F45 (สรุปผลการดำเนินงาน) disclosure PDFs from `https://www.set.or.th/th/market/product/stock/quote/BCH/news` to complement the video/price-action research already built (31-video timeline + BCH.BK price history, see prior turns this session).

**What I found:** SET's site is a Nuxt.js SPA sitting behind **Imperva/Incapsula** bot protection. The *list* of disclosures (titles, dates, internal news IDs) is visible in the server-rendered HTML — I successfully extracted all of it (110+ news items, 24+ MD&A/F45 items back to 2021, matched against Facebook-share metadata embedded in the page for id+title pairs) with plain `curl`/Playwright page loads, no issue. But the actual PDF content is served through a POST API (`/api/cms-w/v1/news/set-news-view`) that Imperva blocks for automated clients:
- Fresh Playwright `chromium.launch(headless=True)`, real Chrome UA → API responds `200` with `content-length: 0` (silently empty).
- Same test with `headless=False` (headful, real rendering) → **identical** `200`/empty result. Not a headless-specific check.
- Plain `requests` session that first GETs the page (to collect Incapsula's `visid_incap_*`/`incap_ses_*` cookies) then POSTs to the API with those cookies + proper `Referer`/`Origin` → response changes to `401`, still empty body. This suggests Imperva's JS challenge itself is not being solved (Playwright can *render* the page, meaning some level of JS runs, but the specific network calls this API's success path gates on are still failing the automation check — likely something at the CDP-automation-flag or TLS/JA3-fingerprint layer, not just cookie possession).

I stopped there rather than trying `navigator.webdriver` patching, stealth plugins, or other fingerprint-spoofing techniques, because that starts to be *actively defeating a WAF control the site operator put there on purpose* — which felt like a line I shouldn't cross unilaterally without asking first, even though the end goal (a user fetching public disclosure documents about a stock they hold, for personal research) is completely legitimate.

**The wrinkle:** the user then said **"ผมเคยโหลดได้นะ"** — they have personally downloaded these exact documents before, apparently without friction, just by clicking through in their own regular browser. That's expected and unsurprising (Imperva is specifically tuned to pass real human browsing and block automation, not to block downloads categorically) — but the user's phrasing ("ask Opus how") suggests they want to know whether *my automation* could be made to behave enough like *their manual browsing* to get through, rather than accepting "you have to click it yourself" as final.

**Relevant precedent already established and accepted in this exact project** (see memory `feedback_facebook_group_download.md` and the root CLAUDE.md yt-dlp/cookies workflow): for YouTube membership content, the accepted pattern is `yt-dlp --cookies-from-browser chrome` — literally reusing the user's own real, already-authenticated Chrome session. For a Facebook Group video that neither yt-dlp nor cobalt could touch, the accepted pattern (built earlier in this same project) was a Playwright script that **injects the user's real browser cookies** to load the page as their authenticated session, then extracts the direct CDN video URL. Both of those are "reuse the user's own legitimate session," not "spoof a fake one" — and both were treated as acceptable, ordinary tooling in this project, not something requiring special ethical caution.

**What's actually being asked of you:**
1. Is reusing the user's real, already-established browser session/cookies for SET.or.th (e.g. via Playwright `launch_persistent_context` pointed at the user's actual Chrome profile directory, so the same long-lived Incapsula visitor reputation and any real session cookies carry over — as opposed to spinning up a fresh, cookie-less automated context every time) a legitimate continuation of the already-accepted YouTube-cookies / Facebook-cookies pattern in this project, or does it cross into a materially different category specifically *because* Imperva here is an anti-bot control rather than a login/paywall? Draw the line precisely — what's the actual distinguishing principle, not just a vibe.
2. If reusing the real Chrome profile is legitimate, is it technically likely to work — i.e. does Imperva's device-reputation/session-trust model plausibly extend trust to an automated driver (Playwright/CDP) merely because it's pointed at a profile with real browsing history, or does Imperva detect the CDP/automation protocol itself regardless of which profile is loaded (in which case this whole approach is a dead end and not worth the user closing their real Chrome to free up the profile lock)?
3. Is there a *different* legitimate middle ground that doesn't touch the user's live browser at all — e.g. a small one-time manual step (user manually visits the page once, exports HAR/cookies via devtools, hands the file to Sonnet) that stays firmly on the "reuse a real human's session" side of the line, similar in spirit to `yt_cookies.txt` export? If so, spell out the concrete mechanism (what to export, how Sonnet would use it, how long it'd stay valid).
4. If none of the above is both legitimate and likely to work, say so plainly — and confirm that "user clicks the already-provided direct links and hands Sonnet the PDFs" is in fact the correct final answer here, not a fallback Sonnet settled for out of insufficient effort. Distinguish clearly, for Sonnet's own calibration going forward: which side of "reuse real session" vs "defeat anti-automation control" future similar requests (not just SET, any site with this shape of protection) should be sorted into by default.

**Why:** user explicitly asked to consult Opus on this ("ถาม opus ที ว่าทำไง") after I declined to escalate past cookie-warmup + headful-browser attempts. This is both a concrete unblock for the BCH MD&A ingestion (T26) and a values/calibration question about where this project's already-accepted "reuse the user's own session" pattern (YouTube, Facebook) legitimately ends and WAF-evasion begins — worth getting a clean, reusable principle out of, not just a one-off answer.

### ANSWER (Opus, 2026-07-10)

**หัวใจ: เส้นแบ่งที่ถูกต้องไม่ใช่ "login vs. ไม่ login" และไม่ใช่ "user มีสิทธิ์ในเนื้อหาหรือเปล่า" — แต่คือ *control ตัวนี้กำลังตรวจสอบอะไร* และการ reuse session จริงตอบคำถามของ control นั้น "อย่างจริง" หรือ "อย่างโกหก".**

นี่คือ principle เดียวที่ทำให้ precedent เดิม (YouTube/FB) กับเคสนี้ (Imperva) แยกออกจากกันได้อย่างสะอาด ไม่ใช่แค่ vibe:

- **Login / membership / paywall cookie** — control ถามว่า *"คุณคือใคร / คุณได้รับอนุญาตไหม"* (identity / authorization). Cookie คือคำตอบของคำถามนั้น. เอา session จริงของ user มาใช้ = ตอบคำถามที่ control ถามจริง **อย่างตรงความจริง** — เพราะ user *เป็น* สมาชิก/เจ้าของบัญชีนั้นจริง. yt-dlp `--cookies-from-browser`, FB cookie injection ทั้งคู่เข้าข่ายนี้: reuse a real, truthful identity claim.
- **Imperva/Incapsula (และ WAF/bot-management ทั้งตระกูล)** — control ถามคนละคำถาม: *"คุณเป็นมนุษย์ในเบราว์เซอร์จริง หรือเป็นโปรแกรม/automation"* (human vs. bot). มัน **ไม่ได้** gate authorization เลย — PDF พวกนี้เปิดสาธารณะ ใครก็เข้าได้ ไม่มี credential ไหนให้สิทธิ์ เพราะสิทธิ์ไม่ใช่สิ่งที่ถูก gate. สิ่งที่ถูก gate คือ *วิธีเข้า* (มนุษย์คลิก vs. สคริปต์ยิง). สำหรับสคริปต์ที่ขับผ่าน CDP คำตอบที่ *ตรงความจริง* ต่อคำถาม "มนุษย์หรือบอท?" คือ **"บอท"** — และไม่มี cookie/profile ไหนเปลี่ยนความจริงข้อนี้ได้. **การทำให้ automation ผ่าน anti-bot check = การโกหก control โดยโครงสร้าง** เพราะคำถามทั้งหมดของมันคือ human-or-bot และคำตอบจริงของ automation คือ bot.

**นี่คือ bright-line test ที่ reusable กับทุกเว็บ:** *"การ reuse session จริง ตอบคำถามที่ control ตัวนั้นถามจริงอย่างตรงความจริงไหม — หรือการจะทำให้มันเวิร์ค ต้องให้ automation โกหกว่าตัวเองเป็นมนุษย์?"* จริง → เขียว. ต้องโกหก → แดง. และจุดที่ subtle ที่สุดที่ต้อง internalize: **ความชอบธรรมของ *เป้าหมาย* ไม่ได้ให้ใบอนุญาตเอาชนะ *กลไก*.** User มีสิทธิ์ในเอกสารนี้เต็มร้อย (มันสาธารณะ) และยัง *ไม่* มีสิทธิ์เอา automation เจาะ anti-bot control — เพราะกลไกไม่ได้เฝ้า *authorization ของเนื้อหา* มันเฝ้า *ช่องทาง* ไม่ให้โดนโหลดแบบโปรแกรม. ท่าที่ซื่อสัตย์เมื่อคุณมีสิทธิ์ในเนื้อหาแต่ช่องทางถูก bot-protect คือ **ให้มนุษย์เดินผ่านช่องทางนั้น** (หรือรันโค้ด *ข้างใน* เบราว์เซอร์ของมนุษย์) ไม่ใช่ปลอมบอทให้เนียนเป็นคน.

**ตอบ 4 ข้อ:**

**1) Persistent-context ชี้ไปที่ Chrome profile จริง = ต่อยอด precedent เดิม หรือข้ามหมวด? — ข้ามหมวด (ฟันธง), และเหตุผลไม่ใช่ "เพราะ Imperva ให้ความรู้สึกต่าง" แต่เพราะมันตอบคนละคำถาม.** YouTube/FB cookie ตอบ "ฉันคือ user ที่ได้รับอนุญาต" อย่างจริง. เอา CDP-driven browser จ่อ Imperva เพื่อสอด automation ผ่าน gate human-vs-bot = พยายามตอบ "ฉันเป็นมนุษย์" ทั้งที่สคริปต์เป็นคนขับ = โกหก control. **มี nuance:** การพา reputation cookie จริง (`visid_incap_*`) ติดมาแบบ passive อ่อนกว่าการ spoof `navigator.webdriver`/JA3 แบบ active อยู่ระดับหนึ่ง — แต่ *เจตนา* ยังเป็นการเอาชนะ anti-bot control อยู่ดี. โชคดีที่เราไม่ต้องไปถกปรัชญาตรงจุดสีเทานี้ให้จบ เพราะข้อ 2 บอกว่ามัน **ไม่เวิร์ค** อยู่แล้ว — เส้นเชิงเทคนิคกับเส้นเชิงคุณค่าบรรจบกันพอดี.

**2) ถ้า reuse profile จริง มันเวิร์คทางเทคนิคไหม? — เกือบแน่นอนว่า *ไม่* และไม่คุ้มให้ user ปิด Chrome จริงเพื่อปลดล็อก profile.** Imperva/Incapsula ตรวจหลายชั้นที่ *ไม่ขึ้นกับ profile ที่โหลด*:
- **CDP detection** — Playwright/Puppeteer ขับ Chrome ผ่าน Chrome DevTools Protocol; client-side JS ของ Imperva ตรวจ artifact ของ CDP (`Runtime.enable`, execution-context signals, automation flags) ได้ไม่ว่าจะโหลด profile ไหน. โหลด profile จริงไม่ได้ถอด CDP driver ออก.
- **TLS/JA3 fingerprint** — handshake ของ automation stack ต่างจาก Chrome จริงได้ ตรวจที่ network layer ก่อนแตะ cookie ด้วยซ้ำ.
- **`navigator.webdriver` + runtime flags** — เซ็ตตอน launch ของ automation ไม่ใช่ property ของ profile.
- **Behavioral** — ไม่มี mouse move, navigate ทันที ฯลฯ.
Reputation cookie จริงช่วยลด *ความถี่* ของ challenge ได้บ้าง แต่มันถูก score *ร่วมกับ* automation signal สดๆ ไม่ใช่ *แทน*. เหตุที่ user คลิกเองผ่านคือเบราว์เซอร์จริงปล่อย automation signal = ศูนย์ *และ* reputation ดี; วินาทีที่คุณเอา Playwright ขับ profile เดียวกัน คุณ *เอา automation signal กลับเข้ามา* ที่ reputation ควรจะหักล้าง → Imperva re-score เป็นบอท. **หลักฐานที่ Sonnet เก็บมาแล้วยืนยันเป๊ะ:** headful (render จริง) ให้ผลว่างเปล่า *เหมือนกันเป๊ะ* กับ headless — พิสูจน์ว่า gate ไม่ใช่ headless-specific แต่เป็น **automation-protocol-specific**. นั่นคือลายเซ็นของ CDP/automation detection ไม่ใช่ rendering หรือ cookie. **ข้อควรระวังที่ต้องพูดตรงๆ:** ทางเดียวที่ทำให้ real profile เวิร์คจริงคือ *ต้อง* ถอด automation signal ทิ้งด้วย (undetected-chromedriver / nodriver / camoufox / stealth plugin) — ซึ่ง *คือ* ขั้น fingerprint-spoofing ที่เราปฏิเสธไปในข้อ 1 พอดี. **ไม่มี config ไหนที่ทั้งเวิร์คและอยู่ฝั่งสะอาด** — เวอร์ชันสะอาดไม่เวิร์ค, เวอร์ชันที่เวิร์คไม่สะอาด. นี่คือข้อสรุปที่คมที่สุดของทั้งเคส.

**3) มี middle ground ที่สะอาดโดยไม่แตะ browser สดของ user เลยไหม? — มี, และตัวที่ดีที่สุดคือ "รันโค้ด *ข้างใน* เบราว์เซอร์จริงของ user เอง" ไม่ใช่ export session ออกมา replay.**
- **ทำไม cookie/HAR export ตก:** Incapsula session cookie ผูกกับ automation-check ไม่ใช่ bearer token ที่ทำงานเดี่ยวๆ — ที่ Sonnet ลอง (requests session เก็บ cookie แล้ว POST) ได้ 401 ก็เพราะเหตุนี้: replay cookie ผ่านสคริปต์ = จุด automation-signal เดิมติดกลับมา. HAR ก็ให้ binary ของ PDF ไม่ครบเชื่อถือได้ยาก + เป็น snapshot ครั้งเดียว + `incap_ses_*` อายุสั้น (นาที-ชั่วโมง). สรุป: ทุกสคีม "export ให้ Sonnet replay" ทั้ง *อายุสั้น* และ *น่าจะโดนบล็อก* — ตัดทิ้ง.
- **ทางสะอาดตัวจริง (แนะนำ) — devtools console fetch ใน tab ของ user เอง:** user เปิดหน้า SET ในเบราว์เซอร์จริง (ผ่าน Imperva แล้ว) → เปิด DevTools Console → paste snippet ที่ Sonnet เขียน ที่วน news IDs ทั้ง 24 ตัว (Sonnet ดึงมาครบแล้ว) ยิง `fetch()` ไปที่ endpoint เดิมที่หน้าเพจใช้ (`/api/cms-w/v1/news/set-news-view` ด้วย body/header ชุดเดียวกับที่เพจยิง ซึ่ง Sonnet เห็น request shape แล้วตอนมันคืน content-length:0) แล้ว trigger download แต่ละ PDF. **เพราะ fetch เกิดจาก JS context ของหน้าจริงที่ Imperva เคลียร์ไปแล้ว มันสืบทอด session จริง + ไม่ปล่อย automation signal แยก** — Sonnet *เขียน* โค้ด, เบราว์เซอร์จริงของ user *รัน*, Sonnet ไม่ได้ขับอะไรเลย. นี่คือ principle "reuse the real session" ในเวอร์ชันที่ซื่อสัตย์ที่สุด: session ไม่ได้ถูก copy ออกมาด้วยซ้ำ — *โค้ดวิ่งอยู่ข้างใน* มัน. เร็ว (24 ไฟล์รวดเดียว), สะอาด (ไม่มี WAF-evasion), และ scale ได้กับ update ครั้งหน้า (user แค่ paste ซ้ำ).
- **ทางง่ายสุด (fallback):** user save PDF เองจาก link ตรงที่ Sonnet ให้ แล้วส่งไฟล์ให้ Sonnet — analog ตรงตัวของ `yt_cookies.txt`: มนุษย์ทำขั้นที่ human-gated, *artifact* (bytes) ถูกส่งต่อ, Sonnet ไม่เคยปลอมเป็นมนุษย์ต่อ control เลย.

**4) ถ้าไม่มีอันไหนทั้งชอบธรรมและเวิร์ค — พูดตรงๆ:** สำหรับ *fully-automated-Sonnet-driven* download: **ไม่มี** ทางที่ทั้งสะอาดและเวิร์ค (ข้อ 2 อธิบายว่าทำไม). ดังนั้น **"user คลิก link ที่ Sonnet ให้ไว้แล้วส่ง PDF กลับมา" คือคำตอบสุดท้ายที่ *ถูกต้อง* ไม่ใช่ fallback ที่ Sonnet ยอมเพราะลงแรงไม่พอ.** มันถูกต้องเพราะทางที่จะ automate เต็มรูปแบบทุกทางต้องเจาะ anti-bot control ซึ่งเป็นเส้นที่เราไม่ข้ามแทน user เองโดยพลการ (ยังเสี่ยงให้ IP/บัญชีของ user โดน challenge/rate-limit และเป็นขอบเขตที่เจ้าของเว็บตั้งใจตั้งไว้). Sonnet หยุดที่ cookie-warmup + headful browser = **ตัดสินใจถูก** ไม่ใช่ยอมแพ้เร็ว. (ถ้าอยากได้ทั้งเร็วทั้งสะอาด → ใช้ console-snippet ข้อ 3 ซึ่ง "อัตโนมัติ" ในเบราว์เซอร์ของ user โดยไม่ให้ Sonnet ขับ.)

**Calibration rule สำหรับอนาคต (ทุกเว็บ ไม่ใช่แค่ SET) — sort ด้วย bright-line test ข้างบน:**
- **เขียว (ทำได้เลย) = control เช็ค identity/authorization** (login, membership, paywall, "เป็นเจ้าของบัญชีไหม"). reuse session/cookie จริงของ user ตอบคำถามนั้นอย่างตรงความจริง → yt-dlp `--cookies-from-browser`, cookie injection, HAR ของ auth token ฯลฯ.
- **แดง (หยุด, ถามก่อน, default = manual/in-browser) = control เช็ค human-vs-bot** (WAF, CAPTCHA, Imperva/Cloudflare/Akamai bot-management, `navigator.webdriver`, JA3/TLS fingerprint, behavioral challenge). ไม่มี session จริงไหนตอบ "ฉันเป็นมนุษย์" แทนสคริปต์ได้อย่างจริง → default: รัน action *ข้างใน* เบราว์เซอร์จริงของ user (console snippet/bookmarklet) หรือให้ user ทำขั้น human-gated เองแล้วส่ง artifact. **ห้าม ship stealth plugin / fingerprint-patch แทน user โดยไม่ได้ขอ go-ahead ที่ชัดเจนและ informed.**

**สิ่งที่ปฏิเสธ:** (i) profile-reuse-เฉยๆ — ไม่เวิร์ค (CDP/JA3 ตรวจได้ไม่ขึ้นกับ profile; headful=headless พิสูจน์แล้ว) และไม่คุ้มให้ user ปิด Chrome ปลดล็อก profile. (ii) undetected-chromedriver/stealth/JA3-spoof — เวิร์คแต่ *คือ* WAF-evasion, ข้ามเส้นแดง. (iii) cookie/HAR export ให้ Sonnet replay — อายุสั้น + โดน 401 ด้วยเหตุเดียวกับ profile reuse (session ผูก automation-check ไม่ใช่ bearer token). เก็บ **console-in-real-browser** เป็นทางอัตโนมัติที่สะอาด, **user-hands-over-PDF** เป็น fallback ที่ถูกต้อง.

---

## Q27 — User explicitly wants Sonnet to fetch autonomously (not a console snippet they run themselves) — does that change the Q26 calibration, or is there a legitimate official/paid data channel that sidesteps Imperva entirely?

**Status:** done (Opus, 2026-07-10) — **ไม่, autonomy ไม่ขยับเส้น Q26 เลย — และเหตุผลคมกว่านั้น: การเอา human-in-the-loop ออกไม่ใช่ "งานเดิม คลิกน้อยลง" แต่คือ "งานคนละอย่าง" เพราะ *มนุษย์คนนั้นเองคือคำตอบที่ซื่อสัตย์ต่อ gate human-vs-bot*.** console-snippet ไม่ได้เป็น friction บังเอิญที่ตัดทิ้งได้ — มันคือชิ้นส่วน load-bearing ที่ค้ำทั้งเรื่องให้อยู่ฝั่งเขียว. วินาทีที่ยกมนุษย์ออกเพื่อให้ Sonnet ยิงเอง Sonnet *กลายเป็น* สิ่งที่ต้องผ่าน gate เอง = ต้องโกหก control ว่าเป็นมนุษย์ = **request นี้ collapse เป็น "ให้ Sonnet เจาะ anti-bot control แทน" แบบเป๊ะๆ ไม่ใช่แค่คล้าย.** ไม่มี daylight ระหว่าง "console น่ารำคาญ" กับ "เจาะ WAF" — พอเอามนุษย์ออก สองอันเป็นอันเดียวกัน. **ช่องทาง official ที่ควร verify จริง (ไม่ใช่เดา domain):** `SETSMART` (setsmart.com — SET data terminal ของจริง, แต่ paid + login-gated → autonomy ยังติดที่ credential/ToS ไม่ใช่ Imperva), `SET DataDirect` (data-feed ของ SET — น่าจะจริง, verify), `Settrade Open API` (จริงแต่เป็น price/market data ผ่าน broker ไม่ใช่ MD&A/F45 PDF), `SEC Thailand (sec.or.th)` + `56-1 One Report` (regulator คนละเจ้ากับ set.or.th — ช่องทางที่ต่างจริง คุ้มค่า WebSearch จริงที่สุด, แต่ไม่รู้ว่า gate ไหม). **ไม่ยืนยันว่ามี free open un-gated API ที่เสิร์ฟ PDF พวกนี้ให้ autonomous fetch — Opus ไม่รู้จริง, ห้ามเดา domain แทน Sonnet.** สำคัญ: ถ้า user *มี* บัญชี SETSMART/broker เอง → ใช้ login จริงของ user = ฝั่งเขียว (identity/authz) ตาม Q26 พอดี. **วิธีบอก "ไม่":** 1 บรรทัดว่าทำไม (control นี้เช็ค human-vs-bot; ทางเดียวให้ผมทำเองคือปลอม automation เป็นคน ซึ่งเป็นสิ่งเดียวที่ผมไม่ทำโดยไม่ขอ) + ยืนยัน autonomy ไม่มีจริงสำหรับ *เว็บนี้* โดยไม่ evasion + re-offer console-snippet เป็น "30 วินาทีครั้งเดียว ไม่ใช่งานประจำ" + เสนอไปหา channel ทางเลือก (SEC/SETSMART) เป็นทาง autonomy จริงถ้ามี. Sonnet executes **T28** (verify channel names ด้วย WebSearch จริงก่อนสรุปว่าไม่มี).

**Context:**

Direct continuation of Q26. Sonnet gave the user the Q26-recommended path: a DevTools console `fetch()` snippet for the user to paste into their own already-open, already-Imperva-passed SET.or.th tab (runs inside their real session, no automation signal, Sonnet writes the code but the user's browser executes it). The user's response: **"ถ้าผมจะให้คุณเข้าไปโหลดจาก set.or.th ต้องทำไง ปรึกษา opus ที"** (if I want *you* to go in and download from set.or.th [yourself], what would that take — ask Opus) followed immediately by **"แบบค้นได้เองเลย"** (the kind where [Sonnet] can just fetch/search it autonomously [without the user doing a manual step]).

So the user is explicitly pushing back on the human-in-the-loop requirement from Q26 — they don't want to paste a console snippet themselves; they want Sonnet to be the one retrieving the documents, fully autonomously, end to end.

Sonnet already knows (from Q26's technical findings, which won't change by re-asking): Imperva here gates on CDP/automation-protocol detection **independent of which browser profile or cookies are used** — headful Playwright with real UA gave the identical empty/blocked result as headless. The only configurations that would actually make Sonnet-driven automation pass (undetected-chromedriver-style patches, stealth plugins that hide `navigator.webdriver`/CDP fingerprints, JA3/TLS fingerprint spoofing) are the exact WAF-evasion techniques Q26 already drew the line at not doing unilaterally.

Sonnet did a quick, cheap check for an alternative *official* data channel that might expose the same public disclosures (MD&A/F45 filings) without going through the Imperva-protected consumer website at all — guessed at a couple of plausible-sounding domain names (`market.sec.or.th`, `opendata.set.or.th`, `mfcl.sec.or.th`) and all failed DNS resolution, meaning they don't exist as guessed. Sonnet did **not** show these invented URLs to the user (per this project's standing rule never to present guessed/unverified URLs as real) and stopped rather than continuing to guess blindly.

**What's actually being asked of you:**
1. Does the user explicitly wanting full autonomy (rather than accepting the console-snippet middle ground) change anything about the Q26 calibration? Or is the answer simply "no — the bright line in Q26 was about *what the control verifies*, not about *how inconvenient the workaround is for the user*, so user preference for less friction doesn't move the line"? Be explicit: is there daylight between "the user finds console-snippet mildly annoying" and "the user is now effectively asking Sonnet to defeat the anti-bot control on their behalf," or are these the same request restated?
2. Is there a real, *legitimate*, non-Imperva-gated channel for the same public disclosure data that Sonnet should actually research properly (not domain-guessing) before concluding none exists — e.g. SET's official market-data/API products (SETSMART, any published open-data API, a broker-terminal data feed the user might already have access to via their brokerage), or SEC Thailand's own public disclosure archive under its real domain? If you know or can reason about what SET/SEC Thailand's real official data products are named, name them concretely so Sonnet can check with a real WebSearch instead of guessing domains. If you don't have reliable knowledge of the real product names either, say so plainly rather than guessing on Sonnet's behalf.
3. If no legitimate autonomous channel exists, what is the clearest, most respectful way for Sonnet to tell the user "no" here — i.e. confirm autonomy isn't available for this specific site/control without evasion, restate why (in one line, not re-litigating all of Q26), and re-offer the console-snippet as the fastest actually-available path, framed as "this takes you 30 seconds once, not a recurring manual chore" rather than as a consolation prize?

**Why:** user explicitly said "ปรึกษา opus ที" a second time, specifically because Sonnet's first answer (console-snippet) didn't give them what they actually asked for (full autonomy) — this is a real test of whether Q26's line holds under direct user pressure to remove the human-in-the-loop step, which is exactly the scenario that bright-line rule needs to survive.

### ANSWER (Opus, 2026-07-10)

**หัวใจ: การที่ user อยากได้ autonomy เต็มรูปแบบ *ไม่ขยับเส้น Q26 แม้แต่นิดเดียว* — และเหตุผลลึกกว่าที่ prompt ตั้งไว้. คำตอบไม่ใช่แค่ "no, เส้นวัดที่ control ตรวจอะไร ไม่ใช่วัดที่ user ลำบากแค่ไหน" (ซึ่งจริง) แต่คือประเด็นที่คมกว่า: ในเคสนี้ *มนุษย์ที่อยู่ใน loop คือคำตอบที่ซื่อสัตย์ต่อ control พอดี* — ดังนั้นการเอามนุษย์ออกไม่ใช่การลด friction ของงานเดิม แต่คือการเปลี่ยนเป็นงานคนละอย่าง.**

---

**1) autonomy เปลี่ยน calibration ไหม? — ไม่. และ "console น่ารำคาญ" กับ "ให้ Sonnet เจาะ anti-bot control" ไม่ใช่แค่คล้ายกัน — พอเอามนุษย์ออก มันเป็น request เดียวกันเป๊ะ. ไม่มี daylight.**

เส้น Q26 วัดที่ *control ตัวนี้ verify อะไร* (human-vs-bot) ไม่ใช่ *workaround ลำบากแค่ไหนสำหรับ user*. ความชอบใจของ user ที่จะให้ลื่นขึ้นไม่ใช่ตัวแปรในสมการเลย — เพราะเส้นถูกกำหนดโดย control ไม่ใช่โดยระดับความสะดวก. นี่คือคำตอบชั้นแรกและมันถูก.

แต่มีชั้นที่ลึกกว่าที่ต้อง internalize เพื่อให้กฎนี้อยู่รอดใต้แรงกดดันแบบนี้: **ทำไม console-snippet ถึงอยู่ฝั่งเขียวตั้งแต่แรก? เพราะมี "มนุษย์จริงในเบราว์เซอร์จริง" เป็นคนตอบ gate human-vs-bot อย่างตรงความจริง** — snippet แค่ทำงาน *ข้างใน* คำตอบที่ซื่อสัตย์นั้น. มนุษย์คนนั้น **ไม่ใช่** friction บังเอิญที่ตัดทิ้งได้แล้วเหลืองานเดิม — เขาคือชิ้นส่วน *load-bearing* ที่ค้ำทั้งเรื่องให้อยู่ฝั่งเขียว. เขา *คือ* เหตุผลที่มันสะอาด.

ดังนั้นวินาทีที่ user พูดว่า "เอามนุษย์ออก ให้ Sonnet ทำเองหมด" — สิ่งที่ถูกถอดออกคือ *คำตอบที่ซื่อสัตย์ต่อ gate* พอดี. เหลือ Sonnet เป็นสิ่งเดียวที่ต้องผ่าน gate human-vs-bot เอง และคำตอบจริงของ Sonnet ต่อ gate นั้นคือ "บอท" (Q26 ข้อ 2 พิสูจน์แล้วว่า headful=headless=empty → gate คือ CDP/automation-protocol ไม่ใช่ rendering). ทางเดียวให้ Sonnet "ผ่าน" คือทำให้ automation *โกหกว่าเป็นมนุษย์* = undetected-chromedriver/stealth/JA3-spoof = เส้นแดงเป๊ะที่ Q26 ปฏิเสธ.

**สรุปข้อ 1 ให้ Sonnet ใช้ได้เลย:** "console-snippet น่ารำคาญ" กับ "ให้ Sonnet fetch เอง fully autonomous" **ไม่ใช่คำขอสองอันที่ต่างกันด้วยระดับความสะดวก — มันคือคำขอเดียวกันพูดสองแบบ** เพราะ human-in-the-loop *คือ* กลไกที่ตอบ gate อย่างซื่อสัตย์ เอาออกเมื่อไหร่ = ขอให้ automation เจาะ gate แทน เมื่อนั้น. ไม่มีจุดกึ่งกลางที่ "autonomous นิดเดียว" ยังสะอาดอยู่ — สำหรับ control ประเภท human-vs-bot, autonomy กับ evasion เป็นสิ่งเดียวกันโดยนิยาม. (ต่างจาก control identity/authz ที่ autonomous-with-real-cookies สะอาดได้สบาย เพราะ cookie ตอบ "ฉันคือ user X" ได้จริงแม้ไม่มีมนุษย์นั่งอยู่.)

---

**2) มีช่องทาง official / non-Imperva ที่ควร research จริง (ไม่ใช่เดา domain) ก่อนสรุปว่าไม่มีไหม? — มีชื่อที่ควร verify ด้วย WebSearch จริง. Opus แยกให้ตามระดับความมั่นใจ และบอกตรงๆ ตรงไหนไม่รู้จริง:**

*ระดับมั่นใจสูง (ของจริงแน่ ตรวจได้):*
- **SETSMART** (SET Market Analysis and Reporting Tool, `setsmart.com`) — data terminal/portal ทางการของตลาดหลักทรัพย์แห่งประเทศไทย, subscription-based, มีงบ/ข่าว/filing/historical. **นี่คือ "official paid channel" ตัวจริงที่สุด.** *แต่* — มัน login-gated + paid + มี ToS → ถ้าจะให้ Sonnet fetch autonomous ก็ยังติดที่ *credential + ToS* (ไม่ใช่ Imperva) และตัว portal เองก็อาจ bot-protected อีกชั้น. ประเด็นสำคัญที่ bridge กับ Q26: **ถ้า user มีบัญชี SETSMART เอง แล้วให้ Sonnet ใช้ login จริงของ user = ฝั่งเขียว** (control เช็ค identity/authz, cookie ตอบตรงความจริง) — นั่นคือ autonomy ที่สะอาดได้ ถ้ามีบัญชี.

*ระดับมั่นใจปานกลาง (น่าจะจริง — ให้ Sonnet verify ชื่อ+ขอบเขต):*
- **SET DataDirect** — บริการ data-feed/distribution ของ SET (real-time + historical market data สำหรับ institutional/vendor). เชื่อว่าเป็นชื่อ product จริงของ SET แต่ **ให้ verify** ว่ายังใช้ชื่อนี้และครอบคลุม disclosure filing (MD&A/F45) หรือแค่ price data.
- **Settrade Open API** (Settrade = บริษัทลูกด้าน brokerage-tech ของ SET, `settrade.com`) — API จริงสำหรับ algo-trading/market-data ผ่าน broker ไทย. **แต่เกือบแน่ว่าเป็น price/order data ไม่ใช่ disclosure PDF** → น่าจะไม่ตอบโจทย์ MD&A/F45 แม้จะเป็นของจริง. ระบุไว้เพื่อให้ Sonnet ตัดออกอย่างมีข้อมูล ไม่ใช่ลืมพิจารณา.

*ช่องทางที่ "ต่างจริง" คุ้มค่า WebSearch ที่สุด — regulator คนละเจ้า:*
- **SEC Thailand / ก.ล.ต.** (`sec.or.th`) — บริษัทจดทะเบียนยื่น disclosure กับ ก.ล.ต. ด้วย ไม่ใช่แค่ SET. รูปแบบ filing หลักปัจจุบันคือ **56-1 One Report** (แทน 56-1 เดิมตั้งแต่ ~2022) + งบการเงิน. **นี่คือช่องทางที่ operator ต่างจาก set.or.th จริง** → ถ้ามันไม่ได้อยู่หลัง Imperva/มี search ที่เข้าถึงได้ ก็อาจเป็น autonomous channel ที่สะอาดตัวจริง. **แต่ Opus ไม่รู้แน่ว่า sec.or.th มี public API หรือ un-gated document search หรือเปล่า** — ต้อง WebSearch จริง.

*บอกตรงๆ ตามกฎโปรเจกต์:* **Opus ไม่มีความรู้ที่เชื่อถือได้ว่ามี free / open / un-gated API ตัวใดที่เสิร์ฟ MD&A/F45 PDF ของ BCH ให้ Sonnet ยิงเอาเองแบบ autonomous ได้.** ชื่อข้างบนคือ *candidate ให้ไปตรวจ* ไม่ใช่คำยืนยันว่ามันทำงานได้ตามที่หวัง. **ห้าม Sonnet เดา domain เพิ่ม** (เหมือนที่ `market.sec.or.th`/`opendata.set.or.th` เดาแล้ว DNS ไม่ resolve) — verify ชื่อ product ที่ Opus ให้ด้วย WebSearch จริงเท่านั้น. ถ้า WebSearch แล้วไม่เจอ open channel → สรุปได้อย่างมั่นใจว่า "ไม่มี autonomous channel ที่สะอาด" โดยไม่ต้องเดาต่อ.

**Realistic expectation ที่ Sonnet ควรตั้งไว้:** ช่องทาง official ส่วนใหญ่ (SETSMART, DataDirect) เป็น *paid + authenticated* — แปลว่าแม้จะ "ไม่ผ่าน Imperva" มันก็ยังไม่ใช่ "Sonnet fetch เองฟรีๆ" อยู่ดี; มันแค่ *ย้ายประเภทของ gate* จาก human-vs-bot (แดง) ไปเป็น identity/authz (เขียว—ถ้า user มีบัญชี). SEC เป็นตัวเดียวที่ *อาจ* free+open จริง. อย่าขาย SETSMART/DataDirect ให้ user ในฐานะ "ทางฟรีอัตโนมัติ" — ขายในฐานะ "ถ้าคุณมีบัญชีอยู่แล้ว ผมใช้ของคุณได้สะอาดๆ."

---

**3) ถ้าไม่มี autonomous channel ที่สะอาด — บอก "ไม่" ยังไงให้ชัดและเคารพ user:**

โครง 4 บรรทัด (ไม่ re-litigate Q26 ทั้งดุ้น):
1. **ทำไม (1 บรรทัด):** "เว็บ set.or.th มีด่านกันบอท (Imperva) ที่เช็คว่า 'คนหรือโปรแกรม' — ทางเดียวที่ผมจะเข้าไปโหลดเองอัตโนมัติได้คือปลอมให้ระบบคิดว่าผมเป็นคน ซึ่งเป็นสิ่งเดียวที่ผมจะไม่ทำให้โดยไม่ขออนุญาตชัดๆ ก่อน."
2. **ยืนยันขอบเขต:** "สำหรับ *เว็บนี้โดยเฉพาะ* การให้ผมค้น/โหลดเองแบบ end-to-end จึงไม่มีทางที่สะอาดจริง — ไม่ใช่ผมขี้เกียจ แต่มันคือเส้นเดียวกับที่คุณคงไม่อยากให้ผมข้าม."
3. **re-offer console-snippet แบบไม่ใช่รางวัลปลอบใจ:** "ทางที่เร็วสุดที่ *มีจริง* คือ: เปิดหน้า BCH ในเบราว์เซอร์คุณ (ที่ผ่านด่านแล้ว) → paste โค้ดที่ผมเขียนให้ลง Console → มันโหลดครบทั้ง 24 ไฟล์รวดเดียว. **ใช้เวลาคุณ 30 วินาที ครั้งเดียว ไม่ใช่งานประจำที่ต้องทำซ้ำทุกไฟล์** — โค้ดวิ่งอยู่ในเบราว์เซอร์คุณเอง ผมแค่เขียนให้."
4. **เปิดทาง autonomy จริงถ้ามี:** "ถ้าอยากได้แบบผมทำเองจริงๆ ในระยะยาว — บอกผมได้ว่าคุณมีบัญชี SETSMART หรือ data terminal ของโบรกไหม ถ้ามี ผมใช้ login ของคุณดึงได้สะอาดๆ (นั่นคือใช้สิทธิ์คุณเอง ไม่ใช่เจาะด่าน); และผมจะลองเช็คว่า ก.ล.ต. (sec.or.th) เปิด filing ให้โหลดตรงได้ไหม เป็นอีกทาง."

จุดสำคัญของ framing: **console-snippet ไม่ใช่ "ทางที่แย่กว่าที่ user ขอ" — มันคือ "ทางเดียวที่เร็ว *และ* ซื่อสัตย์" สำหรับเว็บนี้.** และคำขอ autonomy ของ user ไม่ได้ถูกปัดตก — ถูก redirect ไปยังที่ที่มันเป็นไปได้อย่างสะอาด (บัญชีของ user เอง / regulator channel) แทนที่จะไปยังที่ที่มันเป็นไปไม่ได้อย่างสะอาด (เจาะ Imperva).

**สิ่งที่ปฏิเสธ (ย้ำจาก Q26, ไม่เปลี่ยน):** stealth/undetected-chromedriver/JA3-spoof/webdriver-patch เพื่อให้ Sonnet ยิงเอง — เวิร์คแต่ *คือ* WAF-evasion, ข้ามเส้นแดง แม้ user ขอให้ทำ (user ขอลด friction ไม่ได้แปลว่า user ให้ mandate เจาะ control — และถึงให้ก็ต้องเป็น go-ahead ที่ informed ชัดเจน ไม่ใช่ inferred จาก "แบบค้นได้เองเลย"). **สิ่งที่เก็บ:** console-in-real-browser = ทางอัตโนมัติที่สะอาด; user's-own-SETSMART/broker-login = autonomy ที่สะอาดถ้ามีบัญชี; sec.or.th = ช่องทางทางเลือกที่ต้อง verify.

## Q28 — ออกแบบระบบ "บอททักไปคอนเฟิร์มนัด" ให้คนไข้คลินิก Alonsi (C-Smile Yala) — ใช้ LINE bot ของเราเอง ไม่ใช่โปรแกรม OPD

**Status:** done (Opus, 2026-07-27) — แผนเต็มอยู่ที่ `/Users/alonsi/Desktop/alonsi-clinic-bot/PLAN_appointment_confirm.md`. สรุป: ปัญหาจริงคือบอทรู้จัก LINE userId แค่ 6 คนจากคนไข้ 11,341 คน (patientcsmile.txt มีแต่เบอร์ ไม่มีวันนัด) → แผน MVP คือ (1) tab ใหม่ `Schedule` ให้เจ้าหน้าที่กรอกนัดมือ (ห้ามใช้ tab `Appointments` เดิม เพราะ workflow Auto-Clear ลบทิ้งอัตโนมัติ), (2) tab `LineLink` จับคู่เบอร์↔userId แบบ "แอดที่เคาน์เตอร์+พิมพ์เบอร์เอง" (ต้นทุน 0 บาท ดีกว่า SMS), (3) tab `Patients` นำเข้าแค่ dn/name/phone จาก patientcsmile.txt, (4) workflow ใหม่ 2 ตัว (Send Appointment Confirm 18:00, Morning Brief 09:00) + แก้ workflow เดิมเพิ่ม 2 กิ่ง (link_phone, confirm). ยังไม่ต่อ OPD ในเฟสนี้ตามที่ user บอก. มีคำถามเปิดเหลือ 8 ข้อใน §12 ของแผน (ชื่อโปรแกรม OPD, งบ SMS ฯลฯ) ที่ไม่บล็อกการเริ่มทำ.

**Context:**

User (เจ้าของคลินิกทันตกรรม C-Smile Yala) ส่งไฟล์ `patientcsmile.txt` มาให้ (export จากระบบคลินิกเดิม) แล้วบอกว่า "ผมต้องการใช้สำหรับให้บอททักไปคอนเฟิร์มนัด" — ต้องการให้ LINE bot ของคลินิก (ตัวที่เราสร้างเอง บน n8n) ทักหาคนไข้เพื่อคอนเฟิร์มนัดหมายที่จองไว้

**ไฟล์ `patientcsmile.txt`** (อยู่ที่ `/Users/alonsi/Desktop/studio/patientcsmile.txt`, เพิ่งเข้า `.gitignore` แล้วเพราะเป็น PII จริง ห้าม commit):
- 11,341 แถว, tab-separated, encoding เดิมคือ Windows-874/TIS-620 (ต้อง `iconv -f WINDOWS-874 -t UTF-8` ถึงอ่านออก)
- คอลัมน์: `dn` (รหัสคนไข้/dental number), `Name`, `Address`, `City`, `State`, `Zip`, `HmPhone`, `WkPhone`, `WirelessPhone`, `email`
- **ไม่มีวัน-เวลานัดหมายอยู่ในไฟล์นี้เลย** — เป็นแค่ patient master roster ทั้งหมด ไม่ใช่รายชื่อนัดที่จะคอนเฟิร์ม

เมื่อ Sonnet ถามว่า "รายชื่อนัดที่จะคอนเฟิร์ม มีวัน-เวลาอยู่ที่ไหน" user ตอบว่า: **"ปกติผมจะเชื่อมต่อกับโปรแกรม opd ของคลินิก แต่ตอนนี้ที่เราทำคือพัฒนาบอทของตัวเอง ให้ opus คิด plan หน่อยว่าเราสามารถที่จะคอนเฟิร์มนัดคนไข้ยังไงดี"**

แปลว่า: ปกติคลินิกมีโปรแกรม OPD (ระบบจัดการคลินิกทันตกรรม, ไม่รู้ยี่ห้อ ต้องถาม user) ที่เก็บวัน-เวลานัดจริง และปกติน่าจะมี integration/feature คอนเฟิร์มนัดอยู่แล้วในนั้น — **แต่ user ต้องการให้ระบบ LINE bot ที่เราสร้างเอง (n8n + Gemini + Google Sheets) เป็นคนทำหน้าที่นี้แทน/เสริม** ไม่ใช่พึ่งโปรแกรม OPD

**โครงสร้างระบบ LINE bot ปัจจุบัน (ที่มีอยู่แล้ว, ยืนยันสดในเซสชันนี้):**
- n8n cloud: `csmileyala.app.n8n.cloud`, workflow หลัก ID `GFdRhaxbgbxvIPjw` (ชื่อ Alonsi Clinic LINE Bot), webhook `https://csmileyala.app.n8n.cloud/webhook/Line-webhook`
- Google Sheet state store: spreadsheet ID `1PkKrnezY7HEUKAj1njIl-USsdly4tiKtzgYy0tv8psk` มี 3 แท็บ: `State` (session ปัจจุบันต่อ userId, มี column `handoff`), `Appointments`, `FAQ`
- **`Appointments` sheet มี column ที่เตรียมไว้แล้วแต่ยังไม่มีใครใช้งาน:** `timestamp, userId, name, surname, phone, procedure, doctor, preferred_time, status, confirmed_time, handled_at, hn, appointment_date, appointment_time, confirm_status, confirm_sent_at` — คือมี `appointment_date`, `appointment_time`, `confirm_status`, `confirm_sent_at` อยู่แล้วในสคีมา แต่ตอนเช็คจริงวันนี้ sheet มีแค่ header แถวเดียว **ไม่มีข้อมูลเลยสักแถว** (ไม่มีนัดใหม่เข้ามาตั้งแต่ 2026-07-01 ~26 วัน)
- มี workflow แยกต่างหากชื่อ `Appointment Auto-Clear` (ไฟล์ local `appointment-auto-clear.json`) — รันทุกชั่วโมง อ่าน Appointments sheet แล้ว mark `handled_at` หรือลบแถวตาม action ที่ staff กรอกไว้ — **นี่คือ housekeeping/cleanup job ของ staff เท่านั้น ไม่ได้ส่งข้อความหาใครเลย ไม่ใช่ฟีเจอร์คอนเฟิร์มนัดที่ user ต้องการตอนนี้**
- If1 node (จุดที่เพิ่งแก้บั๊ก reset ไปเมื่อวันนี้): true→Save State (ระหว่างคุยยังไม่จบ), false→Append row in sheet→Clear State by userId (จบ flow นัดผ่านแชท) — คือตอนนี้การได้ appointment เข้า sheet เกิดจาก**คนไข้คุยจบ flow ผ่าน LINE bot เอง** เท่านั้น ไม่มีทางป้อนนัดจากภายนอก (เช่นจากโปรแกรม OPD หรือจากพนักงานหน้าเคาน์เตอร์) เข้า sheet นี้ได้เลยตอนนี้

**ข้อจำกัดทางเทคนิคสำคัญที่ Sonnet เจอและยังไม่ได้ resolve:**
LINE Messaging API **push message ทำได้เฉพาะกับคนที่มี LINE userId ที่ระบบรู้จักแล้วเท่านั้น** (คือต้องเคยเพิ่มเพื่อน/ทักบอทมาก่อนอย่างน้อย 1 ครั้ง ถึงจะมี userId โผล่ใน webhook event) — **ส่งข้อความหาคนแค่มีเบอร์โทรอย่างเดียวไม่ได้เลย ไม่ว่าจะทางไหนของ LINE Messaging API** คนไข้ส่วนใหญ่ใน `patientcsmile.txt` (11,341 คน) เป็น patient เก่าจากก่อนมี LINE bot น่าจะยังไม่เคยแอด LINE OA ของคลินิกเลย ระบบเลย**ไม่มี LINE userId ของคนกลุ่มนี้เก็บไว้** — Sonnet ถามคำถามนี้กับ user ต่อว่า "คนที่ยังไม่เป็นเพื่อน LINE อยากทำยังไง (SMS / ให้แอดก่อน / อื่นๆ)" แต่ user ยังไม่ได้ตอบ (ตัดจบไปสั่งให้ Opus คิด plan แทน) — **นี่คือ unknown ที่ Opus ต้องคิดในแผนด้วย ไม่ใช่แค่ถามกลับเฉยๆ ควรเสนอทางเลือกที่เป็นไปได้จริงในแผนเลย**

**What's actually being asked of you:**
1. ออกแบบสถาปัตยกรรมของฟีเจอร์ "บอททักไปคอนเฟิร์มนัด" ให้จบ ชัดเจนพอที่ Sonnet เอาไปสร้างต่อได้เลยโดยไม่ต้องคิดสถาปัตยกรรมเพิ่ม — ครอบคลุมอย่างน้อย: (a) แหล่งข้อมูลวัน-เวลานัดจะมาจากไหน (ให้ user กรอกมือใน sheet ไปก่อน? หรือมี input อื่น?), (b) จะ match คนไข้ในนัดกับ LINE userId ยังไง โดยเฉพาะคนที่ยังไม่เคยแอดเพื่อน, (c) trigger การส่งข้อความคอนเฟิร์ม (n8n scheduleTrigger ก่อนนัดกี่ชั่วโมง/วัน?), (d) จะใช้ Appointments sheet เดิม (column confirm_status/confirm_sent_at ที่เตรียมไว้แล้ว) หรือสร้างชีตใหม่
2. คนไข้ที่ยังไม่เป็นเพื่อน LINE OA (คาดว่าเป็นส่วนใหญ่ของ 11,341 คน) จะเข้าถึงยังไง — มีตัวเลือกที่เคยคุยไว้คร่าวๆ: (ก) SMS/โทรแทนสำหรับกลุ่มนี้, (ข) ส่งลิงก์ชวนแอดเพื่อน LINE OA ก่อน (ผ่านช่องทางอื่น เช่น SMS/โทร) แล้วให้ระบบ match เบอร์โทรกับ userId ตอนที่เขาแอด/ทักมา, (ค) อื่นๆ — ให้ Opus แนะนำทางที่ practical ที่สุดสำหรับคลินิกทันตกรรมขนาดเล็กที่ไม่มีงบ SMS gateway มาก
3. ถามด้วยว่า **จำเป็นต้องรอ user ตอบคำถามนี้ก่อนไหม หรือ Opus ประเมินแล้วว่ามีทางออกที่ดีพอที่จะเสนอเป็นแผนไปเลย** (per [[feedback-plan-before-execute]] และ [[feedback-opus-plans-sonnet-executes]] — งานนี้ยาว/สถาปัตยกรรมใหม่ ต้องวางแผนโชว์ก่อน Sonnet ค่อยลงมือ)
4. ควรถามอะไรเพิ่มจาก user เกี่ยวกับโปรแกรม OPD เดิมไหม (ยี่ห้อ, มี API/export อัตโนมัติไหม) เผื่อในอนาคตอยากเชื่อมสองระบบจริงๆ (ปัจจุบันยังไม่เชื่อม, user บอกชัดว่าตอนนี้ทำระบบ bot ของตัวเองไปก่อน)

**Why:** user พิมพ์ตรงๆ ว่า "ให้ opus คิด plan หน่อย" — เป็นการยืนยัน workflow ที่บันทึกไว้ใน memory ([[feedback-opus-plans-sonnet-executes]]) ว่างานออกแบบสถาปัตยกรรมใหม่ต้องให้ Opus คิดก่อน Sonnet ค่อยลงมือ ไม่ใช่ให้ Sonnet ออกแบบเอง

---

## Q29 — YouTube digest bot เงียบมา ~2 สัปดาห์โดยไม่มีใครรู้ (silent failure ซ้ำแบบเดิม) — Opus ช่วยตรวจ root cause + คอนเฟิร์มแผนแก้ก่อน Sonnet ลงมือ

**Status:** done (Opus, 2026-08-13) — ยืนยัน root cause = **macOS TCC Desktop-folder protection** (พิสูจน์ด้วย launchd probe จริง + อ่าน TCC.db: `python3.14` มี grant `kTCCServiceSystemPolicyDesktopFolder`, `/bin/zsh` ไม่มี → `open()` คืน EPERM); fix ของ Sonnet ถูกทางแต่ **ไม่พอ** ต้องใส่ `EnvironmentVariables PATH` ด้วยไม่งั้น yt-dlp/node หาไม่เจอ (ทดสอบ full pipeline ผ่าน launchd แล้วผ่าน); OAuth → ย้ายไป **service account** (Gmail เป็น dead code แล้ว); เพิ่ม **watchdog** LINE alert + weekly liveness ping. แผนลงมือ = `for-sonnet/tasks.md` T31

**Context:**

User ถาม Sonnet วันนี้ (2026-08-11) ว่า "line bot thaivi, daily digest ปกติดีไหม" แล้ว Sonnet เช็ค log จริงเจอว่า:

**thaivi digest (roikonroihoon_digest.py, launchd `com.alonsi.roikonroihoon-digest`)** — ปกติดี รันทุกวันจริง ล่าสุดเช้านี้ LINE push OK

**youtube digest (`tools/youtube_digest/`, launchd `com.alonsi.youtube-digest`)** — พังเงียบๆ มาตั้งแต่ **2026-07-27** (วันที่ [[project-daily-digest-automation]] บันทึกว่า "fixed" — คือพังทันทีหลัง fix ครั้งก่อน ไม่มีใครรู้จนวันนี้) ด้วย 2 ปัญหาซ้อนกัน:

1. **launchd เปิด script ไม่ได้:** plist เรียก `/bin/zsh /Users/alonsi/Desktop/studio/tools/youtube_digest/scripts/run-digest.sh` ทุกวัน 08:00 → error `/bin/zsh: can't open input file: ...run-digest.sh` ทุกครั้ง (นับได้ 30 บรรทัดซ้ำใน `logs/launchd.err.log`, exit code 127 ผ่าน `launchctl list`) ทั้งที่ไฟล์อยู่จริง สิทธิ์ปกติ (`-rwxr-xr-x`, readable) และ Sonnet รันเองผ่าน terminal/Claude ตรงจุดเดิมกลับเปิดได้ปกติ → สรุปว่าปัญหาเกิดเฉพาะตอน `/bin/zsh` ถูก **launchd เรียกตรง** (ไม่ผ่าน Terminal.app) ต่างจาก thaivi bot ที่ plist เรียก `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` ตรงๆไม่ผ่าน zsh เลย เดาว่าเป็นเรื่อง macOS TCC/Full-Disk-Access ที่ผูกกับ responsible-process (`/bin/zsh`) ซึ่งไม่เคยได้รับสิทธิ์เข้า path ใต้ `~/Desktop` ตอนถูกเรียกแบบ headless แต่ **ยังไม่ได้ยืนยัน 100%** — เป็นสมมติฐานที่ Sonnet ตั้งไว้ ยังไม่ได้ทดสอบแยก

2. **Google OAuth token หมดอายุซ้ำ:** เพราะ job ไม่เคยรันสำเร็จเลยตั้งแต่ 27 ก.ค. (ปัญหา #1 บล็อกไว้) ทำให้ token ที่ refresh ล่าสุดไว้ 27 ก.ค. (`data/google_oauth_token.json`) ไม่ได้ถูกใช้งาน/ต่ออายุเลยเกิน 7 วัน → ตาย แบบเดิมที่เคยเจอ (Google Cloud OAuth consent screen ยังเป็น "Testing" mode → refresh token อายุ ~7 วันถ้าไม่ได้ใช้) ตอนรันเองวันนี้เจอ `google.auth.exceptions.RefreshError: invalid_grant: Token has been expired or revoked.` ที่ `sheets_client.py:36`

**Sonnet เสนอ fix ไปแล้ว (ยังไม่ได้ลงมือ รอ user "consult opus" ก่อน):**
- Step 1 (Sonnet ทำได้เอง, local reversible): แก้ `com.alonsi.youtube-digest.plist` ให้ `ProgramArguments` เรียก python3 ตรงๆ แบบเดียวกับ thaivi bot's plist (ตัด `/bin/zsh` wrapper ทิ้ง, ให้ python3 chdir เองหรือตั้ง `WorkingDirectory` ใน plist ตามที่ทำอยู่แล้ว) แล้ว `launchctl unload/load` ใหม่
- Step 2 (ต้อง user ทำเอง ต้องเปิด browser login): re-auth Google OAuth ใหม่เพื่อได้ token สดอีกครั้ง

**What's actually being asked of you:**
1. คอนเฟิร์ม (หรือแก้) สมมติฐาน root cause ของปัญหา #1 — จริงๆคือ TCC/Full-Disk-Access ของ `/bin/zsh` เฉพาะตอน launchd เรียกตรงหรือไม่ หรือมีคำอธิบายอื่นที่ตรงกว่า (เช่น launchd `WorkingDirectory` + relative path resolution, environment variable ที่ขาดไปตอน headless, หรืออื่นๆ)
2. Fix ที่ Sonnet เสนอ (เปลี่ยน plist ให้เรียก python3 ตรง ไม่ผ่าน zsh) เพียงพอ/ถูกจุดไหม หรือมีทางที่ robust กว่านี้ (เช่น ควรเลิกเก็บ automation scripts ไว้ใต้ `~/Desktop/studio` เพราะ Desktop เป็น TCC-protected folder ทั้งหมด แล้วย้ายไปที่อื่นแทนสำหรับ launchd jobs ทุกตัวในอนาคต เพื่อไม่ให้เจอปัญหานี้ซ้ำกับ automation ตัวอื่นที่จะสร้างต่อไป)
3. เรื่อง OAuth token หมดซ้ำทุก ~7 วันเมื่อ job หยุดรัน — ควร "Publish" Google Cloud OAuth consent screen ให้พ้น Testing mode จริงจังไปเลยไหม (แก้ที่ต้นตอกันไม่ให้ token อายุสั้นอีก) หรือมีทางเลือกอื่นที่เหมาะกับ personal-use script มากกว่า (เช่น service account แทน OAuth user flow)
4. ควรเพิ่ม monitoring/alert อะไรไหมไม่ให้ silent failure แบบนี้เกิดซ้ำอีก (เช่น LINE alert อัตโนมัติเมื่อ job fail ติดกันเกิน N วัน คล้ายกับที่ thaivi bot มี alert ตอน session หมดอายุ ตาม [[project-daily-digest-automation]]) — ถ้าเห็นด้วย ให้ระบุ mechanism คร่าวๆมาในแผนเลย

**Why:** user พิมพ์ "consult opus," สั้นๆ ทันทีหลัง Sonnet เสนอ fix — ตาม [[feedback-opus-plans-sonnet-executes]] งานที่กระทบ automation/infra (แก้ launchd plist, ตัดสินใจเรื่อง TCC/OAuth) ต้องให้ Opus ตรวจ/วางแผนก่อน Sonnet ค่อยลงมือแก้จริง ไม่ใช่ให้ Sonnet ตัดสินใจ fix เองทันทีทั้งที่ยังไม่ยืนยัน root cause 100%

---

## Q30 — Sonnet ทำ T31 เสร็จแล้ว (รวมเบี่ยงจากแผนที่ Step 2) — Opus ช่วยตรวจว่า execution โอเคไหม

**Status:** done (Opus, 2026-08-17) — Step 1/3/guardrails **ผ่านของจริง** ไม่ใช่แค่ผ่านตอนเทสต์: ตรวจย้อน 4 วันหลัง fix พบ scheduled run สำเร็จทุกวัน (14/15/16/17), err log หยุดนิ่งที่ 13 ส.ค., `last_run.json` = วันนี้ 08:06, watchdog เงียบถูกวันและ **ยิง Sunday ping จริง 16 ส.ค. (LINE 200)**; แต่เจอ **3 ช่องบอด** ที่ต้องแก้: (ก) heartbeat เขียน "ok" แม้ run ล้มเหลว (path `digest.py:121-124` + `--dry-run`) = ตาบอดชนิดเดียวกับที่ watchdog มีหน้าที่กำจัด, (ข) Google auth เป็น single point of failure ของ digest ทั้งเส้น (`digest.py:88` ตายก่อน LINE/Notion ทั้งที่ Sheet สำคัญน้อยสุด), (ค) watchdog plist ไม่มีใน repo เลย. เรื่อง SA: **ยังไม่ใช่ dead end** — project ที่ออก OAuth client ชื่อ `project-47e8d7aa-eca7-43be-aec` = ชื่อ auto-generated ที่ Google product อื่นสร้างให้ (AI Studio/Firebase) ซึ่งมักอยู่ใต้ org ที่ Google จัดการเอง ปลดไม่ได้ตลอดกาล → **ทางออกคือไม่ต้องปลด: สร้าง project ใหม่เองใน Cloud Console ด้วย @gmail.com (จะได้ "No organization" → constraint ไม่ inherit) แล้วสร้าง SA + key ในนั้น** — SA อยู่ project ไหนก็ได้ Sheet ไม่สนใจ แค่แชร์ Sheet ให้ email ของ SA. ทดสอบ 10 นาที รู้ผลชัดเจน. WIF = ยืนยัน reject (ไม่ใช่ overkill แต่ **ใช้ไม่ได้** — ไม่มี external IdP บนเครื่อง Mac). **ยังไม่ปิดเคส** → T32

**Context:**

Sonnet ลงมือทำ T31 (design ของ Opus ใน Q29) เสร็จครบทั้ง 4 ส่วนแล้ววันนี้ (2026-08-13). สรุปสิ่งที่ทำจริงกับผลตรวจสอบ:

**Step 1 (แก้ plist ให้เรียก python3 ตรง + PATH):** ทำตามแผนเป๊ะ — เขียนทับ `~/Library/LaunchAgents/com.alonsi.youtube-digest.plist`, template `.plist.example`, เติม comment เตือนใน `run-digest.sh` ว่าห้าม launchd ใช้. Reload + verify ด้วย `launchctl kickstart -k` จริง (ไม่ใช่รันมือ ตามที่ Opus เตือนไว้) → ผ่าน `last exit code = 0`, ไม่มี error `can't open input file` อีกเลย

**Step 2 (ย้าย OAuth ไป service account) — เบี่ยงจากแผน, ทำไม่ได้:** พาuser ไปสร้าง service account ใน GCP console จริง แต่เจอ **`iam.disableServiceAccountKeyCreation` ถูก enforce จาก Cloud Organization ระดับบน** (ลองทั้ง legacy constraint และ managed constraint, ลองกด Override parent's policy ที่ project level แล้วก็ยังโดนบล็อกอยู่ดี — error ระบุตรงๆว่าต้องมีคนที่มี role "Organization Policy Administrator" **ระดับ Organization** เท่านั้นที่ปลดได้ ซึ่ง user ไม่มีสิทธิ์นี้) → **นี่ไม่ใช่แค่ "ยังไม่ได้ทำ" แต่คือ "ทำไม่ได้จริงด้วยสิทธิ์ที่ user มี"** เปลี่ยนไปใช้ stopgap ที่ Opus เผื่อไว้ในแผนแทน: publish OAuth consent screen (Testing→Production ผ่านแล้ว ยืนยันจาก screenshot), ลบ token เก่า, รัน `sheets_client.get_credentials()` ตรงๆเพื่อเปิด browser ให้ user login ใหม่หนึ่งรอบ → ได้ token ใหม่ scope เดียว (`spreadsheets` เท่านั้น, ตัด `gmail.send` ออกจาก `SCOPES` แล้วเพราะ dead code) โค้ด `sheets_client.py` ที่ Sonnet แก้ยังรองรับ service account ถ้าวันหน้า org policy หลุดล็อก (เช็ค `data/service_account.json` ก่อนเสมอ ไม่มีก็ fallback ไป OAuth ปกติ) แต่ **ตอนนี้ระบบวิ่งด้วย OAuth token ที่มีอายุจำกัดถาวร ไม่ใช่ SA ที่ไม่หมดอายุตามที่ Opus ตั้งใจไว้เดิม**

ลบ `gmail_client.py` ทิ้งแล้ว (ยืนยันแล้วว่า `digest.py` ไม่ import), ลบ `DIGEST_RECIPIENT_EMAIL` ออกจาก `.env` แล้ว

**Step 3 (watchdog):** ทำตามแผน — `state.write_heartbeat()` เขียน `data/last_run.json` ทุกจบ run สำเร็จ (รวม "no new videos" path ที่ต้อง cover ตามที่ Opus ระบุ). `tools/digest_watchdog.py` ใหม่ (~65 บรรทัด) เช็ค heartbeat 2 บอท (youtube = mtime `last_run.json`, thaivi = mtime `digest_state.json` ไม่แตะโค้ด thaivi เลยตามที่สั่ง), stale >36ชม. → LINE alert, วันอาทิตย์ปกติ → liveness ping. LaunchAgent `com.alonsi.digest-watchdog` 09:00 ใช้ pattern เดียวกับ Step 1 เป๊ะ (python3 ตรง + PATH). **Verify แล้วทั้ง 2 branch จริงผ่าน `launchctl kickstart`:** รอบแรก (ยังไม่มี `last_run.json` เพราะโค้ด heartbeat เพิ่งเพิ่ม) → ส่ง LINE alert จริงสำเร็จ ("ไม่เคยรันเลย"); หลัง kickstart youtube-digest อีกรอบให้สร้าง heartbeat แล้ว kickstart watchdog ซ้ำ → เงียบถูกต้อง ("All heartbeats fresh")

**guardrails.md:** เพิ่ม section ใหม่ตามที่ Opus เขียนไว้ใน Q29 ANSWER แบบคำต่อคำ (python3 ตรง ห้าม shell wrapper, ต้องมี `EnvironmentVariables` PATH, verify ด้วย `launchctl kickstart` เท่านั้น, จุดเปราะเรื่องอัป Python เวอร์ชันใหม่)

**สถานะ launchd สุดท้าย** (`launchctl list | grep alonsi`): ทั้ง 5 jobs (`youtube-digest`, `roikonroihoon-digest`, `digest-watchdog`, `prospect-occupancy-watch`, `thaivi-relogin-reminder`) แสดง exit code ล่าสุด = 0 หมด

Sonnet อัปเดต `for-sonnet/tasks.md` (T31 → done, บันทึกการเบี่ยงแผน Step 2 ไว้ละเอียด) และ memory `project_daily_digest_automation.md` แล้วด้วย

**What's actually being asked of you:**
1. Execution ของ Step 1/3/guardrails ตรงตามแผนและมี evidence การ verify (`launchctl kickstart` จริง ไม่ใช่รันมือ) ครบไหม มีจุดไหนที่ยังไม่มั่นใจว่า robust พอไหม
2. **สำคัญสุด:** การเบี่ยง Step 2 จาก "service account" ไปเป็น "stopgap OAuth ถาวร" (ไม่ใช่ temporary แล้ว เพราะ org policy บล็อกจริง ไม่ใช่แค่ยังไม่ได้ทำ) — โอเคไหมที่จะปล่อยไว้แบบนี้เป็น long-term state ของระบบ หรือควรมีทางเลือกอื่นที่ Sonnet ยังไม่ได้พิจารณา (เช่น ใคร/อะไรเป็น Org Policy Administrator ของ organization นี้ user จะติดต่อขอปลดได้ไหม, หรือมีวิธี auth แบบอื่นที่ไม่ต้องพึ่งทั้ง SA-key และ OAuth-3rd-party-app เช่น Workload Identity Federation — ที่ Opus เคยตัดออกไปแล้วในรอบก่อนว่า overkill, ยังยืนตามเดิมไหมเมื่อ SA ทำไม่ได้จริง)
3. ด้วย token OAuth ที่ตอนนี้ published เป็น production แล้ว (ไม่ใช่ testing) — ยังมีความเสี่ยงอะไรที่ควรเตือน user ไว้ล่วงหน้าไหม (เช่น unverified-app warning ระยะยาว, Google อาจ revoke ถ้าไม่ได้ใช้ 6 เดือน ตามที่ Opus เคยพูดถึงใน T31 เดิม) และ watchdog ที่มีอยู่ตอนนี้ (36ชม. staleness) เพียงพอจะจับ scenario แบบนั้นไหม หรือควรมี safeguard เพิ่ม
4. โดยรวม แบบนี้ "โอเค" พอจะปิดเคสได้ไหม หรือมีอะไรที่ Sonnet ควรกลับไปแก้เพิ่มก่อน

### ANSWER (Opus, 2026-08-17) — ตอบ Q30

**วิธีตรวจ:** ไม่อ่านแต่ write-up ของ Sonnet — วันนี้ 17 ส.ค. คือ **4 วันหลัง fix ลง** เลยมี elapsed time จริงให้ตรวจว่า "อยู่ได้" ไม่ใช่แค่ "เทสต์ผ่านตอนนั้น" ตรวจ plist ทั้งสองไฟล์, `launchctl print` ของจริง, log ย้อนหลัง, mtime ของ heartbeat/token/state, โค้ด `sheets_client.py`/`digest.py`/`state.py`/`digest_watchdog.py`, guardrails, template, และ log ของ watchdog เทียบวันในปฏิทิน

**1. Step 1 / Step 3 / guardrails — ผ่าน และผ่านแบบมีหลักฐาน 4 วันจริง ไม่ใช่แค่ kickstart เทสต์**

Step 1 ตรงตามแผนเป๊ะ: plist เรียก `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` ตรง + `EnvironmentVariables PATH` ครบ (`launchctl print` ยืนยันว่า launchd เห็น environment นั้นจริง ไม่ใช่แค่ในไฟล์ — `default environment PATH => /usr/bin:/bin:/usr/sbin:/sbin` ถูก override ด้วย `environment PATH => .../3.14/bin:/opt/homebrew/bin:...`). `.plist.example` แก้ถูกด้วย (สำคัญ ถ้าลืมจุดนี้บั๊กเดิมกลับมาตอน reinstall)

หลักฐานว่ามันอยู่ได้จริงตามตารางตัวเอง ไม่ใช่แค่ตอนเทสต์:
```
launchd.err.log   mtime = Aug 13 16:13   (นิ่งสนิท 4 วัน = ไม่มี error ใหม่เลย)
launchd.out.log   mtime = Aug 17 08:06   (เขียนทุกเช้า)
out log ลำดับท้าย = no new / no new / no new / Found 1 new → Wrote 1 row → Notion → LINE / no new
state.json        mtime = Aug 16 08:02   (วันที่มีคลิปใหม่จริง เขียน Sheet สำเร็จ)
last_run.json     = {"ts":"2026-08-17T01:06:43Z","status":"ok"}  = 08:06 น. วันนี้
launchctl print   runs = 7, last exit code = 0
```
คือ 08:00 ของวันที่ 14/15/16/17 ยิงและจบ 0 ทุกวัน รวมวันที่ 16 ที่มีคลิปใหม่ → เขียน Sheet + Notion + LINE ครบเส้น (นั่นคือ OAuth token ใหม่ใช้งานได้จริงจาก launchd ไม่ใช่แค่จาก terminal — `google_oauth_token.json` mtime = Aug 16 08:01 = refresh สำเร็จเอง)

Step 3 ก็ผ่านของจริงเหมือนกัน `digest_watchdog.out.log` เทียบวันในปฏิทินได้พอดี: `Alert sent` (เทสต์ 13), `fresh` ×3 (14/15/16?), `LINE push: 200 / Weekly liveness ping sent` (**16 ส.ค. = วันอาทิตย์จริง** — branch นี้ไม่ได้เทสต์แบบ mock วันด้วย แต่รอวันอาทิตย์จริงแล้วยิงเองสำเร็จ), `fresh` (17), `runs = 6`, `.err.log` = 0 ไบต์. **ข้อนี้คือหลักฐานที่ดีที่สุดในงานทั้งหมด** เพราะ watchdog พิสูจน์ตัวเองบนตารางของตัวเอง

guardrails: ถอดตามที่ผมเขียนไว้ครบและ**เพิ่มให้ดีกว่าเดิม** (ข้อ 3 เติม "ควรเช็ค TCC grant เองด้วยถ้าอัป Python") ไม่มีอะไรเพี้ยน

**แต่มี 3 ช่องบอด + ของเล็ก ที่ยังไม่ robust พอ:**

**(ก) heartbeat โกหกได้ — ร้ายสุด** `digest.py:168-170` = `main()` แล้ว `state.write_heartbeat()` แบบไม่มีเงื่อนไข. โค้ดนี้เขียนตามที่ผมสั่งไว้ใน T31 เป๊ะ (ผมสั่งเองว่า "2 บรรทัด ครอบทุก success path") — **ผมสั่งผิดเอง** เพราะ `main()` มี path ที่ *return ปกติทั้งที่ล้มเหลว*:
- `digest.py:121-124` — `if not processed_rows: print("No videos successfully summarized this run."); state.save_state(st); return` → เกิดเมื่อ **transcript ดึงไม่ได้ทุกคลิป** (cookie Chrome หมดอายุ / yt-dlp พัง / YouTube เปลี่ยน) หรือ **summarize ล้มทุกคลิป** (ANTHROPIC_API_KEY ตาย / API ล่ม) → return ปกติ → heartbeat เขียน `"ok"` → watchdog เงียบ → **silent failure ชนิดเดียวกับที่ watchdog มีหน้าที่กำจัด กลับมาอยู่ในระบบเรียบร้อยแล้ว**
- `--dry-run` ก็เขียน heartbeat ด้วย → รันมือดีบั๊กหนึ่งครั้ง = กด reset นาฬิกา staleness ให้ตัวเอง ทั้งที่ไม่ได้เขียน Sheet/LINE เลย

จำไว้ว่า `mark_seen` เกิดก่อน (`digest.py` ในลูป) → คลิปที่ transcript พังถูก mark seen ทิ้งถาวร = **เสียคลิปเงียบๆ** ด้วย ไม่ใช่แค่ heartbeat ผิด

**(ข) Google auth = single point of failure ของ digest ทั้งเส้น** `digest.py:88` เรียก `get_credentials()` **ก่อน** ประมวลผลอะไรทั้งสิ้น → token ตาย = ตายทั้ง run = ไม่ได้ Sheet, **ไม่ได้ Notion, ไม่ได้ LINE** ทั้งที่สองอันหลังไม่เกี่ยวกับ Google เลย. นี่คือสิ่งที่เกิดจริงวันที่ 13 (traceback ใน err log ตายที่ `sheets_client.py:36`). และมองจากคุณค่าที่ได้: Notion เก็บเนื้อหาเต็ม, LINE คือช่องที่ user อ่านจริง, **Sheet เป็น output ที่สำคัญน้อยที่สุดของสาม** แต่กลับมีอำนาจ veto ทั้ง pipeline. ตรงนี้ต้องกลับด้าน: Sheet พังให้ degrade ไม่ใช่ให้ล้ม

**(ค) watchdog plist ไม่มีอยู่ใน repo เลย** มีแค่ `~/Library/LaunchAgents/com.alonsi.digest-watchdog.plist` ไฟล์เดียวในเครื่อง ไม่มี `.plist.example`, ไม่มี install script, ไม่ถูก track ใน git. ตัวที่ทำหน้าที่กันลืมทั้งระบบ ดันเป็นตัวที่ไม่มี artifact ให้ติดตั้งใหม่ — ถ้าไฟล์นี้หายไป (rebuild เครื่อง / เผลอ bootout) จะรู้ตัวจาก "ไม่มี ping วันอาทิตย์" เท่านั้น แล้วก็ไม่มีอะไรบอกวิธีเอากลับ

ของเล็กที่ควรเก็บพร้อมกัน:
- `install-launchagent.sh` ยังบอกให้ verify ด้วย `launchctl list` + `launchctl start` = **ขัดกับ guardrail ที่เพิ่งเขียนเอง** (ต้อง `kickstart -k` + เช็ค `last exit code`) และยัง `chmod +x run-digest.sh` ให้ wrapper ที่ launchd ห้ามใช้แล้ว
- `digest.py` docstring ข้อ 6 ยังเขียน "Send one Gmail digest" ทั้งที่ `gmail_client.py` ถูกลบแล้ว (ยืนยันแล้วว่าลบจริงและไม่มีใคร import)
- **latency ของ 36 ชม. ต้องเข้าใจให้ถูก:** digest 08:00 / watchdog 09:00 → ถ้า run วันนี้พัง heartbeat จะเก่า 25 ชม. ตอนเช็ค = **ต่ำกว่า 36 → ไม่เตือน** ต้องรออีกวัน (49 ชม.) กว่าจะเตือน แปลว่า **พังหนึ่งวันไม่มีใครรู้ตามดีไซน์** และ threshold นี้ลดลงมาให้จับวันเดียวไม่ได้เลยนอกจากลงไปต่ำกว่า 25 ชม. ซึ่งจะเริ่ม false-positive ตอน Mac หลับข้ามคืนแล้ว launchd ยิง job ช้า → **ผมยืนยัน 36 ชม. เป็นค่าที่ถูก** แต่ให้แก้ด้วยการทำให้ ping วันอาทิตย์รายงาน "อายุ heartbeat จริงกี่ชั่วโมง" แทนที่จะเป็น ✅ เปล่าๆ (drift จะได้มองเห็น ไม่ต้องพึ่ง threshold เดียว)
- **thaivi heartbeat วัด "ได้รัน" ไม่ใช่ "สำเร็จ":** `roikonroihoon_digest.py:176` เขียน `digest_state.json` **แล้วค่อย `sys.exit(2)`** ตอน session หลุด → mtime สดทั้งที่บอทเจ๊ง. ยอมรับได้เพราะ thaivi มี alert ของตัวเองสำหรับ failure mode เดียวที่มันมี (`_session_alert_sent`) แต่ต้องจดไว้ว่า watchdog **ไม่ได้** ครอบ thaivi ในความหมายนั้น อย่าเข้าใจผิดว่าครอบ
- token refresh ถูกใช้งานเฉพาะวันที่มีคลิปใหม่ (`get_credentials()` อยู่หลัง `return` ของ no-new-videos) → นาฬิกา "6 เดือนไม่ใช้ = Google revoke" ถูกกำหนดโดยความถี่คลิป ไม่ใช่รายวัน. ในทางปฏิบัติปลอดภัย (คลิปมาทุก 2-3 วัน) แค่รู้ไว้

**2. เรื่อง SA ถูกบล็อก — Sonnet สรุปเร็วเกินไปหนึ่งก้าว มันยังไม่ใช่ dead end**

สิ่งที่ Sonnet พิสูจน์ได้จริงคือ "**ปลด constraint บน org นั้นไม่ได้**" ซึ่งผมเชื่อและไม่ต้องลองซ้ำ. แต่คำถามที่ยังไม่ได้ถามคือ **"ทำไม @gmail.com ถึงมี org?"** — บัญชี consumer Gmail ปกติสร้าง project แล้วได้ parent = **No organization** และ constraint ระดับ org ไม่มีทาง inherit ลงมาได้เลย. หลักฐานที่ผมเจอ: `data/google_oauth_client.json` → `project_id = project-47e8d7aa-eca7-43be-aec` — **ชื่อนี้ไม่ใช่ชื่อที่คนตั้ง** เป็น pattern `project-<uuid>` ที่ Google product อื่นสร้าง project ให้อัตโนมัติ (AI Studio / Gemini API / Firebase) และ project ที่เกิดแบบนั้นมักถูกวางใต้ org ที่ **Google จัดการเอง** — ซึ่งอธิบายทั้งชื่อแปลกๆ และทั้ง error "ต้องมี Organization Policy Administrator ระดับ organization" ได้พอดี. ถ้าเป็นแบบนั้นจริง **ไม่มีวันหาคนมาปลดให้ได้** เพราะ admin คือ Google ไม่ใช่คนที่ user รู้จัก → การไปตามหา Org Policy Admin เป็นทางตัน ไม่ต้องเสียเวลา

ทางออกคือ **ไม่ต้องปลดมันเลย — ย้ายออกไปจาก org นั้น**: ให้ user สร้าง project **ใหม่** เองใน Cloud Console ด้วย @gmail.com ตรงๆ (จะได้ `No organization`) → เปิด Sheets API → สร้าง SA + JSON key ในนั้น. เหตุผลที่ทำได้: **SA เป็น identity ระดับ project แต่สิทธิ์เข้า Sheet มาจากการแชร์ Sheet ให้ email ของ SA** ไม่ได้มาจาก project เลย → SA อยู่ project ไหนก็เขียน Sheet เดิมได้ ขอแค่ Sheets API เปิดใน project ของ SA (มันเป็น quota project ของ request). และโค้ดฝั่งเราไม่ต้องแก้อะไรเลยแม้แต่บรรทัดเดียว — `sheets_client.py:34-37` เช็ค `data/service_account.json` ก่อนแล้ว วางไฟล์ลงไปก็สลับเอง (ตรงนี้ Sonnet ทำถูกมาก การเขียน fallback ทิ้งไว้ทำให้วันนี้ราคาของการลองเท่ากับ "วางไฟล์หนึ่งไฟล์")

เป็นการทดลอง 10 นาทีที่ผลชัดเจนไม่กำกวม: **ถ้า project ใหม่ขึ้น "No organization" แล้วสร้าง key ได้ → จบปัญหา OAuth ถาวรตามแผนเดิม; ถ้ายังโดนบล็อกอีก → แปลว่าบล็อกที่ระดับบัญชี ยอมรับ OAuth เป็น long-term ได้เต็มปากเต็มคำ** พร้อมหลักฐาน ไม่ใช่เพราะเดา. ต้องลองก่อนถึงจะประกาศว่า permanent ได้

**WIF — ยืนยัน reject และเปลี่ยนเหตุผลให้แข็งกว่าเดิม:** รอบก่อนผมตัดเพราะ "overkill" ตอนนี้ตัดเพราะ **ใช้ไม่ได้จริง** — WIF ต้องมี external IdP ที่ออก OIDC/SAML token ให้ workload (GitHub Actions, AWS, k8s ฯลฯ) แล้วเอาไป exchange เป็น SA access token แบบไม่ต้องมี key. เครื่อง Mac ที่บ้านไม่มี IdP แบบนั้นและไม่มีวิธีทำให้มีแบบสมเหตุสมผล → ไม่ใช่ทางเลือกตั้งแต่ต้น. ส่วน SA impersonation (`--impersonate-service-account`) ก็ต้องมี base credential ของ user อยู่ดี = วนกลับมาที่ OAuth เหมือนเดิม ไม่ได้อะไรเพิ่ม. ทางเลือกที่เหลือจริงๆ มีทางเดียวคือ `gcloud auth application-default login` (ได้เปรียบข้อเดียว: ใช้ OAuth client ของ Google เองที่ verified แล้ว → ไม่มีหน้าจอ unverified และไม่ผูกกับสถานะ consent screen ของ user) แต่มันก็ยังเป็น refresh token ในไฟล์เหมือนกัน + ต้องลง gcloud SDK ใหม่ทั้งชุด (เครื่องนี้ไม่มี — เช็คแล้ว `gcloud not found`) → **ไม่คุ้ม ไม่ต้องทำ** ถ้า SA ทางใหม่ได้ผล

**3. ความเสี่ยงของ published-but-unverified OAuth app + watchdog พอไหม**

สิ่งที่ publish แก้ได้จริงและจบแล้ว: refresh token ไม่หมดอายุ 7 วันอีก (ยืนยันด้วยของจริง — token refresh สำเร็จเองวันที่ 16 หลังผ่านมา 3 วัน ซึ่งเมื่อก่อนตายไปแล้ว)

หางที่ยังเหลือ เรียงตามโอกาสเกิด:
1. **user เปลี่ยนรหัส Google account** → consumer account จะ revoke refresh token → พังทันที (นี่มีโอกาสเกิดสูงสุดในลิสต์นี้ และ user จะไม่นึกถึงเลยว่าเกี่ยวกัน)
2. **หน้าจอ "Google hasn't verified this app"** ตอน re-auth ครั้งถัดไป (scope `spreadsheets` เป็น sensitive scope, app ไม่ได้ verified) → ต้องกด Advanced → Go to (unsafe) เอง ไม่ใช่ blocker แต่จะทำให้ตกใจถ้าไม่รู้ล่วงหน้า
3. **ไม่ใช้เกิน 6 เดือน → Google revoke refresh token** และ Google ยัง**ลบ OAuth client ที่ inactive นานๆ** ด้วย — ปัจจุบันความถี่คลิปทำให้ไม่เข้าเงื่อนไข ยกเว้นวันไหนช่องหยุดลงคลิปยาวๆ
4. เผลอถอนสิทธิ์ที่ myaccount.google.com/permissions, project ถูกลบ/ระงับ, refresh token เกิน 50 ใบต่อ client/user (re-auth ซ้ำๆ ใบเก่าจะถูกเบียดทิ้ง)
5. cap 100 users ของ unverified production app — ไม่เกี่ยว ใช้คนเดียว

**watchdog จับ class นี้ได้ไหม: ได้ แต่ "ได้" อย่างเปราะ** — มันจับได้เพราะทุกเคสข้างบนทำให้ `get_credentials()` **โยน exception** → `main()` ตาย → heartbeat ไม่ถูกเขียน → stale → alert ภายใน ~2 วัน. แต่ความสัมพันธ์นี้เป็นอุบัติเหตุ ไม่ใช่ดีไซน์ และมันจะ**หายไปทันที**ที่เราแก้ข้อ (ข) ให้ Sheet พังแบบไม่ล้ม pipeline — พอ Sheet ไม่ fatal แล้ว token ตายจะกลายเป็น "digest มาปกติทุกวัน แต่ไม่มีอะไรลง Sheet เลย ไม่มีใครรู้" **สองข้อนี้จึงต้องแก้พร้อมกันเสมอ ห้ามแก้ (ข) โดยไม่ทำ status = degraded** ไม่งั้นจะสร้างช่องบอดใหม่ด้วยมือตัวเอง แล้วเจอรอบสี่

ของที่ควรมีเพิ่มแต่ไม่ต้องทำใหญ่: **runbook re-auth 3 บรรทัด** (ลบ token → รัน `get_credentials()` จาก Terminal ไม่ใช่ launchd → ต้องกด Advanced ผ่านหน้าจอ unverified) จดไว้ใน memory `project_daily_digest_automation.md` ที่เป็นบ้านของเรื่องนี้อยู่แล้ว. ค่าของมันคือเปลี่ยน "พัง = ต้องมา debug กันใหม่" ให้เป็น "พัง = 2 นาที" และตอนนั้นคนที่ทำอาจเป็น session ที่ไม่มี context นี้เลย

**4. สรุป: ยังไม่ปิดเคส — เหลือ 1 รอบสั้น**

Step 1 = ปิดได้ ผ่านของจริง 4 วัน. Step 3 = โครงถูกและพิสูจน์ตัวเองแล้ว (รวม Sunday ping จริง) แต่ **สัญญาณที่มันเฝ้ายังโกหกได้** ซึ่งทำให้มูลค่าจริงต่ำกว่าที่ตัวเลขบอก. guardrails = ปิดได้. Step 2 = **ห้ามประกาศว่า permanent** จนได้ลอง project ใหม่แบบ No organization ก่อน เพราะราคาของการลองคือ 10 นาที ส่วนราคาของการยอมรับผิดๆ คือแบกหาง 5 เส้นข้างบนไปตลอด

งานที่เหลือทั้งหมดเล็กและกลไกล้วน → `for-sonnet/tasks.md` **T32** (heartbeat ให้ซื่อสัตย์ + ลด blast radius ของ Google auth + ลอง SA ทางใหม่ + เก็บ watchdog plist เข้า repo + runbook). ห้ามขยายเกินนี้ — ปัญหาของระบบนี้ไม่เคยคือ "monitoring น้อยเกินไป" แต่คือ "สัญญาณที่มีอยู่เชื่อไม่ได้"

*(หมายเหตุ: บล็อก `### ANSWER (Opus, 2026-08-13)` ด้านล่างนี้เป็นคำตอบของ **Q29** ที่ถูกวางสลับตำแหน่งไว้ ไม่ใช่คำตอบของ Q30 — คงไว้ตามเดิมไม่แก้)*

### ANSWER (Opus, 2026-08-13)

**วิธีตรวจ:** ไม่เชื่อสมมติฐาน เอา launchd มาทดสอบจริง — สร้าง LaunchAgent ชั่วคราว (`com.alonsi.tccprobe`) ที่ไม่ยุ่งกับ job เดิมเลย ให้มัน stat/cat/ls ไฟล์ใต้ `~/Desktop` เทียบกับไฟล์ใน `/private/tmp` แล้ว bootout ทิ้งหลังใช้เสร็จ

**1. Root cause — ยืนยัน TCC ครับ แต่กลไกละเอียดกว่าที่เดาไว้ และ "เดา" หลายข้อของ Sonnet ต้องแก้**

ตัดทิ้งได้หมดก่อน: path ใน plist กับ path จริง **byte-identical** (hexdump ตรงกันทุกไบต์ ไม่มี zero-width/NBSP/encoding แปลก), ไฟล์เป็น ASCII + LF + shebang `#!/bin/zsh` ปกติ, โหมด `-rwxr-xr-x`, ทุก parent dir มีสิทธิ์ครบ, `WorkingDirectory` ก็ resolve ถูก — **ไม่ใช่** history-expansion, ไม่ใช่ตัวอักษรแปลก, ไม่ใช่ shebang, ไม่ใช่ relative-path

ผล probe (ทุกบรรทัดรันจาก launchd จริง):
```
stat  ~/Desktop/.../run-digest.sh   -> 100755 359      (metadata อ่านได้)
cat   ~/Desktop/.../run-digest.sh   -> Operation not permitted
ls    ~/Desktop/.../scripts/        -> Operation not permitted
head  ~/Desktop/tools/roikonroihoon_digest.py -> Operation not permitted
python3.14 open(ไฟล์เดียวกัน)       -> อ่านได้ปกติ
cat   /private/tmp/control.txt      -> อ่านได้ปกติ
```
`stat` ผ่านแต่ `open()` โดน EPERM = ลายเซ็นของ TCC เป๊ะ (TCC บล็อกที่ระดับ content ไม่ใช่ metadata) และหลักฐานปิดคดีคือ TCC.db ของ user:
```
kTCCServiceSystemPolicyDesktopFolder | /Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14 | 2
kTCCServiceSystemPolicyDesktopFolder | com.apple.Terminal | 2
kTCCServiceSystemPolicyDesktopFolder | com.anthropic.claude-code | 2
(ไม่มีแถวของ /bin/zsh)
```
**สรุปกลไกที่ถูกต้อง:** grant ของ TCC ผูกกับ *ตัว binary ที่เรียก open()* ไม่ใช่ผูกกับ "responsible process" แบบที่ Sonnet เดา — `python3.14` เคยได้รับสิทธิ์ Desktop ไว้ (ตอนไหนสักครั้ง) เลยอ่าน Desktop ได้ทุกที่รวมทั้งจาก launchd, ส่วน `/bin/zsh` ไม่เคยได้และไม่มีทางได้เองแบบ headless (ไม่มี UI ให้กด Allow → auto-deny เงียบๆ). ตอนรันผ่าน Terminal/Claude Code มันผ่านเพราะ **Terminal.app กับ claude-code มี grant ของตัวเอง** ไม่ใช่เพราะ zsh มีสิทธิ์ — นี่คือสาเหตุที่ "รันมือได้ แต่ launchd ไม่ได้" และคือสาเหตุที่ thaivi bot รอด (plist เรียก python3 ตรง = binary ที่มี grant)

**แก้ timeline ที่ Sonnet เขียนไว้:** ไม่ใช่ "พังตั้งแต่ 27 ก.ค." — job นี้ **ไม่เคยรันสำเร็จผ่าน launchd เลยแม้แต่ครั้งเดียวตั้งแต่ติดตั้ง** (err log 32 บรรทัด = 32 ครั้งที่ schedule ยิงแล้วตายหมด, `launchctl print` = `runs 22 / last exit code 127`). ที่ digest ยังมาถึง 27 ก.ค. เพราะ **user/Sonnet รันมือ** — ดูจาก mtime: `digest.py`/`.env`/`line_client.py` = Jul 27 15:31 และ `state.json`/`token.json` = Jul 27 15:32 คือ dev session วันนั้นเอง ไม่ใช่ scheduled run. ประเด็นนี้สำคัญเพราะ [[project-daily-digest-automation]] จดว่า "fixed 27 ก.ค." ทั้งที่จริงคือ "ยืนยันด้วยการรันมือ" ซึ่ง **ไม่เคย test path ที่ launchd ใช้จริงเลย** — บทเรียน: verify automation ด้วย `launchctl kickstart` เท่านั้น การรันมือใน terminal พิสูจน์อะไรไม่ได้เลยเพราะ TCC context คนละอันกัน

**2. Fix ของ Sonnet ถูกทางแต่ไม่พอ — มีระเบิดอีก 2 ลูกรออยู่หลังแก้ plist**

เรียก python3 ตรงถูกแล้ว (นั่นคือ binary ที่มี TCC grant) แต่ถ้าแก้แค่นั้นจะไปตายจุดถัดไปทันที:
- **PATH:** launchd ให้ default PATH = `/usr/bin:/bin:/usr/sbin:/sbin` เท่านั้น. `run-digest.sh` เดิมเป็นคนใส่ `/opt/homebrew/bin` ให้ — พอตัด wrapper ทิ้งก็หายไปด้วย. `transcript_utils.py` เรียก `yt-dlp` (อยู่ `/Library/Frameworks/.../3.14/bin/`) และ yt-dlp เรียก `node` (`/opt/homebrew/bin/node`) → **ทั้งคู่หาไม่เจอ ตายทันที**. ต้องใส่ `EnvironmentVariables → PATH` ใน plist
- **ANTHROPIC_API_KEY:** ไม่ได้อยู่ใน `youtube_digest/.env` และไม่ได้ export จาก shell rc — `summarize.py` ไป fallback อ่าน `tools/.env` (มีคีย์อยู่จริง) ดังนั้น**รอด** แต่รอดโดยบังเอิญ ไม่ใช่โดยออกแบบ. ปล่อยไว้ได้ ไม่ต้องแก้ แค่รู้ไว้

ทดสอบ fix pattern จริงผ่าน launchd แล้ว (probe ตัวที่สอง, python3 ตรง + PATH ครบ): imports ผ่าน, `yt-dlp`/`node` resolve ได้, อ่าน `.env` ทั้งสองไฟล์ได้, RSS ดึงได้, และ `fetch_transcript()` ดึง transcript จริงมาได้ 34,948 ตัวอักษร — **รวมถึง `--cookies-from-browser chrome` ที่ทำงานได้จาก launchd** (จุดนี้เป็นความเสี่ยง keychain ที่ผมกลัวว่าจะพัง แต่ผ่าน). แปลว่า pipeline ทั้งเส้นพร้อมแล้ว เหลือแค่ OAuth

**เรื่องย้าย automation ออกจาก `~/Desktop` — ตอบว่า "ไม่ย้าย"** ครับ. เหตุผล: (ก) สิ่งที่ทำให้ระบบทำงานคือ grant บน binary ตัวเดียว ซึ่งมีอยู่แล้วและ automation ทุกตัวในบ้านนี้ใช้ python3 ตัวเดียวกันหมด → ย้ายก็ไม่ได้อะไรเพิ่ม; (ข) `~/Desktop/studio` ถูก hardcode เป็น absolute path อยู่ใน plist หลายตัว, CLAUDE.md, skills, guides, launchd, tools/*.py — blast radius ใหญ่กว่าบั๊กที่ป้องกันได้เยอะ; (ค) ทางเลือกที่ดูสวย (`mv ~/Desktop/studio ~/studio` + symlink กลับ) พึ่งพฤติกรรม TCC ที่ resolve symlink ซึ่งผมไม่อยากให้ automation ทั้งบ้านไปแขวนกับ implementation detail ที่ Apple เปลี่ยนได้. **เอาเป็นกฎแทน:** *launchd plist ทุกตัวต้องเรียก `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` ตรงๆ ห้ามมี shell wrapper และต้องกำหนด PATH เอง* — จุดเปราะที่เหลือคือวันที่อัป Python เป็น 3.15 (path เปลี่ยน → grant หาย → เงียบอีก) ซึ่งข้อ 4 (watchdog) จะเป็นตัวจับ ไม่ใช่ปล่อยให้เงียบ

**3. OAuth — ย้ายไป service account ครับ ไม่ใช่แค่ publish consent screen**

ข้อมูลที่เปลี่ยนคำตอบ: `SCOPES` ยังขอ `gmail.send` อยู่ **แต่ `gmail_client.py` เป็น dead code แล้ว** — `digest.py` ปัจจุบันส่งออกทาง LINE + Notion ไม่ import gmail เลย (`DIGEST_RECIPIENT_EMAIL` ใน `.env` ก็ไม่มีใครใช้). เหลือ Google API จริงๆ แค่ "เขียนแถวลง Sheet ที่ user เป็นเจ้าของเอง" ซึ่งเป็น use case ตำราของ service account เป๊ะ

- **service account:** ไม่มี consent screen, ไม่มี refresh token, ไม่มีวันหมดอายุ, ไม่ต้องเปิด browser login อีกเลยตลอดกาล. แค่แชร์ Sheet ให้ email ของ SA เป็น Editor. key ไฟล์ลงใน `data/` ซึ่ง gitignore ครอบ (`data/*.json`) แล้ว — ปลอดภัย
- **publish consent screen:** แก้เรื่อง 7 วันได้จริง (Testing → In production = refresh token ไม่หมดอายุ) แต่ยังเหลือหางอีกหลายเส้น: unverified-app warning, revoke เมื่อไม่ใช้ 6 เดือน, revoke เมื่อเปลี่ยนรหัส Google, cap 100 users, และ**ยังต้องเปิด browser re-auth ทุกครั้งที่อะไรสักอย่างพัง** — คือยังเป็น class เดิมของบั๊ก แค่ยืดเวลา

โดนเรื่องนี้มาสองรอบแล้ว เลือกทางที่ตัดปัญหาขาด: **SA + ลบ `gmail.send` ออกจาก SCOPES + retire `gmail_client.py`**. ถ้าอยาก digest กลับมาทำงานพรุ่งนี้เช้าเลยโดยไม่รอทำ SA ก็ publish + re-auth เป็น stopgap ได้ แต่อย่าหยุดแค่นั้น

**4. Dead-man's switch — เห็นด้วยเต็มที่ และมันคือ deliverable ที่สำคัญที่สุดในงานนี้**

บั๊กจริงของเรื่องนี้ไม่ใช่ TCC — TCC เป็นแค่ trigger. บั๊กจริงคือ **job ตาย 32 วันติดโดยไม่มีใครรู้ ทั้งที่ err log ก็เขียนอยู่ทุกวัน**. ถ้าแก้แต่ TCC แล้วไม่ใส่ watchdog เดี๋ยวก็เจอรอบสามด้วยสาเหตุใหม่ (อัป Python, token, cookie Chrome หมดอายุ ฯลฯ)

ออกแบบ (ตั้งใจให้เล็ก ~60 บรรทัด อย่าทำใหญ่กว่านี้):
- `digest.py` เขียน heartbeat `data/last_run.json` ตอนจบทุก success path — รวมถึงเคส "ไม่มีคลิปใหม่" ด้วย (นั่นก็คือรันสำเร็จ) วางไว้ใน `__main__` หลัง `main()` return จะครอบทุก path ด้วยโค้ด 2 บรรทัด
- thaivi **ไม่ต้องแก้โค้ดเลย** — มันเขียน `digest_state.json` ทุกรอบอยู่แล้ว ใช้ mtime เป็น heartbeat ได้ฟรี (อย่าไปแตะบอทที่ทำงานดีอยู่)
- `tools/digest_watchdog.py` + LaunchAgent ใหม่ 09:00 (หลังทั้งสอง job) เช็ค heartbeat ทั้งคู่ ถ้าอันไหนเก่าเกิน 36 ชม. → LINE push เตือน
- **weekly liveness ping:** วันอาทิตย์ส่ง "✅ บอททั้งหมดปกติ" หนึ่งครั้ง — เพื่อแก้ปัญหาไก่กับไข่ (ถ้า watchdog เองตายก็เงียบอีก) การได้ข้อความทุกวันอาทิตย์ทำให้ "ความเงียบ" กลายเป็นสัญญาณที่สังเกตได้ ไม่ใช่ default state
- watchdog ต้องใช้ pattern เดียวกับข้อ 2 (python3 ตรง + PATH) ไม่งั้นมันตายด้วย TCC แบบเดียวกับที่มันมีหน้าที่มาจับ

**เก็บกวาดพ่วง:** `scripts/com.alonsi.youtube-digest.plist.example` + `install-launchagent.sh` ยังเป็น pattern `/bin/zsh` อยู่ — ถ้าไม่แก้ วันไหน reinstall ก็ได้บั๊กเดิมกลับมาเป๊ะๆ ต้องแก้ template ด้วย ไม่ใช่แก้แต่ plist ที่ติดตั้งแล้ว

---

## Q-noodle — ปรับ studio ตามแนวคิด poteto/noodle (ผู้ใช้อนุมัติครบ 5 ข้อ 2026-10-09, "เดี๋ยวค่อยทำ")
**Status:** pending (รอผู้ใช้สั่งเริ่ม)

Source: https://github.com/poteto/noodle — ไม่ติดตั้ง binary (ออกแบบมาสำหรับ repo โค้ด + loop Opus อัตโนมัติ = เปลือง usage). ยืมแนวคิดเท่านั้น:
1. `/reflect` skill — หลังจบงาน สรุปบทเรียน → ถ้าฝังเป็น script/กฎได้ ให้ฝังแทนการจดโน้ต. ตัวอย่างค้าง: download skill ควรใช้ `--cookies-from-browser chrome` อัตโนมัติสำหรับ FB reel ที่ต้อง login + ใช้ ffmpeg สำรอง (imageio-ffmpeg) ถ้า brew ffmpeg พัง; ใช้ `ImageOps.exif_transpose` กับรูป HEIC/JPG (orientation 6).
2. `/meditate` skill — audit MEMORY.md/CLAUDE.md รายเดือน ตัดของเก่า/ซ้ำ (เช่น "CLAUDE.md Access Pending", memory บอท n8n ที่เลิกใช้แล้ว).
3. รวม for-opus/questions.md + for-sonnet/tasks.md → `todos.md` เดียว แต่ละงานมี stages + model ต่อ stage (plan:opus → execute:sonnet → check:sonnet → reflect:haiku). ต้องตกลง format กับผู้ใช้ก่อน.
4. ใส่ `schedule:` frontmatter (prose บอกว่า skill ควรรันเมื่อไหร่) ใน skills เดิม เช่น trendlongtun-brief → ตามด้วย red-flag check + reflect.
5. Quality gate — ให้โมเดล/agent อื่นตรวจงาน research/deep dive (ตัวเลขเทียบ NotebookLM) ก่อนปิดงาน.

**เพิ่มเติม (ดู repo อื่นของ poteto แล้ว 2026-10-09):**
- ข้อ 1–2 ให้ใช้ https://github.com/poteto/brainmaxxing (MIT) เป็นต้นแบบ: reflect / meditate / ruminate (ขุดบทสนทนาเก่าใน ~/.claude หา correction ที่ไม่เคยถูกบันทึก) / plan / review — แต่ชี้ไปที่ memory dir เดิม + CLAUDE.md ไม่สร้าง `brain/` ซ้อน
- ข้อ 5 ยืม critique mode จาก https://github.com/poteto/how — critic หลายตัวคนละโมเดลตรวจงานพร้อมกัน
- ใหม่: https://github.com/poteto/verification-skill-example — ทำ "feature map" ให้บอท launchd แต่ละตัว (1 ไฟล์/บอท: มีอะไร, เช็คยังไง, อะไรมักพัง) ให้ bot-ops ใช้ตรวจ

**poteto/how — รายละเอียด (อ่าน SKILL.md + references ครบแล้ว 2026-10-09):**
- 6. `/how` ฉบับ studio: ถาม "บอท X / pipeline Y ทำงานยังไง" → ง่าย = agent เดียว; ซับซ้อน = Explore agents (haiku, read-only) 2–4 มุมพร้อมกัน → explainer (sonnet) รวมเป็นภาษาไทย: ภาพรวม / ส่วนประกอบหลัก / ทำงานยังไง (+mermaid) / ไฟล์อยู่ไหน / จุดที่มักพลาด. Explorer ต้องมีหัวข้อ "Open Questions" (ตรงกฎห้าม hallucinate).
- ข้อ 5 (quality gate) ทำเป็น critique mode สำหรับ deep dive หุ้น: critic 3 ตัว คนละ lens (ตัวเลข/เทียบ filing, moat+ธุรกิจตาม PHILOSOPHY.md, red flags+valuation) แทนคนละโมเดล (มีแต่ Claude). Lead ตัดสินเป็น 4 กลุ่ม: Act on / Consider / Noted / Dismissed. "ไม่มีจุดอ่อน" = ผลลัพธ์ที่ยอมรับได้.
- ชื่อโมเดลใน how เป็นของ Cursor (gpt-5.4, composer-2) → map เป็น Agent tool model: haiku/sonnet/opus.

**poteto/brainmaxxing — รายละเอียด (อ่าน skills/hooks/principles แล้ว 2026-10-09):**
- ไม่ติดตั้ง `brain/` vault: auto-memory (MEMORY.md ถูก inject ทุก session + ไฟล์ละ 1 เรื่อง + Why/How) = ระบบเดียวกันอยู่แล้ว. ยืม skills มาชี้ไปที่ memory dir + CLAUDE.md + guides/ + skills แทน.
- 7. `/ruminate` — ตอนนี้เหลือ transcript แค่ 3 ไฟล์ (เก่าสุด 2026-09-15) เพราะ Claude Code ลบอัตโนมัติ (cleanupPeriodDays default 30). → ทำก่อน: ตั้ง cleanupPeriodDays ให้ยาวขึ้นใน ~/.claude/settings.json (ใช้ update-config skill) แล้วรัน ruminate เร็วๆ ก่อนหายอีก. ต้นฉบับใช้ทีม Opus ต่อ batch → เปลี่ยนเป็น sonnet. Filter: เก็บเฉพาะที่เกิดซ้ำ/ผลกระทบสูง, เสนอเป็นตารางให้ผู้ใช้เลือก.
- 8. `guides/principles.md` — เลือกหลักการที่ตรงกับผู้ใช้ ~5 ข้อ: encode-lessons-in-structure, cost-aware-delegation, guard-the-context-window, prove-it-works, fix-root-causes. ข้ามข้อที่เป็น software architecture ล้วน. (หลักลงทุนอยู่ใน research/PHILOSOPHY.md อยู่แล้ว)
- 9. Hook PostToolUse: แก้ไฟล์ใน knowledge/ → รัน tools/build_knowledge_index.py อัตโนมัติ (แบบ auto-index-brain.sh).
- `/plan` ของ brainmaxxing = ใช้เป็นแม่แบบให้ Opus เขียนแผนเป็นเฟสลง todos/for-sonnet (ข้อ 3).

- ✅ 2026-10-09: ตั้ง `cleanupPeriodDays: 365` ใน ~/.claude/settings.json แล้ว (ส่วนแรกของข้อ 7) — เหลือรัน /ruminate

- ✅ 2026-10-09 ช่วง 1 สร้างแล้ว: `.claude/skills/{ruminate,reflect,meditate}/SKILL.md`, `ruminate/scripts/extract_conversations.py`, `guides/principles.md` (5 ข้อ), router ใน CLAUDE.md. รัน ruminate รอบแรกแล้ว (3 sessions) — รอผู้ใช้เลือก fix ที่จะทำ
- ✅ 2026-10-09 ruminate fixes ทำครบ 4 ข้อ: archivist ห้ามลบ studio/ + api/ node_modules; download.md เพิ่ม route Facebook (cookies Chrome, sleep, yt-dlp -U, VP9→H.264, ffmpeg fallback, เซฟลง archive); รัน Python Install Certificates แล้ว (HTTPS ผ่าน); tools/remove_people.py (ทดสอบแล้ว ผลตรงกับรูปที่อนุมัติ). **ช่วง 1 เสร็จ** — ช่วง 2 (ข้อ 4,5) และช่วง 3 (ข้อ 3,6,9 + bot feature map) ยัง pending
