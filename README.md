# Northstar Contract Review Assistant

**Intra IUB Hackathon — Final Round Submission**

---

## Problem Statement

Companies sign contracts for software, services, partnerships, and vendors. Each contract contains clauses covering payment timelines, termination rights, data handling, intellectual property, and legal liability. Manually checking every clause against internal company standards is time-consuming and error-prone — important risks are easy to miss.

The system built here automates that checking: it locates the relevant clause in a contract, retrieves the matching company-approved standard, compares the two, and returns a risk rating backed by exact evidence — all while requiring a human reviewer to make every final decision.

Two hard constraints shaped the entire design:

1. **No information may be invented.** If a clause does not exist in the contract, the system must say so explicitly — not guess, not infer from legal knowledge, not fill the gap.
2. **A human must always make the final decision.** The system is an assistant, not an authority.

---

## Core Design Decision

The naive approach — sending the full contract and a question to an LLM and asking for an answer — fails the first constraint. A language model is fluent, and a fluent wrong answer is more dangerous than an honest "not found."

The solution is to keep the LLM out of the picture for as long as possible. Every stage before the LLM call is deterministic and verifiable. The LLM is invoked only at the one point where language understanding is genuinely necessary: comparing two pieces of text and explaining the difference in plain language.

This produced a **7-stage deterministic pipeline** where the LLM is stage 6.

---

## How the System Works

### Stage 1 — Intent Resolution (`services/intent.py`)

The user can either select a clause category directly (e.g. click "Automatic Renewal") or type a plain-language question (e.g. "Will this contract renew on its own?").

For free-text input, a keyword scoring classifier maps the question to one of the 7 canonical categories. Each category has an associated keyword list. The classifier counts how many keywords from each category appear in the question using `\b` word-boundary regex matching (case-insensitive), then returns whichever category scores highest.

If the top two categories tie in score, or if nothing matches at all, the system raises `AmbiguousIntentError`. The backend returns HTTP 422 with the list of candidate categories. The frontend catches this, switches to direct-selection mode, and shows the user only the tied categories to pick from manually. A confusing question never silently routes to the wrong category.

No LLM is used at this stage.

### Stage 2 — Cache Retrieval (`services/cache.py`)

Before any processing, the system checks whether this exact `(contract_id, category)` pair has already been reviewed. There is a two-layer cache:

- **In-process:** a Python dictionary guarded by an `asyncio.Lock`, checked first on every request.
- **DB-backed:** a SQLite query ordered by `created_at DESC`, checked on in-process miss, which then populates the in-process layer for future requests.

On a cache hit, the full pipeline is skipped and the stored result is returned immediately — zero LLM calls, zero segmentation work.

### Stage 3 — Clause Segmentation (`services/segmenter.py`)

The contract's raw text is split into individual clause blocks using a regular expression that detects numbered section headings:

```
Pattern: ^\d+\.\d+\s+.+$  (multiline)
Examples matched: "2.1 Payment", "7.1 Automatic Renewal", "10.1 Liability"
```

For each heading found, the clause body is captured as the text between that heading line and the start of the next heading (or end of file). The `Dataset Note:` block appended by the organisers is stripped before parsing using a separate `re.DOTALL` pattern, so it never enters clause content.

The output is a list of `ClauseInstance` objects, each carrying a `heading`, `section_number`, and `text`.

### Stage 4 — Clause Classification (`services/classifier.py`)

Each extracted `ClauseInstance` is mapped to one of the 7 canonical categories using a static keyword dictionary (`CATEGORY_KEYWORDS`). Classification attempts the clause heading first; if no category matches the heading, it falls back to scanning the clause body text.

```python
CATEGORY_KEYWORDS = {
    "Payment":                ["payment", "invoice", "fee"],
    "Termination":            ["termination", "terminate"],
    "Data Protection":        ["data protection", "security", "breach notice",
                               "subprocessor", "subprocessors", "use of data",
                               "data return", "data deletion"],
    "Confidentiality":        ["confidentiality", "confidential"],
    "Automatic Renewal":      ["automatic renewal", "renewal", "renews"],
    "Intellectual Property":  ["intellectual property", "ownership", "ip"],
    "Limitation of Liability":["limitation of liability", "liability"],
}
```

All matching uses `re.search(rf"\b{re.escape(keyword)}\b", heading_lower)` — word boundaries prevent partial matches (e.g. "terminate" does not match inside "determinate").

