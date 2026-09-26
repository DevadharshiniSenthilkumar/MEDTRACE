import type { RiskLevel } from "../types/api";

interface VialBarProps {
  /** Current level as a value between 0 and `max`. */
  value: number;
  max: number;
  /** Where the safety threshold sits, same units as value/max. */
  safetyThreshold?: number;
  riskLevel: RiskLevel;
  label?: string;
}

export default function VialBar({
  value,
  max,
  safetyThreshold,
  riskLevel,
  label,
}: VialBarProps) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const thresholdPct =
    safetyThreshold != null && max > 0
      ? Math.max(0, Math.min(100, (safetyThreshold / max) * 100))
      : null;

  return (
    <div className="vial" data-risk={riskLevel}>
      <div className="vial-track" role="img" aria-label={`Stock level ${value} of ${max}`}>
        <div className="vial-fill" style={{ width: `${pct}%` }} />
        {thresholdPct != null && (
          <div
            className="vial-safety-line"
            style={{ left: `${thresholdPct}%` }}
            title={`Safety threshold: ${safetyThreshold}`}
          />
        )}
      </div>
      <div className="vial-label">
        <span>{label ?? "Stock"}</span>
        <span>
          {value.toLocaleString()} / {max.toLocaleString()}
        </span>
      </div>
    </div>
  );
}
