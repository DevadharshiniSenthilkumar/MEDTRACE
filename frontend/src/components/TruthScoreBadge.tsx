import type { StockTruthOut } from "../types/api";

export function TruthScoreBadge({ score }: { score: number }) {
  const tone =
    score >= 80 ? "var(--risk-low)" : score >= 50 ? "var(--risk-high)" : "var(--risk-critical)";
  return (
    <span className="truth-badge">
      <span className="truth-value" style={{ color: tone }}>
        {Math.round(score)}
      </span>
      <span className="truth-label">Truth score</span>
    </span>
  );
}

const ROWS: { key: "recency_score" | "completeness_score" | "consistency_score"; label: string }[] = [
  { key: "recency_score", label: "Recency" },
  { key: "completeness_score", label: "Completeness" },
  { key: "consistency_score", label: "Consistency" },
];

export function TruthScoreBreakdownBars({
  breakdown,
}: {
  breakdown: StockTruthOut;
}) {
  return (
    <div className="stack" style={{ gap: 10 }}>
      {ROWS.map(({ key, label }) => (
        <div className="truth-bar-row" key={key}>
          <span>{label}</span>
          <span className="truth-bar-track">
            <span
              className="truth-bar-fill"
              style={{ width: `${Math.max(0, Math.min(100, breakdown[key]))}%` }}
            />
          </span>
          <span className="truth-bar-value">{Math.round(breakdown[key])}</span>
        </div>
      ))}
    </div>
  );
}
