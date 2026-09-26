import TiltCard from "./TiltCard";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}

export default function KpiCard({ label, value, sub, accent }: KpiCardProps) {
  return (
    <TiltCard flat>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${accent ? "accent" : ""}`}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </TiltCard>
  );
}
