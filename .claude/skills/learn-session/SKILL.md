# /learn-session — Minnie + Fact-checker course learning pipeline

**Trigger:** `/learn-session <topic folder> <session file>` or natural language: "สรุป session <N> ของ <topic>", "เรียน <topic> session <N> ให้หน่อย"
**Also triggers on:** "ทำ cross-session synthesis ของ <topic>" (see Phase C)

**Origin:** Built 2026-07-01 for the AI Leading Indicator course after a user request to have Minnie (idea-card asker) query NotebookLM for clarity, plus a separate Fact-checker sub-agent that independently verifies against the raw transcript before finalizing. The plan was reviewed by Opus first — see "Why this shape" below. Validated across all 4 sessions of that course before being promoted to a skill.

**Goal:** Not just an accurate summary — the target is **understand → remember → apply**. A pipeline that only optimizes accuracy misses the point (this was Opus's core critique of v1 of this plan).

---

## Prerequisites

- `source/<topic>/session_X_structured.md` must exist (chapter-by-chapter breakdown with quotes). If missing, offer to run `tools/structure_transcript.py` first (uses Haiku, report cost estimate, confirm before running). agy is on trial for this step (subscription, not API): try it on one session, compare with the Haiku output, and keep the script as the default until the user decides.
- `source/<topic>/transcript_X.txt` (raw transcript) must exist for the same session — this is what Fact-checker reads, never NotebookLM.
- NotebookLM notebook for `<topic>` registered in `knowledge/index.md` is **optional** — if absent, skip the NotebookLM gap-fill step and rely on the structured doc + transcript alone.

## Scope

One **full session** per run (not one chapter at a time — chapter-level was tried first and felt too granular/tedious to the user). A "session" = one `session_X_structured.md` file, which may cover anywhere from ~10 to ~30 chapters.

---

## Phase A — Minnie (draft)

1. Read `session_X_structured.md` in full — this is the primary source, not NotebookLM.
2. Identify genuine gaps: terms named but not explained (e.g. a keyword listed but never defined in the body), numbers/frameworks that feel compressed, or explicit `[ไม่ได้พูดถึง]` markers worth double-checking.
3. **Minnie's persona while asking: a genuinely curious 10-year-old, not a checklist-runner.** A 10-year-old doesn't stop at "what is this" the way a 6-year-old might — they poke at *why* it works, *what breaks if a piece is missing*, and *how it's different* from something they already half-know. For each gap, run a real interrogation, not one Q&A round — mix these question types, not just "ทำไม" on repeat:
   - **ทำไมถึงเป็นแบบนั้น** (why does the mechanism work this way, not just what it's called)
   - **แล้วถ้า [เงื่อนไขเปลี่ยน] ล่ะ** (what-if / edge case — what happens if this factor flips or disappears)
   - **ยกตัวอย่างอื่นที่ไม่ใช่ในคลาสได้ไหม** (transfer — can you name a new example the source never gave)
   - **อันนี้ต่างจาก [เรื่องที่เรียนไปแล้ว] ยังไง** (contrast against a concept already covered, to catch fuzzy boundaries)
   - **ใครได้ประโยชน์ ใครเสียประโยชน์ตรงนี้** (incentives — especially useful for finance content)
   - **งั้นสรุปคือ...ใช่ไหม** (paraphrase check, but never the *only* check — see below)

   **A restated definition is not understanding.** If an answer just repeats the term in different words without exposing the mechanism or cause behind it, that's a signal to keep pushing, not a stopping point. The discipline is in *what* triggers a line of questioning (only real gaps from step 2, never "summarize everything about session X" — that invites cross-session contamination, see below), not in artificially limiting *how many follow-ups* one gap gets once it's worth asking about.

   **Graduation test — both must be true before moving to the next gap:** (a) Minnie can explain this one back in plain language unprompted, AND (b) Minnie can apply it to a new example the source never gave. (a) alone can just mean the answer got echoed back; (b) is what proves it actually clicked. Soft cap ~15-20 *topics* (not raw question count) for a whole session — the cap stops Minnie from re-deriving content the structured doc already covers, it isn't a leash on genuine curiosity about a real gap.
4. **Cross-session contamination warning:** if the NotebookLM notebook contains sources from multiple sessions/days (common — one notebook usually holds the whole course), any answer it gives may silently blend content from a different session. **Never trust a NotebookLM answer about "session X" without grepping it against `transcript_X.txt` specifically.** If the term/number isn't in that session's own transcript, cut it — it likely leaked from another session's source.
5. Draft the summary grouped **by theme**, not mechanically chapter-by-chapter (silos hurt retention). Apply the course's established teaching-style rules — check `knowledge/index.md` or the topic's memory entry for topic-specific style requirements (for AI Leading Indicator: explain-like-a-6-year-old, vivid/concrete analogies, technical terms in English in parens after the plain explanation, can go deep since the learner wants depth, don't pad length just to look complete).
6. **Avoid spec-dump:** if the source material is a long list (rules, checklists, etc.), do not translate the whole list verbatim. Pick the 4-5 most important items, explain each with an analogy + the reason it matters, and put the rest in a compact appendix table for reference — a wall of translated bullets fails the "6-year-old" bar even if every line is accurate.
7. **Avoid duplicate explanations across sections of the same summary** — explain a concept once, cross-reference it elsewhere instead of re-explaining.
8. **Per-heading source footer (required):** every numbered heading (`### N. ...`) ends with **one footer line**:
   ```
   📎 **ที่มา:** transcript_X.txt (Day N) · structured บทที่ K · สไลด์หน้า A–B
   ```
   List only what actually applies (drop the slide part if there's no PDF). This is a by-product of the per-heading grouping you're already doing in step 5, not new work. **Do not** cite per-line or per-sentence — that breaks the analogy prose that carries the pedagogy. The footer is the default citation grain for everything in that section.
9. **Marker vocabulary for exceptions** — inline markers are ONLY for content that breaks the section's default footer citation:
   | Marker | Meaning |
   |---|---|
   | *(none)* | Grounded in what the section's own 📎 footer cites (default — most content) |
   | `🌐` | External supplementary knowledge, not from the instructor — see step 10 |
   | `⚠️` | From slides/memory, not verifiable against transcript (e.g. the MC/Mc Jeans-style case) |
   | `🔗` | Cross-session reference (replaces the old bare `[cross-ref]` tag — same meaning, use `🔗` going forward for consistency) |

   Density principle: **citation density should track risk-of-mis-belief, not be uniform.** A footer per section is the floor; markers are for the exceptions that footer alone can't cover.
10. **External knowledge (positive path, NotebookLM stays instructor-only):** when a genuine gap is a term the instructor *names but never defines*, or a concept compressed past what even a curious 6-year-old could follow from the transcript alone — WebSearch a plain definition instead of leaving the gap or inventing one. Never add the external material as a new NotebookLM source (the notebook must stay instructor-voice-only) and never merge it into the instructor's own paragraph. Render it as its own blockquote:
    ```markdown
    > 🌐 **ความรู้เสริม (นอก source ผู้สอน · WebSearch <วันที่>):**
    > <นิยาม 1-2 บรรทัด> — อ้างอิง: <แหล่ง เช่น Investopedia>. *ผู้สอนใช้คำนี้ในหัวข้อ N แต่ไม่ได้นิยามในคลาส เพิ่มเพื่อความเข้าใจ*
    ```
    Three hard rules, no exceptions: (1) external content always lives in its own `🌐` block, never merged into instructor prose; (2) always cite the real source + the date it was looked up; (3) always state explicitly that the instructor didn't say/define this part. Don't bother routing plain definitions through Fable/Opus for verification — that's overkill for this; a citable source + the marker is enough rigor here.

## Phase B — Fact-checker (independent verification)

This is a distinct pass, not Minnie double-checking itself.

**Who runs it: agy** (`agy-cli/run.sh` with `--add-dir` for the source folder), so the checker is a different model that never saw Minnie's reasoning. Give it the absolute paths of the draft, `transcript_X.txt` and the slide PDF, and tell it to follow steps 1-5 below, reading this section of the skill. Ask for a table: draft says / source says (with file and location) / verdict, plus a separate list of words that look mis-transcribed. Withhold the structured doc and NotebookLM. **Claude then greps every flagged item in both the transcript and the PDF before accepting it**: agy's output is a list of leads, not a verdict. If agy fails or is out of quota, run the check with a sub-agent as before and say so.

1. Read `transcript_X.txt` directly — raw text, not NotebookLM, not the structured doc. This is what makes it independent (Minnie's draft and the structured doc both trace back through the same LLM-summarization step; the raw transcript doesn't). **Also get the slide PDF fulltext for the same session** (extract with `pdftotext`/`pypdf` if not already available as text) and read it alongside the transcript — not optional, see step 3.
2. Scope of check is **fidelity, not truth**: does the draft match what the instructor actually said? Do not fact-check against the real world / real markets — that's out of scope and risks turning into an argument about whether the instructor is right, which isn't the job here.
3. **Mandatory checklist — every proper noun, ticker, product name, and number gets checked, no exceptions.** Do not rely on "does this feel suspicious" — that heuristic has a proven blind spot: in the first run, an oddly-spelled name ("Kawa") got caught because it looked wrong, but a rocket named "Newton" (real name: Neutron) and a ticker "PDD" attributed to the wrong company slipped through because they *looked* plausible. Grep the transcript for every name/number in the draft, one by one.
   **Before concluding anything is AI-invented/hallucinated, grep BOTH the raw transcript AND the slide PDF fulltext — never transcript alone.** Slide-only content (shown on screen but never spoken aloud) is legitimate source material, not hallucination — this is a distinct error class from the cross-session misattribution covered above, and checking transcript alone produces false positives on real content. This must stay consistent with Phase A step 9, which already accepts slides as a source (via the `⚠️` marker) and with the fact that the structured doc itself is built partly from the PDF — Phase B can't hold a stricter bar than Phase A does.
   - ✅ **Worked example (correct call):** a course draft claimed the instructor cited "Aswath Damodaran." Grepped both the transcript and all slide PDFs for that session — zero hits in either. Correctly flagged `⚠️` as unverifiable, kept only the underlying idea.
   - ❌ **Worked example (wrong call — what this rule prevents):** a rebuild grepped only the transcript for "Punchcard Principle," found nothing, and concluded it was AI-invented. It was wrong — the phrase is verbatim on a slide (`"ครั้งมากขึ้น (Punchcard Principle)"`) that was never read aloud. Checking the PDF too would have caught this immediately.
4. **Accept lossy simplification.** A 6-year-old-level explanation necessarily drops detail — that's fine and expected. Only flag a simplification if it's **misleading** (changes what a reader would conclude), not merely if it's incomplete. Flagging every trimmed detail creates conflict-spam and defeats the plain-language goal.
5. When something doesn't match the transcript verbatim but the transcript itself looks like a mis-transcription (garbled foreign name, phonetic near-miss), say so explicitly rather than silently "fixing" it — e.g. "transcript says X, but based on context this is likely Y (real company/product), no impact on the lesson's point."

## Phase C — Resolve conflicts, then finalize

1. If Fact-checker found something that **changes meaning or would change a decision**, show it to the user before finalizing (don't just silently correct and move on, and don't have Minnie/Fact-checker "debate it out" privately either — this was an explicit user preference).
2. If it's a minor labeling nit with no impact on meaning, note it inline as a fact-check footnote and move on.
3. Confirm every numbered heading has its `📎 ที่มา:` footer (Phase A step 8) before saving — this is the last checkpoint before the file is written, not optional polish.
4. Add a closing block to the summary (this is the fix for Opus's "you're optimizing accuracy, not retention" critique):
   - **Active Recall**: 5-10 open-ended questions covering the session's main ideas, each tagged with which section of the summary answers it (so a solo learner can self-check without a human quizzing them).
   - **Application exercise**: 2-4 prompts that make the reader apply a concept from this session to a real stock they hold or watch.
5. Save output:
   - Append a `## Session X — "..."` block to `source/<topic>/lesson_notes.md` (create if missing).
   - Build `source/<topic>/session_X.html` using the HTML template below. Open it with `open "<path>"` so the user can see it immediately.

---

## HTML Template

Self-contained, offline-capable (no external CSS/JS dependency besides the Google Fonts link — matches the course's own Development Rule about standalone dashboards). Reuse verbatim, changing only the accent palette, nav links, hero content, and body sections. Rotate the accent palette per session so sessions are visually distinguishable at a glance:

| Session slot | `--accent` | `--accent2` | `--accent3` | `--accent4` |
|---|---|---|---|---|
| 1st | `#6c63ff` (purple) | `#00d4aa` | `#ff6b6b` | `#ffd93d` |
| 2nd | `#00d4aa` (teal) | `#6c63ff` | `#ff6b6b` | `#ffd93d` |
| 3rd | `#ff6b6b` (red) | `#ffd93d` | `#6c63ff` | `#00d4aa` |
| 4th | `#00d4aa` (teal, alt hero gradient) | `#6c63ff` | `#ff6b6b` | `#ffd93d` |
| synthesis/hub page | `#ffd93d` (gold) | `#6c63ff` | `#00d4aa` | `#ff6b6b` |

```html
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><SESSION TITLE> | <COURSE TITLE></title>
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&family=IBM+Plex+Sans+Thai:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --surface2: #22263a; --border: #2e3250;
    --accent: <ACCENT>; --accent2: <ACCENT2>; --accent3: <ACCENT3>; --accent4: <ACCENT4>;
    --text: #e8eaf6; --text-muted: #8b92b8;
    --gradient: linear-gradient(135deg, <ACCENT> 0%, <ACCENT2> 100%);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'IBM Plex Sans Thai', 'Sarabun', sans-serif; font-size: 16px; line-height: 1.7; }
  nav { position: sticky; top: 0; z-index: 100; background: rgba(15,17,23,0.85); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); padding: 14px 32px; display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }
  nav .logo { font-weight: 700; font-size: 15px; color: var(--accent); letter-spacing: 0.5px; white-space: nowrap; }
  nav a { color: var(--text-muted); text-decoration: none; font-size: 12px; font-weight: 500; transition: color 0.2s; white-space: nowrap; }
  nav a:hover { color: var(--text); }
  .hero { padding: 100px 40px 80px; text-align: center; background: radial-gradient(ellipse at 50% 0%, rgba(108,99,255,0.15) 0%, transparent 70%); border-bottom: 1px solid var(--border); }
  .hero .tag { display: inline-block; background: rgba(108,99,255,0.15); border: 1px solid rgba(108,99,255,0.4); color: #a78bfa; border-radius: 20px; padding: 4px 16px; font-size: 12px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 24px; }
  .hero h1 { font-size: clamp(1.8rem, 5vw, 3.2rem); font-weight: 700; line-height: 1.2; background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 20px; }
  .hero p { color: var(--text-muted); font-size: 18px; max-width: 640px; margin: 0 auto 40px; }
  .hero-stats { display: flex; justify-content: center; gap: 40px; flex-wrap: wrap; }
  .stat { text-align: center; }
  .stat .num { font-size: 2rem; font-weight: 700; color: var(--accent2); }
  .stat .label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
  main { max-width: 1100px; margin: 0 auto; padding: 60px 32px; }
  .section-header { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; margin-top: 64px; }
  .section-header:first-of-type { margin-top: 0; }
  .section-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
  .section-header h2 { font-size: 22px; font-weight: 700; }
  .section-header p { font-size: 13px; color: var(--text-muted); margin-top: 2px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 26px 30px; margin-bottom: 18px; transition: border-color 0.2s, transform 0.2s; }
  .card:hover { border-color: rgba(108,99,255,0.4); transform: translateY(-2px); }
  .card h3 { font-size: 15px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
  .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
  .quote { border-left: 3px solid var(--accent); background: rgba(108,99,255,0.07); border-radius: 0 12px 12px 0; padding: 18px 24px; margin: 20px 0; font-style: italic; font-size: 16px; color: #c4b5fd; }
  .badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 20px; letter-spacing: 0.5px; }
  .badge-purple { background: rgba(108,99,255,0.2); color: #a78bfa; }
  .badge-teal { background: rgba(0,212,170,0.15); color: #34d399; }
  .badge-red { background: rgba(255,107,107,0.15); color: #f87171; }
  .badge-yellow { background: rgba(255,217,61,0.15); color: #fbbf24; }
  .warning { background: rgba(255,217,61,0.08); border: 1px solid rgba(255,217,61,0.3); border-radius: 12px; padding: 16px 20px; display: flex; gap: 12px; align-items: flex-start; margin: 20px 0; }
  .warning-icon { font-size: 18px; flex-shrink: 0; }
  .warning p { font-size: 14px; color: #fde68a; }
  .note { background: rgba(0,212,170,0.06); border: 1px solid rgba(0,212,170,0.25); border-radius: 12px; padding: 14px 18px; display: flex; gap: 12px; align-items: flex-start; margin: 16px 0; }
  .note-icon { font-size: 16px; flex-shrink: 0; }
  .note p { font-size: 13px; color: #6ee7c7; }
  .cross-ref { background: rgba(108,99,255,0.06); border: 1px dashed rgba(108,99,255,0.35); border-radius: 12px; padding: 14px 18px; margin: 20px 0; }
  .cross-ref p { font-size: 13px; color: #c4b5fd; }
  .source-footer { margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-muted); }
  .external { background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.3); border-radius: 12px; padding: 14px 18px; margin: 16px 0; }
  .external p { font-size: 13px; color: #7dd3fc; }
  .timeline { display: flex; align-items: center; gap: 0; margin: 24px 0; flex-wrap: wrap; }
  .timeline-step { background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 12px 18px; text-align: center; flex: 1; min-width: 120px; }
  .timeline-step .t-icon { font-size: 20px; margin-bottom: 4px; }
  .timeline-step .t-label { font-size: 12px; font-weight: 600; }
  .timeline-step .t-sub { font-size: 11px; color: var(--text-muted); }
  .timeline-arrow { color: var(--accent); font-size: 20px; padding: 0 6px; flex-shrink: 0; }
  .version-flow { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 16px; }
  .version-box { background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; font-size: 12px; }
  .version-box .vnum { font-weight: 700; color: var(--accent); font-size: 11px; }
  .sector-table, .fc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .sector-table th, .fc-table th { background: var(--surface2); color: var(--text-muted); font-size: 10px; letter-spacing: 1px; text-transform: uppercase; padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }
  .sector-table td, .fc-table td { padding: 12px 14px; border-bottom: 1px solid rgba(46,50,80,0.5); vertical-align: top; }
  .sector-table tr:last-child td, .fc-table tr:last-child td { border-bottom: none; }
  details.recall { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; margin-bottom: 12px; }
  details.recall summary { cursor: pointer; font-size: 14px; font-weight: 600; list-style: none; display: flex; align-items: center; gap: 10px; }
  details.recall summary::-webkit-details-marker { display: none; }
  details.recall summary::before { content: '▸'; color: var(--accent); transition: transform 0.2s; }
  details.recall[open] summary::before { transform: rotate(90deg); }
  details.recall .answer { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 13px; color: var(--text-muted); }
  .apply-card { background: var(--surface); border: 1px solid rgba(255,217,61,0.3); border-radius: 14px; padding: 22px 26px; }
  .apply-card li { margin-bottom: 10px; }
  footer { text-align: center; padding: 48px 32px; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 13px; margin-top: 80px; }
  .reveal { opacity: 0; transform: translateY(20px); transition: opacity 0.5s, transform 0.5s; }
  .reveal.visible { opacity: 1; transform: translateY(0); }
  ul { padding-left: 20px; }
  li { margin-bottom: 6px; font-size: 14px; color: var(--text-muted); }
  li strong { color: var(--text); }
  @media (max-width: 600px) { .hero { padding: 60px 20px 48px; } main { padding: 40px 20px; } nav { padding: 12px 16px; gap: 10px; } .hero-stats { gap: 24px; } }
</style>
</head>
<body>

<nav>
  <span class="logo"><EMOJI> <SESSION LABEL></span>
  <!-- one <a href="#anchor">label</a> per major section -->
</nav>

<section class="hero">
  <div class="tag"><SESSION LABEL> · <SHORT SUBTITLE></div>
  <h1><SESSION TITLE></h1>
  <p><ONE-LINE HOOK — the north-star takeaway of this session></p>
  <div class="hero-stats">
    <!-- up to 4 <div class="stat"><div class="num">N</div><div class="label">...</div></div> -->
  </div>
</section>

<main>
  <!-- one section per theme group from Phase A step 5 -->
  <!-- use .card / .grid-2 / .grid-3 / .quote / .warning / .note / .timeline / .version-flow / .sector-table as needed -->
  <!-- .note blocks flag fact-check corrections inline, right where the corrected claim appears -->
  <!-- .cross-ref block + a link when a topic repeats content from a prior session instead of re-explaining it (🔗 marker) -->
  <!-- .source-footer: one per numbered heading/section, closes it with "📎 ที่มา: ..." (Phase A step 8 / Phase C step 3) -->
  <!-- .external: 🌐 blockquote for WebSearch-sourced supplementary knowledge (Phase A step 10) — always its own block, never merged into instructor prose -->

  <!-- Active Recall section: one <details class="recall"><summary>Q</summary><div class="answer">A + section pointer</div></details> per question -->

  <!-- Application exercise: .apply-card with a <ul> of prompts -->
</main>

<footer>
  <p><SESSION LABEL> — "<SESSION TITLE>" · สรุปจากคอร์ส <COURSE TITLE></p>
  <p style="margin-top:8px;color:rgba(139,146,184,0.5);font-size:12px">ผ่านกระบวนการ Minnie → Fact-checker (raw transcript) · <DATE></p>
</footer>

<script>
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
</script>
</body>
</html>
```

---

## Phase D — Cross-session synthesis (after all sessions of a course are done)

Triggered separately once every `session_X.html` for a topic exists. Do not run this after just one session.

1. Re-read every `## Session ...` block already appended to `source/<topic>/lesson_notes.md`.
2. Extract the **recurring frameworks** — concepts that show up in 3+ sessions independently (not things you're forcing to connect). These are the actual spine of the course; call them out explicitly as "if you remember nothing else, remember these N things."
3. Build a **master sector/topic → tool table** consolidating every named data source/tool across all sessions (helps a solo learner see the whole toolkit at a glance instead of re-deriving it session by session).
4. Build a **master fact-check log** consolidating every correction made across all sessions in one table — this is also a real diagnostic: patterns in what kind of things get mis-transcribed (proper nouns in English inside a Thai transcript, consistently) tell you where to focus extra scrutiny next time.
5. Build a **"🧠 Active Recall — ทั้งคอร์ส"** block: pool every Active Recall question from every session's `## Session X` block into one course-wide self-quiz (still tagged with which session/section answers each one). This is the cheap, no-scheduler-needed version of spaced repetition for a solo learner — do this, don't build a real SRS/forget-tracking system on top of it (out of scope for this project's scale).
6. Append this synthesis to the end of `lesson_notes.md` and build one `synthesis.html` hub page (same HTML template, gold/`#ffd93d`-led palette) that links out to every `session_X.html` plus shows the master tables and the course-wide Active Recall block. Open it in the browser.

---

## Why this shape (Opus review, 2026-07-01)

Original plan asked NotebookLM as many questions as possible per chapter and had a second agent "independently" re-ask NotebookLM to verify — Opus flagged both as flawed:

- **Two agents asking the same NotebookLM notebook is not independent verification** — if the notebook's RAG mis-reads a source once, both agents inherit the same mistake and you get false confidence. Fix: Fact-checker reads the raw transcript directly, never the notebook.
- **"Ask as many questions as possible" is over-engineering** when a structured doc already exists — it re-derives content that's already in hand and adds hallucination surface. Fix: only ask about genuine gaps, with an explicit stopping rule.
- **The plan optimized for accuracy, not for the user's actual goal** (remember it, use it while trading). Fix: mandatory Active Recall + application block at the end of every session, not just a fact-checked summary.
- **Simplification vs. fact-checking are in tension by design** — flag misleading simplification, not lossy simplification, or every plain-language paraphrase gets flagged as a "conflict."

## Cost estimate per session
- NotebookLM gap-fill queries: ~15-20 questions, free tier or included in existing NotebookLM subscription
- Fact-checker transcript grep: no LLM cost, direct file search
- Sonnet drafting + HTML generation: 1-2 passes, comparable to `publish-course`'s Sonnet pass (~$0.10-0.30 per session)
