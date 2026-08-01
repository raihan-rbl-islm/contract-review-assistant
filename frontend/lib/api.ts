/**
 * Typed fetch wrappers to the backend API.
 * See Plan.md §13 for endpoint specifications.
 */

import type {
  ContractSummary,
  ReviewRequest,
  ReviewResponse,
  DecisionRequest,
  DecisionResponse,
  TestQuestion,
  LatencyStats,
  QueryLogEntry,
  AmbiguousIntentError,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(`API Error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }

  return res.json();
}

/** GET /api/contracts — list all contracts with IDs and titles */
export async function getContracts(): Promise<ContractSummary[]> {
  return request<ContractSummary[]>("/api/contracts");
}

/** GET /api/categories — list the 7 canonical categories */
export async function getCategories(): Promise<string[]> {
  return request<string[]>("/api/categories");
}

/** GET /api/test-questions — sample questions for the demo dropdown */
export async function getTestQuestions(): Promise<TestQuestion[]> {
  return request<TestQuestion[]>("/api/test-questions");
}

/**
 * POST /api/review — run a clause review.
 * Returns the review result, or throws an ApiError with
 * status 422 if intent was ambiguous.
 */
export async function createReview(body: ReviewRequest): Promise<ReviewResponse> {
  return request<ReviewResponse>("/api/review", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Check if an API error is an ambiguous intent error.
 * If so, parse and return the candidate categories.
 */
export function parseAmbiguousIntent(
  err: unknown
): AmbiguousIntentError | null {
  if (err instanceof ApiError && err.status === 422) {
    const detail = err.detail as { detail?: AmbiguousIntentError };
    if (detail?.detail?.error === "ambiguous_intent") {
      return detail.detail;
    }
  }
  return null;
}

/** POST /api/review/{id}/decision — submit a human decision */
export async function submitDecision(
  reviewId: string,
  body: DecisionRequest
): Promise<DecisionResponse> {
  return request<DecisionResponse>(`/api/review/${reviewId}/decision`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** GET /api/diagnostics/latency — aggregated stats */
export async function getLatencyStats(): Promise<LatencyStats> {
  return request<LatencyStats>("/api/diagnostics/latency");
}

/** GET /api/diagnostics/logs — recent query logs */
export async function getQueryLogs(limit = 50): Promise<QueryLogEntry[]> {
  return request<QueryLogEntry[]>(`/api/diagnostics/logs?limit=${limit}`);
}

export { ApiError };
