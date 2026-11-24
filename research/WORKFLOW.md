# Research Workflow
_Single source of truth for stock research in studio. Supersedes the global `research-idea` skill within this directory._

---

## Design Principles

1. **Phases, not spawns.** Run the full pipeline as sequential phases in ONE model context. Do NOT spawn 6 sub-agents. Only exception: Vera, only when research drives a real decision (run by agy, see Phase 4; sub-agent is the fallback).
2. **Cite-or-flag (anti-hallucination).** Every number/claim must carry a source (NotebookLM citation, filing, or local file). No source → mark `[UNVERIFIED]`. Conflicting numbers → `[CONFLICT]`. If no source exists at all → STOP and tell the user to add sources first.
3. **No duplication.** This file is the only workflow definition for studio. ONE knowledge base (`studio/knowledge/`), ONE set of playbooks.
4. **Cost discipline.** One context; don't re-read sources already in context; use partial pipelines for simple asks (see routing table); only run a separate Vera when it matters.
5. **Analysis only.** Never give buy/sell advice. Separate facts / assumptions / opinions throughout.

---

## The Lean Loop (5 Phases)

### Phase 0 · Discovery
_Run only if this is an unfamiliar company or first time researching it._

| | |
|---|---|
| **Input** | Company name / ticker |
| **Action** | Explain the business in plain language: one-sentence summary, what it does, how it makes money, who the customers are, what the market looks like, who the competitors are, beginner risks. Output a verdict: `proceed` / `needs-info` / `skip`. |
| **Output** | Short business-understanding note (≤10 lines). Save to `knowledge/insights/<TICKER>_atoms.md` as a "Business" atom if new. |

_Adapted from Company Discovery agent — condensed to plain-language briefing only; drop the heavy 10-section format._

---

### Phase 1 · Frame
| | |
|---|---|
| **Input** | Ticker, any known context from `knowledge/insights/<TICKER>_atoms.md` |
| **Action** | Build an **Idea Card** using `research/playbooks/question_playbook.md`. Pull leading-indicator angles from the "AI Leading Indicator" NotebookLM notebook (after T2.6). Prioritize 5–8 questions, one at a time. Draft bull/bear hypothesis. |
| **Output** | Idea Card with prioritized questions + bull/bear hypothesis. |

---

### Phase 2 · Gather
| | |
|---|---|
| **Input** | Idea Card questions, stock's NotebookLM notebook ID from `knowledge/index.md` |
| **Action** | Query the stock's OWN NotebookLM notebook one question at a time, following the question playbook rules: state the year, name the document to force citation, separate fact vs sentiment. **Thai (SET) stocks — also run the numbers snapshot first:** `~/.venvs/thaifin/bin/python -I tools/thaifin_fetch.py <TICKER>` (5 yrs + 6 qtrs: revenue, net profit, YoY, GPM/NPM, ROE/ROA, D/E, EPS, CFO, P/E, P/BV). Exit 2 = not on SET → skip. Use it to spot trends worth asking NotebookLM about, and paste the table into the Q&A doc. |
| **Output** | Q&A doc with citations (+ thaifin snapshot for SET stocks). |
| **STOP condition** | If there is no notebook or no sources for this stock → tell the user to add sources first; do not proceed to Phase 3. |

---

### Phase 3 · Synthesize
| | |
|---|---|
| **Input** | Q&A doc from Phase 2 |
| **Action** | Write a Research Doc: Summary (≤3 bullets), Bull Case, Bear Case, Key Metrics table. Every number must be cited. Mark `[UNVERIFIED]` for anything without a source. Mark `[CONFLICT]` for contradictions. **thaifin numbers** are a secondary aggregator (Finnomena), not a filing: cite them as `(thaifin/Finnomena)`. They may fill trend/ratio rows, but any headline number the thesis leans on (latest revenue, net profit, dividend) must also be cited to a filing; if they differ → `[CONFLICT]`, filing wins. Never use thaifin's Div Yield when the script flags it. thaifin alone never satisfies the "no source → STOP" rule. |
| **Output** | Research Doc saved to `reports/<TICKER>_research_<date>.md`. |

---

