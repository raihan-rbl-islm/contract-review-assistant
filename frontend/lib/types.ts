/**
 * Shared TypeScript types mirroring backend Pydantic schemas.
 * See Plan.md §13 for the API contract shapes.
 */

export type RiskLevel =
  | "Low Risk"
  | "Medium Risk"
  | "High Risk"
  | "Not Enough Information";

export type DecisionType = "approve" | "reject" | "mark_for_review";

export interface ContractSummary {
  id: string;
  title: string;
}

export interface ReviewResponse {
  id: string;
  contract_id: string;
  clause_type: string;
  risk_level: RiskLevel;
  contract_evidence: string | null;
  standard_id: string;
  standard_text: string;
  reason: string;
  human_review_required: boolean;
  cached: boolean;
  grounding_passed: boolean | null;
  latency_ms: number;
}

export interface ReviewRequest {
  contract_id: string;
  category?: string;
  question?: string;
}

export interface DecisionRequest {
  decision: DecisionType;
  feedback_text?: string;
}

export interface DecisionResponse {
  id: string;
  review_result_id: string;
  decision: DecisionType;
  feedback_text: string | null;
  created_at: string;
}

export interface TestQuestion {
  id: string;
  contract_id: string;
  question: string;
  group: "public_test" | "missing_info";
  expected_behaviour?: string;
}

export interface AmbiguousIntentError {
  error: "ambiguous_intent";
  candidate_categories: string[];
}

export interface LatencyStats {
  total_reviews: number;
  cache_hit_rate: number;
  total_llm_calls: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  stage_averages: Record<string, number>;
}

export interface QueryLogEntry {
  id: number;
  request_id: string;
  contract_id: string;
  category: string;
  input_mode: string;
  intent_ambiguous: boolean;
  stage_timings_json: string | null;
  cache_hit: boolean;
  grounding_method: string | null;
  llm_retries: number;
  created_at: string;
}
