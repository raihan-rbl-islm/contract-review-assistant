"use client";

export default function LoadingState() {
  return (
    <div className="loading-state">
      <div className="loading-spinner" />
      <p className="loading-text">Reviewing clause...</p>
      <p className="loading-subtext">Comparing against company standard</p>
    </div>
  );
}
