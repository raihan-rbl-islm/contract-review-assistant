# Northstar Contract Review Assistant

Northstar is a full-stack, AI-powered legal contract review assistant designed with strict deterministic constraints, human-in-the-loop validation, and comprehensive system observability. This repository encapsulates the entire application, breaking it down into a robust FastAPI backend and a specialized Next.js frontend.

This document serves as an exhaustive breakdown of every architectural decision, logic flow, and file within the project.

---

## 1. System Architecture Overview

The system follows a strict decoupling of responsibilities. It is not a simple "prompt-in, text-out" LLM wrapper; instead, it wraps the LLM within a **deterministic guardrail pipeline**.

1. **Frontend (Next.js)**: Handles user interaction, complex state management for ambiguous queries, and renders a specialized "legal case-file" design system.
2. **Backend (FastAPI)**: Serves as the orchestration layer. It pipelines requests through deterministic rules (segmentation, classification, gap-checking, cache retrieval) *before* invoking the LLM, and applies grounding validation *after* the LLM returns.
3. **Database (SQLite)**: Stores human-in-the-loop feedback, query logs, cacheable review results, and system latency metrics.

---

## 2. Backend Analysis (`/backend`)

The backend is written in Python using FastAPI, SQLAlchemy (async), and the `google-genai` SDK.

### 2.1 Core Application Setup
* **`requirements.txt`**: Defines the minimal required libraries, notably locking `fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite`, and the new `google-genai` SDK.
* **`app/main.py`**: The entrypoint for the ASGI server. It sets up CORS middleware to allow cross-origin requests from the Next.js frontend and initializes the SQLite database asynchronously on startup. It stitches together the routers (`review`, `feedback`, `diagnostics`).
* **`app/db_models.py`**: Contains the SQLAlchemy models:
  * `ReviewResult`: Stores the final output of a clause review. Used for caching subsequent exact matches. It logs execution latency and the `llm_called` boolean to track system efficiency.
  * `QueryLog`: An append-only audit trail logging every interaction, tracking intent ambiguity, cache hits, LLM retries, and grounding success.

### 2.2 Routers (API Endpoints)
* **`app/routers/review.py`**: Exposes `POST /api/review`. It accepts a `ReviewRequest` (either a direct category or a free-text question). It wraps the `pipeline_service` and catches specialized exceptions like `AmbiguousIntentError`, mapping them to `422 Unprocessable Entity` with structured candidate categories so the frontend can prompt the user to disambiguate.
* **`app/routers/feedback.py`**: Exposes `POST /api/review/{id}/decision`. Allows human reviewers to mark an AI judgment as `approved`, `rejected`, or `needs_review`, appending a human feedback note.
* **`app/routers/diagnostics.py`**: Exposes `GET /api/diagnostics/latency` and `/logs`. It queries the SQLite database to aggregate total API calls, calculate the system-wide cache hit rate, and average out the latency of individual pipeline stages.

### 2.3 The Orchestration Pipeline (`app/services/pipeline.py`)
This is the heart of the backend. It executes a strict 7-stage process:
1. **Intent Resolution**: Passes the user input to `intent.py`.
2. **Cache Lookup**: Checks `cache.py`. If a valid past review exists, it returns immediately, skipping all further stages.
3. **Segmentation**: Passes the contract JSON to `segmenter.py` to break the monolithic document into individual clauses.
4. **Classification**: Passes clauses to `classifier.py` to identify which clauses relate to the identified intent category.
5. **Gap Check**: Evaluates if the standard demands a clause that isn't present in the contract.
6. **LLM Judgment**: Calls the Gemini API via `llm_judge.py`.
7. **Grounding Validation**: Validates the LLM output via `grounding.py`.

The pipeline meticulously logs timing metrics for *each* stage using `time.perf_counter()` and persists a `QueryLog` regardless of success or failure.

### 2.4 Deterministic Services
These services operate without AI, relying on fast, hardcoded logic to guard the LLM:
* **`app/services/intent.py`**: Maps natural language to predefined categories (e.g., "how long does this last?" -> "Term"). If multiple categories match, it raises `AmbiguousIntentError` rather than guessing.
* **`app/services/cache.py`**: Uses SQLAlchemy to find exact matches for `contract_id` and `category` where the risk level is definitive (not missing info).
* **`app/services/segmenter.py`**: Loads the raw JSON contract from the file system (`data/contracts/`) and splits it by headers/paragraphs into manageable textual chunks.
* **`app/services/classifier.py`**: Uses dictionary-based keyword matching (e.g., matching "renew", "extend" to the "Automatic Renewal" category) to isolate only the relevant clauses for the LLM.
* **`app/services/gap_check.py`**: A vital security layer. If the classifier finds no clauses for a requested category, the gap check immediately returns a "Not Enough Information" state, physically preventing the LLM from hallucinating an answer.
* **`app/services/standards.py`**: Stores the "Gold Standard" definitions. The LLM is instructed to strictly judge the clause against these predefined rules rather than its own internal knowledge.