When multiple clauses in the same contract map to the same category (e.g. C-003's five data-protection sub-clauses), they are merged into a single `ClassifiedClause` with concatenated text and all sub-clauses preserved individually for display.

The output is a dictionary keyed by category string.

### Stage 5 — Gap Check (`services/gap_check.py`)

This is the hallucination firewall.

`check_gap()` does one thing: it checks whether the requested category exists as a key in the classified clause dictionary. If it does not exist, it returns `GapCheckResult(clause_present=False)`.

The pipeline then constructs a `Not Enough Information` result and **returns immediately without reaching stage 6**. The LLM is never called. There is no prompt, no model, no output to hallucinate from.

This is how all three missing-information test cases are handled:

| Case | Contract | Missing Clause | Behaviour |
|---|---|---|---|
| MI-01 | C-004 | Automatic Renewal | Gap fires → NEI, 0 LLM calls |
| MI-02 | C-007 | Termination | Gap fires → NEI, 0 LLM calls |
| MI-03 | C-008 | Limitation of Liability | Gap fires → NEI, 0 LLM calls |

The structural guarantee: `Not Enough Information` can only be produced by gap check (stage 5) or grounding failure (stage 7). It is **explicitly excluded** from the LLM's allowed output at stage 6.

### Stage 6 — LLM Judgment (`services/llm_judge.py`)

Only at this point, with a confirmed clause in hand and a matched company standard, does the system call the LLM.

`call_llm_judge()` is an `async` function that calls Gemini 2.0 Flash via the `google-genai` async client (`client.aio.models.generate_content`). It sends a structured prompt containing:

- The clause category
- The full contract clause text (from the classifier output)
- The company standard text and its ID

The response is constrained to `response_mime_type="application/json"` and the model is instructed to return exactly four fields:

```json
{
  "risk_level": "Low Risk | Medium Risk | High Risk",
  "reason": "one or two plain-language sentences",
  "contract_evidence_quote": "copied word-for-word from the contract clause",
  "standard_evidence_quote": "copied word-for-word from the standard text"
}
```

Two prompt-level constraints prevent hallucination at this stage:

1. `Not Enough Information` is not listed as a valid `risk_level`. The model cannot produce it.
2. The evidence quote fields must be copied verbatim — paraphrasing or summarising is explicitly forbidden in the prompt.

**Retry logic:** On transient errors (HTTP 429, RESOURCE_EXHAUSTED, 503, UNAVAILABLE), the call retries up to 2 times with progressive backoff (0.5s, then 1.5s). On final failure, a soft NEI result is returned rather than crashing the request.

### Stage 7 — Grounding Validation (`services/grounding.py`)

Even with strict prompting, a model can subtly alter quoted text. Grounding validation verifies that each quote the LLM returned is a genuine substring of the source text it was given.

The check runs in three layers:

1. **Strict:** normalise whitespace and quote characters (curly quotes → straight, em dashes → hyphens, collapse whitespace), then check if the quote is a plain substring of the source.
2. **Fuzzy (global):** run `difflib.SequenceMatcher` on the full source. Accept if ratio ≥ 0.9.
3. **Windowed fuzzy:** slide a window across the source text at the length of the quote, checking local similarity at each position. Accept if best window ratio ≥ 0.9.

If all three fail, the result is **downgraded to NEI** and the unverifiable evidence is not shown to the user.

When grounding passes, the displayed evidence is taken from the **original source text** (the contract file and the standards JSON), not from the LLM's echo of it. The user always sees controlled data, never raw model output.

---

## The Full Pipeline — Data Flow

```
User Request (contract_id + category OR question)
        │
        ▼
[1] Intent Resolution       question → category via keyword scoring (no LLM)
        │                   tie or no match → AmbiguousIntentError → 422
        ▼
[2] Cache Check             (contract_id, category) → hit? return stored result
        │                   miss → continue
        ▼
[3] Segmentation            regex splits contract text → list of ClauseInstances
        │
        ▼
[4] Classification          keyword dict maps each clause → canonical category
        │                   multiple matches → merged into one ClassifiedClause
        ▼
[5] Gap Check               category missing from classified set?
        │                   YES → return NEI immediately (LLM never reached)
        │                   NO  → continue
        ▼
[6] LLM Judgment            Gemini 2.0 Flash (async)
        │                   structured JSON output: risk_level + reason + quotes
        │                   retry ×2 on transient errors → soft NEI on failure
        ▼
[7] Grounding Validation    strict → fuzzy → windowed fuzzy
        │                   all fail → downgrade to NEI
        │                   pass → use original source text for display
        ▼
    Persist to DB + Cache
        │
        ▼
    Return ReviewResponse to frontend
```

---

## Human Review

Every result — Low Risk, Medium Risk, High Risk, or Not Enough Information — includes a human action panel with three buttons: **Approve**, **Reject**, and **Mark for Review**. An optional free-text feedback field is also shown.

Submitting a decision calls `POST /api/review/{id}/decision`, which creates a `ReviewDecision` record in the database linked to the `ReviewResult`. The interface permanently displays `"Human review required — this is not legal advice."` on every result card.

---

## API Layer (`routers/`)

| Endpoint | Purpose |
|---|---|
| `GET /api/contracts` | List all 8 contracts with IDs and titles |
| `GET /api/categories` | List the 7 canonical category names |
| `GET /api/test-questions` | Public test questions + missing-info cases for the demo dropdown |
| `POST /api/review` | Run the full pipeline; returns ReviewResponse or 422 on ambiguous intent |
| `POST /api/review/{id}/decision` | Record a human Approve / Reject / Mark for Review decision |
| `GET /api/diagnostics/latency` | Aggregated stats: total reviews, cache hit rate, LLM call count, avg/min/max latency, per-stage averages |
| `GET /api/diagnostics/logs` | Recent query log rows (configurable limit) |

---

## Data Persistence (`models/db_models.py`)

Three tables, created on startup via `Base.metadata.create_all()`:

**`review_results`** — one row per completed pipeline run. Stores contract ID, category, risk level, reason, contract evidence text, standard ID, standard text, grounding pass/fail, total latency in ms, and whether the LLM was called.

**`review_decisions`** — one row per human decision. Foreign key to `review_results`. Stores decision type and optional feedback text.

**`query_logs`** — one row per request for observability. Stores input mode, whether intent was ambiguous, per-stage timing JSON, cache hit flag, grounding method, and LLM retry count.

---

## Observability (`app/diagnostics/page.tsx`)

A dedicated diagnostics page shows:

- Total queries, cache hit rate, total LLM calls made
- Average, minimum, and maximum end-to-end latency
- Per-stage average latency: intent classification, cache lookup, deterministic pipeline (segment + classify + gap), LLM call, grounding check
- Recent query log with input mode, cache hit/miss, grounding method, retry count per row

Per-stage timing is recorded in a JSON column (`stage_timings_json`) on every `QueryLog` row, computed as wall-clock milliseconds around each stage in `pipeline.py`.

---

## Failure Mode Coverage

| Failure Mode | Mechanism That Prevents It |
|---|---|
| LLM invents a missing clause | Gap check fires before any LLM call |
| LLM paraphrases or alters quoted evidence | Grounding validation; fail → NEI, evidence never displayed |
| LLM outputs "Not Enough Information" on its own | NEI excluded from the model's allowed `risk_level` enum |
| Free-text question routes to wrong category | Tie → `AmbiguousIntentError` → user picks manually |
| Repeated queries hit the LLM every time | Two-layer cache (in-process + DB) keyed by `(contract_id, category)` |
| LLM API goes down mid-demo | Retry ×2 with backoff; soft NEI fallback on final failure |
| Unverified model output displayed as fact | Grounding failure → downgrade to NEI; display uses source text, not model echo |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python, Uvicorn (fully async) |
| Database | SQLite via SQLAlchemy async + aiosqlite |
| LLM | Gemini 2.0 Flash — `google-genai` async client |
| Fonts | Fraunces (serif headings), IBM Plex Mono (IDs/metadata), Inter (body) |

---

## Running the Project

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Create .env with: GEMINI_API_KEY=your-key-here
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
# Runs at http://localhost:3000
```

**Tests**

```bash
cd backend
pytest tests/
```

Tests cover clause classification accuracy for all 8 contracts and confirm all 3 missing-information cases produce `clause_present=False` without reaching the LLM.

---

## Scope Notes

- Contracts are loaded from plain-text files provided by the organisers. No PDF parsing or OCR is implemented.
- The cache does not auto-invalidate. A contract update would require a manual cache clear.
- CORS is whitelisted to `localhost:3000`. No authentication system is implemented.
- Tables are created with `create_all()` on startup. Database migrations are out of scope for a prototype.
- The system has been tested against the 8 provided contract excerpts only.