### Phase 4 · Check
| | |
|---|---|
| **Input** | Research Doc from Phase 3 |
| **Action** | **Chris** (same context): identify logic gaps, missing perspectives, imbalance in bull/bear. **Vera** (only for real decisions): independently re-verify every number against sources; flag `[UNVERIFIED]`/`[CONFLICT]`. Recompute every derived number (ratios, YoY, valuation, market cap) with `python3 -I tools/fin_check.py` and compare multi-source figures with `fin_check.py cross-validate --ref <filing>` (exit 1 = conflict) — inline Vera too, never mental math. Run it through agy (`agy-cli/run.sh` with `--add-dir` for the source folder), pointing it at `source/<TICKER>/` and the report. For a blind valuation, withhold the report and forbid `reports/` and `knowledge/`. **agy red-team** (same trigger, optional): agy lists holes in the thesis; Claude weighs them and agy's view never becomes the conclusion. Check every mismatch against the source yourself before accepting it. If agy fails or is out of quota, use a sub-agent. For non-actionable or quick research, run Vera inline. |
| **Output** | Annotated Research Doc with Chris's critique + Vera's fact-check (say whether agy or a sub-agent ran it). |

---

### Phase 5 · Decide + Archive
| | |
|---|---|
| **Input** | Checked Research Doc |
| **Action** | Apply `research/playbooks/decision_framework.md` (quality scorecard + valuation read → conviction score; no buy/sell label). Write a Decision Journal entry. Extract durable atoms → `knowledge/insights/<TICKER>_atoms.md`. Update `knowledge/index.md`. |
| **Output** | Decision Journal entry + updated atoms file. |

---

## Routing Table

_Avoid running the full loop for everything._

| Request | Run |
|---|---|
| New stock / raw idea | Phase 0 → 5 (full) |
| "X ของหุ้นนี้คือเท่าไหร่" / "what is X of this stock" | Phase 2 → 3 only |
| "เทียบ A vs B" / "compare A vs B" | Phase 1 → 4 (two stocks) |
| "อัปเดต report" / "update the report" | Phase 2 → 3 → 4 |
| "สรุปที่รู้แล้ว" / "summarize what we know" | Read `knowledge/insights/`, answer directly — no pipeline needed |

---

## Hard Rules

- **Cite or flag.** Every number needs a source. No source → `[UNVERIFIED]`.
- **Stop if no source.** If there is no notebook or filing for the stock, STOP and say so. Do not fabricate.
- **Separate facts / assumptions / opinions** clearly throughout the research doc.
- **Analysis only.** Never give a buy/sell recommendation. Produce research and a decision framework — the user makes the call.
- **Conflict = flag.** If two sources contradict each other, write `[CONFLICT: source A says X, source B says Y]` and let the user resolve.

---

## How to Invoke

**Prerequisites:**
- The stock must have its own NotebookLM notebook with sources (filings, annual reports, etc.) added and registered in `knowledge/index.md`.
- "Putting sources in" = adding filings/reports to the stock's NotebookLM notebook via `notebooklm source add`.

**Trigger phrases:**

| User says | Action |
|---|---|
| "วิจัย `<TICKER>`" / "research `<TICKER>`" | Full loop Phase 0 → 5 |
| "ถาม `<TICKER>` ว่า `<X>`" / "`<X>` ของ `<TICKER>`?" | Phase 2 → 3 only |
| "เทียบ `<A>` vs `<B>`" | Phase 1 → 4 (two stocks) |
| "อัปเดต report `<TICKER>`" | Phase 2 → 3 → 4 |
| "สรุปที่รู้แล้วเรื่อง `<TICKER>`" | Read `knowledge/insights/`, answer directly |

**On trigger:**
1. Read this WORKFLOW.md (already loaded if in studio).
2. Check `knowledge/index.md` for the stock's NotebookLM notebook ID.
3. If no notebook → STOP. Tell user to add sources first.
4. Run on Sonnet (execution). Run Vera through agy (Phase 4) only when user signals the research will drive a real decision.

---

## Pointers

| Resource | Path |
|---|---|
| Question Playbook | `research/playbooks/question_playbook.md` |
| Decision Framework | `research/playbooks/decision_framework.md` |
| Knowledge Base Index | `knowledge/index.md` |
| Per-stock atoms | `knowledge/insights/<TICKER>_atoms.md` |
| Research reports | `reports/<TICKER>_research_<date>.md` |
