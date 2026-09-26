import type { RiskLevel } from "../types/api";

const LABELS: Record<RiskLevel, string> = {
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
  OK: "OK",
};

export default function RiskPill({ level }: { level: RiskLevel }) {
  return (
    <span className="risk-pill" data-risk={level}>
      <span className="pill-cap" />
      {LABELS[level] ?? level}
    </span>
  );
}
