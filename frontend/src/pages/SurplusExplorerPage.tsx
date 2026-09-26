import { useApi } from "../hooks/useApi";
import { getSurplusSummary } from "../services/api";
import TiltCard from "../components/TiltCard";
import VialBar from "../components/VialBar";
import RiskPill from "../components/RiskPill";
import { TruthScoreBadge } from "../components/TruthScoreBadge";
import { LoadingView, ErrorView } from "../components/StateViews";

export default function SurplusExplorerPage() {
  const { data, loading, error, reload } = useApi(getSurplusSummary);

  const eligibleSurplus = data?.eligible_surplus ?? [];
  const nearExpiryCandidates = data?.near_expiry_candidates ?? [];

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Proactive browsing</span>
          <h1>Surplus & Expiry Explorer</h1>
          <p className="page-sub">
            Facilities holding verified surplus stock and batches nearing expiry that can prevent stockouts.
          </p>
        </div>
      </div>

      {loading && <LoadingView label="Loading surplus & expiry data" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && (
        <div className="stack" style={{ gap: "2rem" }}>
          {/* Section 1: Eligible Surplus */}
          <div>
            <h2 className="section-title" style={{ marginBottom: "1rem" }}>
              Eligible Surplus (Available Rescue Donors)
            </h2>
            {eligibleSurplus.length === 0 ? (
              <TiltCard flat>
                <p className="kpi-sub" style={{ textAlign: "center", padding: "1.5rem" }}>
                  None right now.
                </p>
              </TiltCard>
            ) : (
              <div className="surplus-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
                {eligibleSurplus.map((item, idx) => (
                  <TiltCard key={`${item.facility_id}-${item.medicine_id}-${idx}`}>
                    <div className="kpi-label">{item.facility_name || item.facility_id}</div>
                    <h3 style={{ marginBottom: 10 }}>{item.medicine_name || item.medicine_id}</h3>
                    <VialBar
                      value={item.donor_surplus}
                      max={Math.max(item.current_stock, item.safety_stock, 1)}
                      safetyThreshold={item.safety_stock}
                      riskLevel="OK"
                      label="Donor Surplus"
                    />
                    <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className="kpi-sub">Stock: {item.current_stock} (Safety: {item.safety_stock})</span>
                      <TruthScoreBadge score={item.stock_truth_score} />
                    </div>
                    {item.batch_expiry_date && (
                      <p className="kpi-sub" style={{ marginTop: "8px", fontSize: "11px" }}>
                        Batch Expiry: {item.batch_expiry_date}
                      </p>
                    )}
                  </TiltCard>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Near-Expiry Candidates */}
          <div>
            <h2 className="section-title" style={{ marginBottom: "1rem" }}>
              Near-Expiry Candidates (Batch Rescue Opportunities)
            </h2>
            {nearExpiryCandidates.length === 0 ? (
              <TiltCard flat>
                <p className="kpi-sub" style={{ textAlign: "center", padding: "1.5rem" }}>
                  None right now.
                </p>
              </TiltCard>
            ) : (
              <div className="surplus-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
                {nearExpiryCandidates.map((item, idx) => (
                  <TiltCard key={`${item.holding_facility_id}-${item.recipient_facility_id}-${idx}`}>
                    <div className="kpi-label">Holding: {item.holding_facility_name || item.holding_facility_id}</div>
                    <h3 style={{ marginBottom: 6 }}>Medicine: {item.medicine_id}</h3>
                    <p className="kpi-sub">
                      Target Recipient: <strong>{item.recipient_facility_name || item.recipient_facility_id}</strong>
                    </p>
                    <div style={{ margin: "10px 0", display: "flex", gap: "10px", alignItems: "center" }}>
                      <span className="expiry-tag" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", padding: "4px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "bold" }}>
                        Expires in {item.days_to_expiry} days
                      </span>
                      <RiskPill level={item.recipient_risk_level} />
                    </div>
                    <p className="kpi-sub" style={{ fontSize: "11px" }}>
                      Expiry Date: {item.batch_expiry_date} • Distance: {item.distance_km} km
                    </p>
                  </TiltCard>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
