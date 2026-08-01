"use client";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state">
      <p className="error-icon">⚠</p>
      <p className="error-message">{message}</p>
      {onRetry && (
        <button className="error-retry-btn" onClick={onRetry} type="button">
          Try Again
        </button>
      )}
    </div>
  );
}
