import { useApi } from "../hooks/useApi";
import { getRootCauses } from "../services/api";
import TiltCard from "../components/TiltCard";
import { LoadingView, ErrorView, EmptyView } from "../components/StateViews";

export default function RootCausesPage() {
  const { data, loading, error, reload } = useApi(getRootCauses);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Pattern Analysis</span>
          <h1>Root Causes</h1>
          <p className="page-sub">
            Facilities with repeat stockout risk patterns and evidence-backed systemic root causes.
          </p>
        </div>
      </div>

      {loading && <LoadingView label="Loading root-cause analysis" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyView
          title="Root-cause analysis unavailable"
          message="Root-cause analysis will be available once Phase 5 is deployed."
        />
      )}

      {data && data.length > 0 && (
        <div className="stack">
          {data.map((entry, idx) => (
            <TiltCard flat key={`${entry.facility_id}-${entry.medicine_id}-${idx}`}>
              <div className="row-between" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 className="section-title" style={{ marginBottom: 0 }}>
                  Facility: {entry.facility_id} — {entry.medicine_id}
                </h3>
                <span className="cause-label" style={{ padding: "4px 10px", borderRadius: "6px", background: "var(--teal-500)", color: "#fff", fontWeight: "bold", fontSize: "12px" }}>
                  {entry.pattern_label}
                </span>
              </div>
              <div style={{ marginTop: "12px" }}>
                <p className="kpi-sub" style={{ fontWeight: 600, color: "var(--ink-700)" }}>
                  Evidence:
                </p>
                <p className="kpi-sub" style={{ marginTop: "4px" }}>
                  {entry.evidence}
                </p>
              </div>
            </TiltCard>
          ))}
        </div>
      )}
    </>
  );
}