### 2.5 AI Services
* **`app/services/llm_judge.py`**: Interfaces with `gemini-2.0-flash`. 
  * **Structured JSON**: Forces Gemini to output a strict schema (`risk_level`, `reasoning`, `quotes`) using `response_schema`.
  * **Robust Retry Logic**: Implements a retry loop specifically targeted at `429 Too Many Requests` (Quota Exhaustion) errors, parsing the Google generic exceptions to intelligently back off and retry.
* **`app/services/grounding.py`**: The final safeguard. It takes the verbatim `quotes` extracted by the LLM and performs strict substring matching against the original clause text. If the LLM modified even a single word, the quote is flagged as `UNGROUNDED`.

---

## 3. Frontend Analysis (`/frontend`)

The frontend is a Next.js 14 application utilizing React Server Components (where applicable) and heavily relying on Client Components for interactive states.

### 3.1 Design System & Architecture
* **`app/globals.css`**: The entire visual identity of the app is defined here. It bypasses generic Tailwind utility classes in favor of semantic CSS variables. It implements a highly specific **"Legal Case File" aesthetic**:
  * **Typography**: Uses `Fraunces` for authoritative serif headers, `Inter` for highly readable body text, and `IBM Plex Mono` for contract IDs and system data.
  * **Tokens**: Defines precise color variables (`--color-paper`, `--color-ink`, risk scales).
  * **Micro-interactions**: Includes specific hover states, focus rings for accessibility, and CSS animations (respecting `prefers-reduced-motion`).
* **`lib/api.ts` & `lib/types.ts`**: The boundary layer. `types.ts` defines all TypeScript interfaces (e.g., `ReviewResponse`, `LatencyStats`), ensuring absolute parity with the FastAPI models. `api.ts` provides cleanly wrapped asynchronous fetch functions with error handling.

### 3.2 Pages & Routing
* **`app/layout.tsx`**: The persistent shell. Injects the Google Fonts and renders the global Navigation Bar.
* **`app/page.tsx`**: The main operational hub. 
  * **State Management**: Manages complex transitional states (loading, ambiguous errors, displaying results).
  * **Tab Switching**: Toggles between Direct Category Selection and Free-Text NLP input.
  * **Ambiguity Handling**: If the API returns a 422 with candidate categories, the UI smoothly drops the user back into "Direct Selection" mode, highlighting the likely matches.
* **`app/diagnostics/page.tsx`**: The observability dashboard. It fetches real-time latency statistics and renders them in mono-spaced statistic cards. It generates a tabular view of the `QueryLog`, exposing cache hits, execution modes, and LLM retry counts.

### 3.3 UI Components (`/components`)
Components are modularized for strict single-responsibility:
* **`ContractPicker.tsx` & `CategoryPicker.tsx`**: Selectable grid and chip interfaces that manage their own hover/active states while passing selections back up via `onSelect` callbacks.
* **`EvidenceCard.tsx`**: The most complex component. It renders the finalized review. It conditionally styles a visual "Risk Badge" (a stamped, rotated circle) based on the risk level. It renders the LLM's reasoning and utilizes highlighter-yellow (`--color-highlight`) to present verbatim quotes. It also displays grounding metadata tags.
* **`NotEnoughInfoState.tsx`**: A specialized, subdued presentation card utilized specifically when the `gap_check` fires, informing the user that the contract lacks the requested clause entirely.
* **`ReviewActions.tsx`**: The human-in-the-loop component. Provides action buttons (Approve, Reject, Flag) and a text input for human feedback notes. It manages local submission state and swaps to a "Decision Badge" once successfully posted to the API.
* **`LoadingState.tsx` & `ErrorState.tsx`**: Standardized fallback components ensuring the user is never left with a blank or broken screen during async operations.

---

## 4. Execution Flow Summary

1. User selects "Contract A" and asks a free-text question on the Next.js frontend (`page.tsx`).
2. The frontend calls `POST /api/review` (`api.ts`).
3. The FastAPI router passes the request to `pipeline.py`.
4. `intent.py` analyzes the text and resolves it to a specific standard category.
5. `cache.py` checks SQLite. If a match is found, it returns immediately.
6. If no cache, `segmenter.py` and `classifier.py` extract the exact target clause from the JSON contract.
7. `gap_check.py` verifies the clause exists. If missing, it halts the pipeline.
8. `llm_judge.py` formats the clause and the standard, queries the Gemini LLM, and enforces the strict JSON schema.
9. `grounding.py` verifies the LLM's quotes against the original text.
10. `pipeline.py` logs the timing, saves the result to SQLite, and returns the data.
11. The frontend receives the data and renders it beautifully via `EvidenceCard.tsx` and the custom CSS design system.
