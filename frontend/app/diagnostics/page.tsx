"use client";

import { useState, useEffect } from "react";
import { getLatencyStats, getQueryLogs } from "@/lib/api";
import type { LatencyStats, QueryLogEntry } from "@/lib/types";

export default function DiagnosticsPage() {
  const [stats, setStats] = useState<LatencyStats | null>(null);
  const [logs, setLogs] = useState<QueryLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, logsData] = await Promise.all([
          getLatencyStats(),
          getQueryLogs(20),
        ]);
        setStats(statsData);
        setLogs(logsData);
      } catch (err) {
        console.error("Failed to load diagnostics", err);
        setError("Could not load diagnostic data.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <div className="page-container">Loading diagnostics...</div>;
  if (error) return <div className="page-container error-text">{error}</div>;
  if (!stats) return null;

  return (
    <div className="page-container">
      <header className="page-header">
        <h1>Observability Diagnostics</h1>
        <p className="subtitle">System performance, cache efficiency, and query logs.</p>
      </header>

      {/* Aggregate Stats (Plan.md §21.3) */}
      <h2 style={{ marginBottom: "16px" }}>Performance Stats</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_reviews}</div>
          <div className="stat-label">Total Queries</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{(stats.cache_hit_rate * 100).toFixed(1)}%</div>
          <div className="stat-label">Cache Hit Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_llm_calls}</div>
          <div className="stat-label">LLM Calls Made</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.avg_latency_ms}ms</div>
          <div className="stat-label">Avg Total Latency</div>
        </div>
      </div>

      {/* Pipeline Stage Averages */}
      <h2 style={{ marginTop: "48px", marginBottom: "16px" }}>Stage Latency (Avg)</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.stage_averages.intent_ms || 0}ms</div>
          <div className="stat-label">Intent Classify</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.stage_averages.cache_ms || 0}ms</div>
          <div className="stat-label">Cache Lookup</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {((stats.stage_averages.segment_ms || 0) + (stats.stage_averages.classify_ms || 0) + (stats.stage_averages.gap_check_ms || 0)).toFixed(0)}ms
          </div>
          <div className="stat-label">Deterministic Pipeline</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.stage_averages.llm_ms || 0}ms</div>
          <div className="stat-label">LLM Call</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.stage_averages.grounding_ms || 0}ms</div>
          <div className="stat-label">Grounding Check</div>
        </div>
      </div>

      {/* Query Logs */}
      <h2 style={{ marginTop: "48px", marginBottom: "16px" }}>Recent Queries</h2>
      <div style={{ overflowX: "auto" }}>
        <table className="logs-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Contract / Category</th>
              <th>Mode</th>
              <th>Cache?</th>
              <th>Grounding</th>
              <th>LLM Retries</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td style={{ whiteSpace: "nowrap" }}>
                  {new Date(log.created_at).toLocaleTimeString()}
                </td>
                <td>
                  <span className="mono-id">{log.contract_id}</span> / {log.category}
                </td>
                <td>
                  {log.input_mode}
                  {log.intent_ambiguous && <span style={{ color: "var(--color-error)", marginLeft: "4px" }}>(Ambiguous)</span>}
                </td>
                <td>
                  {log.cache_hit ? (
                    <span style={{ color: "var(--color-risk-low)", fontWeight: 500 }}>HIT</span>
                  ) : (
                    <span style={{ color: "var(--color-ink-soft)" }}>MISS</span>
                  )}
                </td>
                <td>{log.grounding_method || "-"}</td>
                <td>{log.llm_retries > 0 ? <span style={{ color: "var(--color-risk-medium)" }}>{log.llm_retries}</span> : "0"}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "32px", color: "var(--color-ink-soft)" }}>
                  No queries logged yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
