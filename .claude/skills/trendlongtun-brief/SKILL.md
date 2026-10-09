---
name: trendlongtun-brief
description: >-
  Write an in-depth, deep-dive business/stock analysis article in a casual
  Business / Investor style, OUTPUT IN THAI. Use whenever the user asks to
  "write a deep dive on [company/ticker]", "เขียนบทวิเคราะห์เจาะลึก [หุ้น]",
  "วิเคราะห์ธุรกิจ [บริษัท]", "Trendlongtun brief", "ทำ brief หุ้นตัวนี้",
  "บทวิเคราะห์เชิงลึก", or any request to produce a long, paragraph-style,
  number-heavy, two-sided (opportunity + risk) business analysis post about a
  public company. Produces a structured 12-section Thai-language article,
  backed by a NotebookLM-based red-flag check that cross-references
  management's Oppday/earnings-call commentary against official filings
  (56-1 One Report / Form 56-REIT / MD&A for Thai names, 10-K/10-Q/20-F +
  transcripts for foreign names). Always research first (web + any provided
  files) before writing. Do NOT use for short summaries, news blurbs, or
  quick Q&A about a stock.
schedule: "After Step 5b, always run Step 5c (critique) before delivery; after delivery run /reflect if the user corrected anything or a tool needed a workaround."
---

# Trendlongtun Brief

Produce a long-form, deep-dive business analysis article on a company/stock, written like a casual Business / Investor post. **The final article is always written in Thai**, regardless of the language of the request or source material.

The article is backed by a **NotebookLM red-flag check**: official filings and management commentary (Oppday / earnings calls / interviews) are loaded into a NotebookLM notebook and cross-referenced against each other *before* writing, so the article's risk section is grounded in actual discrepancies rather than a generic risk list.

## Prerequisites

- `notebooklm auth check --test --json` must return `"status": "ok"` before starting the NotebookLM steps.
- If auth fails → tell the user to run `notebooklm login`.
- **Fast mode (skip the cross-check):** enter **only** when the user explicitly asks for speed — e.g. "quick", "เร็วๆ", "ไม่ต้องเช็ค NotebookLM", "ข้ามการเช็คไฟลิ่ง", or a stated deadline. Never enter fast mode on your own judgment. In fast mode, skip Steps 2–4 and write from web research only. The article must then open — **above Section 1** — with the banner **⚠️ โหมดเร็ว: หัวข้อ "ความเสี่ยง" ยังไม่ได้ตรวจสอบกับเอกสารทางการ (56-1/MD&A/10-K) ผ่าน NotebookLM**, and Section 12's heading carries the suffix "(ยังไม่ได้ cross-check กับไฟลิ่ง)". Because fast mode generates no Step 4 output, no Severity callout appears in fast mode — the fast-mode banner and the Severity callout are mutually exclusive.
- **Notebook reuse (still runs the cross-check):** if `notebooklm list --json` already has a notebook for this ticker covering the needed ~4-year window, reuse it — skip the Step 2 re-download and Step 3 re-upload, but **still run Step 4** on it. This is *not* fast mode: the red-flag section is verified, so no banner is added. If the notebook is missing recent periods, add only the missing sources rather than rebuilding.

## Workflow

### Step 1: Identify the target
Confirm the company/ticker. If the user attached a file (10-K, transcript, deck, financials), read it first — per the user's preference, prefer local filing/transcript data when available.

Determine the market:
- **Thai listed (SET)** → the primary filings are **56-1 One Report** (ordinary companies) or **Form 56-REIT / 56-REIT1** (REITs/trusts), plus quarterly/annual **MD&A** (คำอธิบายและวิเคราะห์ของฝ่ายจัดการ). Earnings-call equivalent is **Oppday** (Opportunity Day).
- **Foreign listed** → primary filings are 10-K/10-Q (US) or 20-F (foreign private issuer), plus the quarterly earnings-call transcript.

### Step 2: Gather primary sources
Pull the last **~4 years** of official filings plus the matching management-commentary media:

