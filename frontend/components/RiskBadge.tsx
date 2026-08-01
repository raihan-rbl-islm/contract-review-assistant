"use client";

import type { RiskLevel } from "@/lib/types";

interface RiskBadgeProps {
  riskLevel: RiskLevel;
}

const RISK_CONFIG: Record<
  RiskLevel,
  { className: string; label: string }
> = {
  "Low Risk": { className: "risk-low", label: "Low" },
  "Medium Risk": { className: "risk-medium", label: "Medium" },
  "High Risk": { className: "risk-high", label: "High" },
  "Not Enough Information": { className: "risk-unknown", label: "N/A" },
};

export default function RiskBadge({ riskLevel }: RiskBadgeProps) {
  const config = RISK_CONFIG[riskLevel];

  return (
    <div className={`risk-badge ${config.className}`} aria-label={`Risk level: ${riskLevel}`}>
      <span className="risk-badge-label">{config.label}</span>
      <span className="risk-badge-sublabel">Risk</span>
    </div>
  );
}
