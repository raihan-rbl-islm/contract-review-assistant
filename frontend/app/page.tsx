"use client";

import { useState, useEffect, FormEvent } from "react";
import ContractPicker from "@/components/ContractPicker";
import CategoryPicker from "@/components/CategoryPicker";
import EvidenceCard from "@/components/EvidenceCard";
import NotEnoughInfoState from "@/components/NotEnoughInfoState";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import {
  getContracts,
  getCategories,
  getTestQuestions,
  createReview,
  parseAmbiguousIntent,
} from "@/lib/api";
import type {
  ContractSummary,
  TestQuestion,
  ReviewResponse,
} from "@/lib/types";

type Mode = "direct" | "free-text";

export default function Home() {
  // Data
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [testQuestions, setTestQuestions] = useState<TestQuestion[]>([]);

  // UI State
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [mode, setMode] = useState<Mode>("direct");
  
  // Form State
  const [selectedContractId, setSelectedContractId] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [question, setQuestion] = useState<string>("");

  // Review State
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ambiguousCategories, setAmbiguousCategories] = useState<string[] | null>(null);

  // Initial Data Fetch
  useEffect(() => {
    async function fetchInitialData() {
      try {
        const [contractsData, categoriesData, questionsData] = await Promise.all([
          getContracts(),
          getCategories(),
          getTestQuestions(),
        ]);
        setContracts(contractsData);
        setCategories(categoriesData);
        setTestQuestions(questionsData);
        if (contractsData.length > 0) setSelectedContractId(contractsData[0].id);
        if (categoriesData.length > 0) setSelectedCategory(categoriesData[0]);
      } catch (err) {
        console.error("Failed to load initial data", err);
        setError("Could not connect to the backend server.");
      } finally {
        setLoadingInitial(false);
      }
    }
    fetchInitialData();
  }, []);

  const handleReview = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!selectedContractId) return;
    if (mode === "direct" && !selectedCategory) return;
    if (mode === "free-text" && !question.trim()) return;

    setIsReviewing(true);
    setError(null);
    setReviewResult(null);
    setAmbiguousCategories(null);

    try {
      const result = await createReview({
        contract_id: selectedContractId,
        ...(mode === "direct" ? { category: selectedCategory } : { question }),
      });
      setReviewResult(result);
    } catch (err: unknown) {
      const ambiguous = parseAmbiguousIntent(err);
      if (ambiguous) {
        setAmbiguousCategories(ambiguous.candidate_categories);
        // Switch to direct mode so they can pick one
        setMode("direct");
        setSelectedCategory(ambiguous.candidate_categories[0]);
      } else {
        console.error("Review failed", err);
        setError("Failed to run review. Please try again.");
      }
    } finally {
      setIsReviewing(false);
    }
  };

  const handleSampleQuestionSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const qId = e.target.value;
    if (!qId) return;

    const selectedQ = testQuestions.find(q => q.id === qId);
    if (selectedQ) {
      setSelectedContractId(selectedQ.contract_id);
      setQuestion(selectedQ.question);
      setMode("free-text");
    }
  };

  if (loadingInitial) {
    return <div className="page-container">Loading...</div>;
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <h1>Contract Review Assistant</h1>
        <p className="subtitle">Select a contract and a clause category to review.</p>
      </header>

      {/* Contract Selection */}
      <ContractPicker
        contracts={contracts}
        selectedId={selectedContractId}
        onSelect={(id) => {
          setSelectedContractId(id);
          setReviewResult(null);
        }}
      />

      <hr className="section-divider" />

      {/* Mode Switcher */}
      <div className="tab-switcher">
        <button
          className={`tab-btn ${mode === "direct" ? "active" : ""}`}
          onClick={() => setMode("direct")}
          type="button"
        >
          Direct Selection
        </button>
        <button
          className={`tab-btn ${mode === "free-text" ? "active" : ""}`}
          onClick={() => setMode("free-text")}
          type="button"
        >
          Free-Text Question
        </button>
      </div>

      {/* Direct Mode Input */}
      {mode === "direct" && (
        <div className="mode-panel">
          {ambiguousCategories && (
            <div style={{ background: "#F5E6E3", color: "#A63A2E", padding: "12px", borderRadius: "4px", marginBottom: "16px", fontSize: "0.875rem" }}>
              <p style={{ margin: 0 }}>
                <strong>Ambiguous Request:</strong> We couldn't determine a single category from your question. 
                Please select one of the likely matches below:
              </p>
            </div>
          )}
          <CategoryPicker
            categories={ambiguousCategories || categories}
            selectedCategory={selectedCategory}
            onSelect={setSelectedCategory}
          />
          <div style={{ marginTop: "24px" }}>
            <button
              className="submit-btn"
              onClick={() => handleReview()}
              disabled={isReviewing || !selectedCategory}
              type="button"
            >
              Review Clause
            </button>
          </div>
        </div>
      )}

      {/* Free-Text Mode Input */}
      {mode === "free-text" && (
        <div className="mode-panel">
          <form onSubmit={handleReview} className="question-section">
            <label className="picker-label">Ask a question</label>
            <div className="question-input-wrapper">
              <input
                type="text"
                className="question-input"
                placeholder="e.g. Does this contract have an automatic renewal?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <button
                type="submit"
                className="submit-btn"
                disabled={isReviewing || !question.trim()}
              >
                Ask
              </button>
            </div>
            
            {/* Demo Dropdown */}
            {testQuestions.length > 0 && (
              <div className="sample-dropdown">
                <select className="sample-select" onChange={handleSampleQuestionSelect} defaultValue="">
                  <option value="" disabled>Or pick a sample question...</option>
                  <optgroup label="Public Test Cases (PQ)">
                    {testQuestions.filter(q => q.group === "public_test").map(q => (
                      <option key={q.id} value={q.id}>{q.id}: {q.question} ({q.contract_id})</option>
                    ))}
                  </optgroup>
                  <optgroup label="Missing Info Cases (MI)">
                    {testQuestions.filter(q => q.group === "missing_info").map(q => (
                      <option key={q.id} value={q.id}>{q.id}: {q.question} ({q.contract_id})</option>
                    ))}
                  </optgroup>
                </select>
              </div>
            )}
          </form>
        </div>
      )}

      <hr className="section-divider" />

      {/* Results Area */}
      <div className="results-area">
        {isReviewing ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={() => handleReview()} />
        ) : reviewResult ? (
          reviewResult.risk_level === "Not Enough Information" ? (
            <NotEnoughInfoState review={reviewResult} />
          ) : (
            <EvidenceCard review={reviewResult} />
          )
        ) : (
          <div style={{ textAlign: "center", color: "var(--color-ink-soft)", padding: "48px 0" }}>
            Select a contract and category to see the review.
          </div>
        )}
      </div>
    </div>
  );
}