**Thai listed company:**
1. Company IR site (`https://[ticker].listedcompany.com` or the issuer's own IR domain) → download 56-1 One Report / Form 56-REIT for each of the last 4 fiscal years, and MD&A for each quarter/year where filed (MD&A is only mandatory when a metric swings >20% YoY, so gaps are expected and not an error).
2. If the IR site is JS-rendered and blocks scraping, use WebFetch on the newsroom listing pages (paginate with `?page=N`), extract the `ir.listedcompany.com/tracker.pl?type=6&id=...` tracker links, and resolve them with `curl -sIL` (curl bypasses the bot-protection that blocks WebFetch on some of these trackers) to get the final PDF URL, then download with `curl -sL`.
3. Search YouTube (via WebSearch, e.g. `"Oppday [TICKER]" youtube`) for the Oppday/earnings-call videos covering the same ~4-year window. Also search for any independent analyst interviews or management interviews specific to the company. **For every media type — Oppday, earnings-call transcript, and interview — explicitly record which periods have coverage and which are missing** (small-caps often have no interviews at all, and Oppday is frequently skipped for some quarters, as happened with AIMCG). A missing period is a data gap to disclose, not to gloss over: list it in the Sources "Media" group, and where a claim leans on a period with no commentary, say so inline.
4. **board.thaivi.org** — per-stock threads (search `site:board.thaivi.org <ticker>`) often carry Oppday summaries, analyst target-price notes and management guidance not findable elsewhere. Login-walled: if a thread redirects to login, use the Playwright manual-login + cookie-reuse script `stock-research/thaivi/login_and_fetch.py` (memory `feedback_login_walled_forum_scrape`) instead of skipping the source. Forum content is secondhand, never a filing — see Step 6.

**Foreign listed company:**
1. Company IR site or SEC EDGAR → 10-K/10-Q/20-F for the last ~4 years.
2. Earnings-call transcripts (Seeking Alpha, Motley Fool, company IR) and/or the recorded earnings-call video/webcast if public.
3. Search YouTube for management interviews, investor-day presentations, and analyst commentary. As with Thai names, **record period-by-period which media exist (transcript, call video, interview) and which are missing**, and disclose the gaps in the Sources "Media" group.

Never rely on a single source per period — the whole point of Step 3 is to compare *what management said* against *what the filing shows*.

### Step 3: Load everything into NotebookLM
1. `notebooklm auth check --test --json` → confirm `"status": "ok"`.
2. Check `notebooklm list --json` for an existing notebook for this ticker; reuse it (`notebooklm use <id>`) instead of creating a duplicate.
3. If none exists: `notebooklm create "[TICKER] - 56-1/MD&A vs Oppday Analysis"` (or `10-K/10-Q vs Earnings Call` for foreign names).
4. Add every filing PDF: `notebooklm source add ./path/to/file.pdf --notebook <id>`.
5. Add every YouTube video: `notebooklm source add "https://youtube.com/watch?v=..." --notebook <id>`. Some videos will fail to ingest (no captions/restricted) — skip and note it, don't block on it.
6. Confirm all sources reach `ready`: `notebooklm source list --notebook <id> --json`.

### Step 4: Run the red-flag cross-check
Before writing a single word of the article, ask NotebookLM to cross-reference the two source types. Use `notebooklm ask "..." --notebook <id> --json` with a prompt structured around four questions (adapt language/terms to the market):

1. **Spin** — where does management's framing in Oppday/earnings-call look better than the number the filing actually shows (e.g. occupancy including related-party fill-in, "net investment income" vs GAAP/TFRS net loss, adjusted vs reported metrics)?
2. **Inconsistency** — where does spoken commentary (e.g. "we only collected X in cash") not match how the filing recognizes the same period (accrual vs cash, timing of impairment/provisions)?
3. **Red flags** — counterparty/tenant/receivable default risk, distributions funded by capital reduction instead of profit, recurring fair-value/asset write-downs, lease-renewal or customer-concentration risk, rising leverage or funding cost, related-party transactions, going-concern language, anything auditors flagged.
4. **Management track record (multi-year)** — extract, from the older filings and Oppday/earnings-call media already in the notebook (the full ~4-year window, not just the latest period): (a) every explicit prior commitment — guidance/targets (revenue, occupancy, DPU, margin), stated strategy (e.g. tenant diversification, deleveraging, cutting related-party exposure), and the stated rationale for each past acquisition — then check each against what the later filings actually delivered; (b) insider alignment — director/executive (for a REIT: manager-and-sponsor) ownership of shares/units, counted **at the related-person level** (the named individual plus spouse, minor children, and other persons deemed related — Thai มาตรา 258 / SEC beneficial-ownership rules — as already aggregated in the filings), **and their transaction history across the full window**, i.e. whether they are a stable long-term holder or trade in and out of their own stock; (c) the compensation or manager-fee structure and what behaviour it rewards. If a subject has too little history to judge (e.g. a newly-installed executive), say so explicitly — "no track record yet" is itself a finding, not a blank. This feeds Section 8. Baseline related-person ownership comes from the filings already loaded (56-1 director-and-related-person shareholding table / 56-REIT sponsor-manager unitholding / DEF 14A beneficial-ownership table + 20-F). The transaction *pattern* is a bounded web read of the insider-transaction record over the full ~4-year window — for Thai names the SET "การถือหลักทรัพย์ของกรรมการและผู้บริหาร" page and/or the SEC market.sec.or.th insider report (แบบ 59), plus แบบ 246-2 for major-holder acquisition/disposal; for foreign names every Form 4/Form 5 on SEC EDGAR over the window. Read the whole transaction list, not just the latest row. This is a heavier read than a single snapshot but is **still a web read outside NotebookLM — it is not a reason to rebuild or re-download the notebook**. If the transaction record can't be accessed or is too sparse to characterize, say so in Section 8 rather than inventing a pattern.

Capture the answer verbatim (with its citations) — this becomes the factual backbone for Section 2, Section 8, and Section 12 below. Do not soften or drop a finding just because it complicates the bull case; the whole point of this step is to keep the article honest.

### Step 4b: Grade the findings (severity gate)
Classify each Step 4 finding. A finding is **severe** if it falls into any of these concrete buckets:
- Going-concern language, auditor qualification, emphasis-of-matter, restatement, covenant breach, or material weakness.
- Distributions/dividends funded by capital reduction, return of capital, or new borrowing rather than profit or operating cash flow.
- A headline metric management presented as positive that the filing shows with the **opposite sign** (e.g. positive "net investment income" vs an actual TFRS/GAAP net loss).
- A utilization metric (occupancy, load factor, backlog, AUM) materially inflated by related-party or non-arm's-length transactions.
- Recurring counterparty default, receivable impairment, or fair-value write-down affecting a material portion (≳10%) of revenue or assets.
- Customer/tenant concentration where losing a single counterparty threatens going-concern.
- A demonstrated management-quality failure: a multi-year *pattern* of missed guidance or abandoned stated strategy (not a single miss); material insider/executive (related-person aggregate, per Section 8) selling during the period the bull case rests on, **or a clear in-and-out trading pattern in their own stock timed around price-sensitive news** (net distribution while the bull case is being promoted, or sells clustered right before bad news / after good news); or a compensation/manager-fee structure that pays management to act against unitholder/shareholder interests (e.g. a fee on gross asset value while unit NAV/DPU falls). Newly-installed or unproven management with **no track record** is *not* severe on its own — note it in Section 8 as execution risk, do not raise a callout for it. A single, small, or routine sale (e.g. a pre-scheduled 10b5-1 / disclosed tax-related disposal) is likewise not severe on its own — it takes a *pattern*, not one transaction.

If **one or more** severe findings exist → the article must open with a **Severity callout** (see Output). If findings exist but none are severe → no callout; they still lead Section 12 as usual. Note which bucket(s) triggered it.

### Step 5: Write the article
Follow the structure and tone rules below. Sections 2 and 12 **must** incorporate the Step 4 findings explicitly (see notes on those sections).

### Step 5b: Number & term check (fact-check gate)
Before delivery, audit every number in **Section 2 and Section 12**, plus **any number anywhere in the article that came from the Step 4 cross-check**. For each:
- Traceable to a filing or to the NotebookLM answer's citation → leave as-is.
- No source → append inline `[ยังไม่ยืนยัน]` right after the figure.
- Sources disagree → append inline `[ขัดแย้ง: <ตัวเลข A จาก X> vs <ตัวเลข B จาก Y>]`.

**Named terms are in scope too, not just numbers.** A NotebookLM answer can attach a fluent-sounding English/Thai label to a real, well-cited figure without that label itself appearing anywhere in the source — the number checks out, the term riding next to it doesn't. This happened for real: a Step 4 answer described AIMCG's occupancy adjustment as "(Fill-In/List Back)"; the underlying 91.70%/78.1% figures were genuinely in the filings, but "List Back" was NotebookLM's own invented gloss — grepping the actual PDF text turned up zero hits for it, only "Fill-In." So: before asserting any named term, defined phrase, or quoted label that came out of a Step 4 answer (not just a number), verify it appears in the primary source — via `notebooklm source fulltext <id>` or a direct grep/pdftotext pass on the downloaded filing — before it goes in the article as if it were official terminology. If it can't be found verbatim, either drop it or rewrite it as plain descriptive language instead of presenting it as a defined term.

This gate **annotates, it does not block** — ship the article with the flags in place (unlike research-idea's Vera, which blocks archiving). Collect every `[ยังไม่ยืนยัน]` / `[ขัดแย้ง]` into a one-line "สิ่งที่ยังยืนยันไม่ได้" note placed just above the disclaimer. Numbers outside Sections 2/12 that are not from Step 4 (general market-size, history, etc.) are not in scope for inline flagging.

### Step 5c: Critique pass (quality gate — before delivery)
Step 5b checks that numbers have sources. This step checks whether the **article as a whole** holds up — the way a skeptical senior analyst would read it. Adapted from the critique mode in poteto/how, but run as **phases in this same context**, not three sub-agents (PHILOSOPHY §4.1 "Phases, not spawns").

**First, the mechanical checks:** `python3 -I tools/lint_deepdive.py reports/<TICKER>_deepdive.html`. Every FAIL line is automatically **ต้องแก้** — fix and re-run until PASS. (It checks ROE/ROA/กำไรสะสม, Watch Items, Filings sources group, disclaimer, and the word "moat". On 2026-10-09 all 11 existing reports failed it — these rules were being forgotten when they lived only as text.)

Then re-read the finished draft three times, each time through one lens only:

**Lens A — Numbers & evidence**
- The same figure stated differently in two sections (e.g. occupancy 73% in Section 2, 75% in Section 4).
- A comparison of two numbers that doesn't say which is better and why.
- Growth/margin claims that use yearly data where quarterly/monthly exists.
- ROE, ROA and retained earnings present and explained (incl. how excess cash drags ROE/ROA).

**Lens B — Business logic (PHILOSOPHY §1)**
- The word "moat" anywhere → replace with competitive advantage + why it could erode.
- A competitive-advantage claim with no evidence (no number, no peer comparison) — assertion only.
- Peer comparisons that cross sectors (hospital vs REIT, office REIT vs logistics REIT) → remove or replace with same-sector peers.
- A section that is one-sided (upside only, or downside only).
- Watch Items without a concrete resolution condition.

**Lens C — Bias & red flags**
- Section 1 states as fact something Step 4 contradicts, or tells the reader to buy despite a severe finding.
- A Step 4 red flag softened, buried, or missing from Section 12 because it conflicts with the bull case (PHILOSOPHY §2.10).
- Severity callout wrong: a severe bucket was hit but no callout — or a callout raised for a single, non-pattern event.
- Management judged on a snapshot instead of the ~4-year record.

For every finding record: **which section, the exact sentence, the evidence (source / Step 4 answer), and the cost** (what a reader would wrongly believe). No evidence → not a finding. An empty critique is a valid result — don't invent problems to look thorough.

**Lead judgment** — you are the editor, not an aggregator. Sort every finding:
| Verdict | Meaning | Action |
|---|---|---|
| **ต้องแก้ (Act on)** | wrong number, cross-sector comparison, softened red flag, missing callout | fix in the article before delivery |
| **น่าพิจารณา (Consider)** | real concern, but needs the user's judgment or data we don't have | list for the user in the delivery message |
| **รับทราบ (Noted)** | valid, low impact | skip |
| **ตัดทิ้ง (Dismissed)** | wrong or style preference | drop |

**Independent check (only when the research drives a real decision):** if the user says they will act on this article (buy/sell/size a position), additionally spawn **one** `sonnet` sub-agent to re-run Lens A independently against the NotebookLM notebook, giving it the article path and notebook ID up front. This mirrors WORKFLOW's Vera rule — do not spawn it for routine deep dives.

In the delivery message, report: number of findings fixed per lens, and the **น่าพิจารณา** items as a short list. Do not paste the whole critique.

### Step 6: Cite sources
List sources at the end, primary sources preferred, each with a link/filename and date. Separate into two groups: "เอกสารทางการ (Filings)" and "คลิป/บทสัมภาษณ์ (Media)", so the reader can see the red-flag check was grounded in both. If board.thaivi.org or similar member-aggregated threads were used, list them in a third group "สรุปจากกระทู้ (Forum-aggregated)", and state in "สิ่งที่ยังยืนยันไม่ได้" that precise-looking figures from them (exact growth %, target prices) are member summaries not verified against the original document.

## Tone & style rules

- Casual Business / Investor voice. Concise, to-the-point language — but the article overall must be **long and dense with detail**, not a short summary.
- Written as a post made of full paragraphs with clear subheadings per section. **Not** a news report. **Not** a bullet-point summary.
- **Labeled structured exhibits are allowed as supplements, never as a replacement for prose.** The paragraph rule above governs the *body* of every section; it does not forbid a clearly-titled, visually set-apart exhibit that *summarizes* material the surrounding prose has already delivered — this is what already makes the financial-trend tables in Section 10 fine, and it is what permits the Business Model Canvas in Section 3. Rules for any such exhibit: (a) it is a compact reference, not the analysis — the prose must still carry the full explanation and pass a **delete test**: if the exhibit were removed, the section must remain complete and lose no essential fact; (b) it introduces no fact, number, or claim that the prose does not already state, and must not contradict the prose or other sections; (c) it is few in number, self-contained, and styled distinctly from body text (reuse the `.card` / titled-exhibit convention) so it never reads as prose fragmented into bullets. Do not use an exhibit as an excuse to thin the prose of a section.
- Emphasize numbers. Whenever two figures are compared, state which is better and explain **why**.
- Compare against industry peers and competitors wherever relevant.
- Explain strategy with relatable, easy-to-grasp analogies.
- **Write for a reader who has never heard of this company, ticker, or instrument type before.** Do not assume prior familiarity with the name or the kind of security it is. The article must orient a complete newcomer, not just readers who already follow this market.
- **Gloss every technical term on first use, anywhere in the article.** The first time any industry/financial term, metric, acronym, or filing name appears — regardless of which section it lands in first (Section 2's financials routinely hit jargon before Section 3 explains the model) — attach a short plain-language gloss in the same sentence or in parentheses (e.g. "gearing (อัตราส่วนหนี้สินต่อสินทรัพย์รวมของกอง) 10% เทียบเพดานกฎหมาย 35%", "DPU (เงินปันผลต่อหน่วย)", "NAV (มูลค่าสินทรัพย์สุทธิต่อหน่วย)", "ECL (ผลขาดทุนด้านเครดิตที่คาดว่าจะเกิดขึ้น)"). Once a term has been glossed, later sections may use it bare. Section 3 still carries the full business-model explanation; this rule only guarantees no term appears un-glossed before it.
- Be two-sided in every dimension — show both the upside and the downside. Write like a pro who sees both the opportunity and the risk. Avoid being overly positive.
- Prefer monthly/quarterly data first; fall back to yearly only if finer granularity is unavailable.
- The user does not believe in the concept of a "moat" — frame durability as **competitive advantage**, not "moat."

## Required sections (write all 12)

1. **ความน่าสนใจของธุรกิจ (Why it's interesting)** — **เปิดด้วยประโยคปูพื้น 1–2 ประโยคก่อนเข้าเนื้อหา bull thesis:** สมมติผู้อ่านไม่เคยได้ยินชื่อบริษัท/กองทรัสต์/หลักทรัพย์ตัวนี้มาก่อนเลย บอกด้วยภาษาชาวบ้านว่ามันคือกิจการ/เครื่องมือประเภทไหน ทำอะไร หาเงินจากอะไรแบบคร่าว ๆ (เช่น "AIMCG คือกองทรัสต์เพื่อการลงทุนในอสังหาฯ หรือ REIT ที่เอาเงินนักลงทุนไปซื้อคลังสินค้า/โรงงานให้เช่า แล้วแบ่งค่าเช่ากลับมาเป็นปันผล") — ห้ามยิงศัพท์เทคนิคหรือเปรียบเทียบตัวเลขก่อนผู้อ่านจะรู้ว่ากำลังดูอะไรอยู่. จากนั้นค่อย Lay out the strongest version of the bull thesis — why the market and the bulls got excited, the kind of setup that makes a reader lean in. What happened in the past 1–2 quarters that drove the stock up a lot? What problems did the stock face before, and how is it turning around or continuing to grow? Frame this as *the case the market is making*, written compellingly but honestly — not as your own endorsement. Do **not** state as fact any figure or claim that the Step 4 cross-check contradicts; if a headline number here is one the filing tells differently, give the bull framing and immediately signpost the handoff (e.g. "…แต่ตัวเลขนี้มีรายละเอียดที่ต้องดูใน Section 2"). If Step 4b flagged a **severe** finding, Section 1 stays descriptive of the bull narrative and must not tell the reader to buy now.
2. **สรุปงบการเงิน + Earnings call ไตรมาสล่าสุด** — Summarize the latest quarterly financials and earnings call/Oppday, including the concerns and drivers analysts asked about that quarter. **Must include the Step 4 spin/inconsistency findings by name** — if management framed a number more favorably in the call than the filing shows, say so here with both figures side by side.
3. **Business model — หาเงินยังไง** — อธิบายให้คนที่ไม่เคยรู้จักธุรกิจ/หลักทรัพย์ประเภทนี้เข้าใจตั้งแต่ศูนย์ว่ามันคือกิจการแบบไหน โครงสร้างหารายได้เป็นอย่างไร เงินเข้าจากไหนออกไปไหน ใครเป็นคนจ่ายให้ และกลไกนี้ต่างจากคู่แข่งในอุตสาหกรรมอย่างไร. นี่คือจุดที่ลงลึกเรื่องโมเดลธุรกิจแบบเต็ม (ต่อยอดจากประโยคปูพื้นสั้น ๆ ใน Section 1 ไม่ใช่พูดซ้ำ; ศัพท์เทคนิคที่โผล่ในหัวข้อก่อนหน้าถูก gloss ครั้งแรกไปแล้วตามกฎ Tone & style). How it makes money, and how that differs from competitors in the industry.

   **ปิดท้าย Section 3 ด้วย Business Model Canvas (BMC) หนึ่งชุด (ผังโมเดลธุรกิจ 9 ช่อง)** วางไว้ *หลัง* ย่อหน้าอธิบายโมเดลธุรกิจแบบเต็มข้างต้น — เป็นส่วนเสริม ไม่ใช่แทนที่ ย่อหน้าเนื้อความยังต้องอธิบายโมเดลตั้งแต่ศูนย์ให้ครบและผ่าน delete test (ลบ canvas ทิ้งแล้ว Section 3 ต้องยังสมบูรณ์อยู่ได้เอง; canvas ต้องไม่มีข้อเท็จจริง/ตัวเลขใหม่ที่เนื้อความไม่ได้พูดไว้). เรนเดอร์เป็นกล่อง exhibit ที่มีหัวข้อชัดเจนและสไตล์แยกจากเนื้อความ (ใช้คอนเวนชัน `.card` / กล่อง exhibit แบบเดียวกับที่ใช้แสดง track record/red-flag) เป็นกริด 9 ช่อง (3×3) ต้องกรอก**ครบทั้ง 9 บล็อกมาตรฐาน** ใส่ชื่อทั้งไทยและอังกฤษในหัวช่อง: (1) พันธมิตรหลัก (Key Partners) (2) กิจกรรมหลัก (Key Activities) (3) ทรัพยากรหลัก (Key Resources) (4) คุณค่าที่ส่งมอบ (Value Propositions) (5) ความสัมพันธ์กับลูกค้า (Customer Relationships) (6) ช่องทาง (Channels) (7) กลุ่มลูกค้า (Customer Segments) (8) โครงสร้างต้นทุน (Cost Structure) (9) กระแสรายได้ (Revenue Streams).
   ตีความแต่ละบล็อกในบริบท **"วิเคราะห์บริษัท/หุ้น"** ไม่ใช่ startup pitch — เช่น Customer Segments = ประเภทลูกค้า/ผู้เช่าจริง, Key Partners = คู่ค้า/ซัพพลายเออร์/ (กรณี REIT) ผู้จัดการกองทรัสต์และสปอนเซอร์, Revenue Streams = โครงสร้างรายได้ค่าเช่า/ค่าบริการ ฯลฯ (เช่น AIMCG: Key Partners = ผู้จัดการกองทรัสต์และสปอนเซอร์ ตามที่ปูไว้ใน Section 8).
   **กติกากันซ้ำซ้อน/ขัดแย้ง:** บล็อกที่เนื้อหาทับกับหัวข้ออื่น ให้สรุปสั้นในช่องแล้วชี้ไปหัวข้อนั้น *อย่าอนุมานตัวเลข/ข้อเท็จจริงใหม่หรือเล่าซ้ำแบบยาว* — Revenue Streams โยง Section 4, Channels/Customer Segments/มุมคู่แข่ง โยง Section 6, Key Partners (ผู้จัดการ/สปอนเซอร์/related-party) โยง Section 8. ทุกช่องต้องสอดคล้องกับตัวเลข/ข้อเท็จจริงในเนื้อความ ห้ามขัดกันเอง.
   **กติกา gloss:** canvas อยู่ท้าย Section 3 (ตามหลัง Section 1–2 และย่อหน้าเต็มของ Section 3) จึง**ห้ามให้ศัพท์เทคนิคตัวใด "โผล่ครั้งแรก" ในช่อง canvas** — ทุกคำในช่องต้องถูก gloss มาก่อนหน้านี้แล้ว; ถ้าจำเป็นต้องใช้คำที่ยังไม่เคย gloss ให้ไป gloss ในเนื้อความก่อน หรือใช้ภาษาชาวบ้านในช่องแทน (ไม่ต้องยัด gloss ในช่องซึ่งพื้นที่จำกัด). แต่ละช่องเป็นวลีสั้นไม่กี่คำตามธรรมชาติของ BMC — เนื้อความข้างบนเป็นตัวอธิบาย canvas เป็นแผนที่อ้างอิงแบบกระชับ.
   หมายเหตุการเรนเดอร์: กำหนดเฉพาะโครงสร้าง/เนื้อหา ไม่ต้องฝัง CSS (ดีไซน์จัดที่ขั้นเขียนบทความตาม design skill) — สั่งเป็น "กล่อง exhibit หัวข้อ Business Model Canvas + กริด 9 ช่องที่มีหัวช่องไทย/อังกฤษ".
4. **สัดส่วนรายได้แต่ละส่วน (%) และอัตรากำไร** — Revenue breakdown by segment (% of total) and each segment's margin. Which segment is most profitable and why; which is least profitable and why. Is there international revenue, and what share?
5. **Competitive advantage** — Why this company is strong and worth holding long-term, and why it gets better the bigger it gets.
6. **เปรียบเทียบกับคู่แข่ง** — How it differs from competitors in business model, product, service, and revenue.
7. **Growth potential** — How it can grow, how it grew in the past, and how it will keep growing.
8. **ผู้บริหารและคุณภาพการบริหาร (Management & management-quality assessment)** — เปิดด้วยภาพผู้ก่อตั้ง/ผู้บริหารชุดปัจจุบัน (สำหรับ REIT คือผู้จัดการกองทรัสต์และสปอนเซอร์): ปรัชญาการทำธุรกิจ วิธีบริหาร และจุดเด่น (เนื้อหาเดิมของหัวข้อ Founder). จากนั้น **ประเมินฝ่ายจัดการในฐานะหัวข้อของตัวเอง** โดยใช้ผลจาก Step 4 ข้อ 4 (Management track record) เป็นแกน และต้องเขียน 4 เช็กนี้ให้ครบทุกครั้ง:
   1. **พูดแล้วทำได้ไหม (หลายปี):** หยิบคำมั่น/เป้า/กลยุทธ์/เหตุผลการซื้อทรัพย์ที่ผู้บริหารเคยพูดไว้ในกรอบ ~4 ปี (guidance รายได้/occupancy/DPU/มาร์จิน, กลยุทธ์ที่ประกาศ เช่น กระจายผู้เช่า ลดหนี้ ลด related-party, และเหตุผลของแต่ละดีลที่ซื้อมา) แล้วเทียบกับสิ่งที่ไฟลิ่งงวดหลังทำได้จริง — ทำได้ตามที่พูดกี่ข้อ พลาดข้อไหน. ถ้าผู้บริหารคนปัจจุบันเพิ่งเข้ามาและยังไม่มี track record ให้ระบุตรง ๆ ว่า "ยังพิสูจน์ฝีมือไม่ได้" ถือเป็น execution risk ที่ต้องบอก (ไม่ใช่ปล่อยผ่าน) และให้ประเมิน track record ของผู้บริหาร/ผู้จัดการชุดก่อนหน้าที่ดูแลช่วงที่ผ่านมาควบคู่ไปด้วย.
   2. **ผู้บริหารมี skin in the game ไหม + ซื้อๆ ขายๆ หรือถือยาว (insider alignment + trading pattern):** ดู 2 มิติ — **(ก) ถือมากน้อยแค่ไหน แบบนับทั้งตระกูล/ผู้เกี่ยวข้อง** ไม่ใช่แค่ชื่อผู้บริหารคนเดียว: รวมคู่สมรส บุตรที่ยังไม่บรรลุนิติภาวะ และผู้ที่ถือว่าเกี่ยวข้องตาม **มาตรา 258** (Foreign คือ beneficial ownership ที่รวมคู่สมรส/ทรัสต์/บุตรตามเกณฑ์ SEC — ตาราง beneficial ownership ใน proxy (DEF 14A) รวมให้อยู่แล้ว). Thai: ยอดถือครองพื้นฐาน + คอลัมน์ผู้เกี่ยวข้อง (คู่สมรส/บุตรที่ยังไม่บรรลุนิติภาวะ) ดูจากตารางการถือหลักทรัพย์ของกรรมการและผู้บริหารใน 56-1 One Report (REIT: สัดส่วนหน่วยที่สปอนเซอร์/ผู้จัดการถือใน 56-REIT ว่าเหลือ skin in the game แค่ไหน) — ใช้เท่าที่ไฟลิ่งเปิดเผย ไม่ต้องไปสืบเครือญาติเพิ่มเอง. **(ข) รูปแบบการซื้อขายตลอด ~4 ปี** ไม่ใช่ snapshot จุดเดียว: อ่านประวัติธุรกรรมทั้งชุดจากหน้า "การถือหลักทรัพย์ของกรรมการและผู้บริหาร" บน SET และ/หรือรายงานแบบ 59 บนเว็บ ก.ล.ต. (market.sec.or.th) รวมถึงแบบ 246-2 ของผู้ถือหุ้นใหญ่ (Foreign: อ่าน Form 4/Form 5 ทุกฉบับบน SEC EDGAR ตลอดกรอบเวลา) แล้วสรุปว่าเป็น **ผู้ถือยาวที่ทยอยสะสม (ซื้อสุทธิ = alignment)** หรือ **นักเล่นรอบที่ซื้อๆ ขายๆ ถี่ (ขายสุทธิ/เข้าออกบ่อย = สัญญาณ misalignment)** — พิจารณา net ซื้อ/ขายสุทธิ, ความถี่ธุรกรรม, ขนาดเทียบกับยอดถือครอง, และจังหวะ. ธงแดงที่ต้องชี้ชัด: ขายหนัก/ขายสุทธิมากในช่วงที่บทวิเคราะห์กำลังเชียร์ หรือธุรกรรมซื้อๆ ขายๆ ที่กระจุกรอบข่าว — ขายก่อนข่าวร้าย/หลังข่าวดี (จังหวะแบบ "เล่นหุ้นตัวเอง"). ทั้งหมดนี้เป็น web read นอก NotebookLM ไม่ต้องตั้ง pipeline ดาวน์โหลดใหม่ (ชื่อแบบอาจปรับตามประกาศ ก.ล.ต. ล่าสุด). **ถ้าข้อมูลผู้เกี่ยวข้องหรือประวัติธุรกรรมไม่เปิดเผย/เข้าถึงไม่ได้/มีน้อยเกินกว่าจะสรุปรูปแบบ ให้เขียนตรง ๆ ว่า "ไม่เปิดเผย" หรือ "ข้อมูลไม่พอสรุปรูปแบบการซื้อขาย" — ห้ามข้ามเงียบ ๆ และห้ามแต่งรูปแบบขึ้นเอง.**
   3. **ประวัติการจัดสรรทุน (capital allocation):** ใช้ข้อมูลดีล/การก่อหนี้ที่มีอยู่แล้วใน Step 2–4 และ Section 7 (Growth potential) — ไม่ต้องหาแหล่งใหม่ — แล้วตัดสิน: ดีลที่ซื้อมาสร้างผลตอบแทนตามเหตุผลที่เคยให้ไว้ไหม (โยงกับเช็กข้อ 1), ก่อหนี้ด้วยต้นทุน/เลเวอเรจที่สมเหตุผลไหม. ถ้าเจอว่าจ่ายปันผลจากการลดทุน/คืนทุน/กู้แทนกำไร ให้ชี้หนึ่งบรรทัดแล้วส่งต่อไป Section 12 (อย่าเล่าซ้ำ — มันคือ severe bucket ของ Step 4b).
   4. **โครงสร้างค่าตอบแทน/ค่าธรรมเนียม (compensation/fee structure):** อยู่ในขอบเขตทั้ง Thai และ foreign เมื่อ "มีการเปิดเผย". Thai REIT: ค่าธรรมเนียมผู้จัดการกองทรัสต์/ผู้บริหารอสังหาฯ (base fee เป็น % ของมูลค่าทรัพย์สิน + performance fee) เปิดเผยใน 56-REIT ที่อยู่ในโน้ตบุ๊กอยู่แล้ว — ประเมินว่าโครงสร้างนี้จูงใจให้ทำสิ่งที่ถูกไหม (เก็บ fee บนมูลค่าสินทรัพย์รวมโดยไม่ผูกกับผลตอบแทนผู้ถือหน่วย = จูงใจให้โต/ถือทรัพย์ไม่ว่าผลตอบแทนจะดีไหม = misalignment; ผูกกับ DPU/NAV = alignment). บริษัทไทยทั่วไป: ค่าตอบแทนกรรมการ/ผู้บริหารใน 56-1 One Report (มักไม่ละเอียดระดับ pay-for-performance — ประเมินเท่าที่เปิด). Foreign: CD&A ใน proxy (DEF 14A). ถ้าไม่เปิดเผย ให้เขียนว่า "ไม่เปิดเผย" — ห้ามข้ามเงียบ ๆ และห้ามแต่งขึ้น.
   ปิดหัวข้อด้วย **คำตัดสินหนึ่งย่อหน้า**: จากทั้ง 4 เช็ก เชื่อมือฝ่ายจัดการชุดนี้ให้คุมสิ่งที่ Section 12 ชี้ว่าเป็นความเสี่ยงได้แค่ไหน. **อย่าเขียนซ้ำกับหัวข้ออื่น:** ประเด็นผลประโยชน์ทับซ้อน/ธรรมาภิบาลเป็นของ Section 12 — อ้างถึงหนึ่งบรรทัดแล้วชี้ไป ไม่เล่าซ้ำ; ความไม่ตรงกันของคำพูดผู้บริหาร "รอบล่าสุด" กับไฟลิ่งเป็นของ Step 4/Section 2. หัวข้อนี้โฟกัสเฉพาะ track record หลายปี ความสอดคล้องของผลประโยชน์ (การถือหุ้น/ค่าตอบแทน) และฝีมือจัดสรรทุน.
9. **ภาพรวมตลาด (Market overview)** — How strongly the market is growing, and how competitive it is.
10. **การเติบโตของรายได้ / อัตรากำไร / FCF** — Revenue growth, margins, and free cash flow explained so a general reader understands. Include past events that slowed growth or compressed margins, and how growth and margins recovered.
11. **ประวัติของธุรกิจ (Company history)** — In great detail; a timeline format is preferred.
12. **ความเสี่ยง + Counter-argument** — What risks does the stock carry? **Lead with the Step 4 red-flag findings** (spin, inconsistency, red flags) before adding any other risks, then build a counter-argument against everything written above in the article.

    **ปิดท้าย Section 12 ด้วย "ประเด็นที่ต้องติดตามต่อ" (Watch Items)** — รายการสั้นๆ ของสิ่งที่ **ยังไม่รู้ผลตอนเขียนบทความ** แต่จะเป็นตัวชี้ขาดว่า bull case หรือ bear case จะถูก — นี่คือคนละเรื่องกับ red flags ข้างต้น (ซึ่งเป็นปัญหาที่เกิดขึ้นแล้ว/พิสูจน์แล้ว) และคนละเรื่องกับ Step 5b's "สิ่งที่ยังยืนยันไม่ได้" (ซึ่งเป็นเรื่อง data ที่หาแหล่งอ้างอิงไม่ได้ ไม่ใช่เรื่องอนาคต) Watch Items ดึงมาจาก 3 แหล่งที่มีอยู่แล้วในบทความ ไม่ต้องหาข้อมูลใหม่:
    - จาก Section 7 (Growth potential): แผนขยาย/ดีลที่ประกาศไว้แต่ยังไม่เกิดขึ้นจริงหรือยังไม่เห็นผล (เช่น โครงการที่กำลังก่อสร้าง ยังไม่เปิดดำเนินการ)
    - จาก Section 8 (Management): จุดที่ระบุไว้ว่า "ยังพิสูจน์ฝีมือไม่ได้" (ผู้บริหารใหม่ไม่มี track record, หรือ capital allocation ที่ยังไม่เห็นผลตอบแทน)
    - จาก Step 4: ข้อสังเกตที่ยัง "เปิดอยู่" ไม่ใช่ข้อเท็จจริงปิดเคสแล้ว (เช่น แนวโน้มที่เพิ่งเริ่มเปลี่ยน ยังต้องดูอีก 1-2 ไตรมาสว่าจะดำเนินต่อไปแบบไหน)

    เขียนเป็นรายการสั้น 3-5 ข้อ แต่ละข้อระบุ **เงื่อนไขที่จะทำให้รู้คำตอบ** ให้ชัดเจน (เช่น "ถ้าโรงพยาบาลภูเก็ตเปิดตรงเวลาไตรมาส 4/2569 และ break-even ได้ในกรอบเวลาใกล้เคียงกับที่สมุยเคยทำได้ ถือว่าฝ่ายจัดการพิสูจน์ฝีมือซ้ำได้อีกครั้ง — ถ้าล่าช้าหรือขาดทุนยืดเยื้อเกิน 12 เดือน ถือเป็นสัญญาณเตือน") ไม่ใช่แค่บอกว่า "ต้องติดตามความเสี่ยงนี้" แบบลอยๆ ไม่มีเกณฑ์ตัดสิน.

## Output

- **Language: Thai.**
- Default deliverable format: a clean, self-contained `.html` document (per the user's default output preference). Use `.pdf` or markdown only if the user asks.
- **Severity callout (conditional).** If Step 4b flagged one or more severe findings, the article opens — **above Section 1** — with a single boxed block titled **⚠️ ข้อสังเกตสำคัญก่อนอ่าน**, containing 2–4 one-sentence bullets, each stating one severe finding with both-sides figures, and a closing line "รายละเอียดอยู่ใน Section 2 และ Section 12". Keep it to one box — do not expand it into a full risk section. If no severe finding, omit the callout entirely; never print an empty or "all clear" box. (This callout and the fast-mode banner are mutually exclusive — fast mode skips Step 4/4b, so it can never produce a Severity callout.)
- Section 12 closes with **"ประเด็นที่ต้องติดตามต่อ" (Watch Items)** — 3-5 forward-looking items with a stated resolution condition each (see Section 12's instruction). This sits between the counter-argument and the Sources section, styled distinctly (reuse the `.card` convention) so it doesn't blur into the counter-argument prose.
- End with a **Sources** section split into "เอกสารทางการ (Filings)" and "คลิป/บทสัมภาษณ์ (Media)", each entry with a link and publication date. Note any disclosed media/filing gaps here (see Step 2).
- Mention the NotebookLM notebook ID/title used for the cross-check, so the user can reopen and ask further questions later.
- This is educational business analysis, not personalized investment advice — include a brief disclaimer.
