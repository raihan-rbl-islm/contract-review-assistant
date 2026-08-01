"use client";

import { useState, useEffect } from "react";
import type { ContractSummary } from "@/lib/types";

interface ContractPickerProps {
  contracts: ContractSummary[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function ContractPicker({
  contracts,
  selectedId,
  onSelect,
}: ContractPickerProps) {
  return (
    <div className="contract-picker">
      <label className="picker-label">Contract</label>
      <div className="picker-grid">
        {contracts.map((c) => (
          <button
            key={c.id}
            className={`contract-card ${selectedId === c.id ? "selected" : ""}`}
            onClick={() => onSelect(c.id)}
            type="button"
          >
            <span className="contract-id">{c.id}</span>
            <span className="contract-title">{c.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
