import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { getRescueCaseDetails, recommendTransfer, submitFeedback } from "../services/api";
import TiltCard from "../components/TiltCard";
import VialBar from "../components/VialBar";
import ApprovalBanner from "../components/ApprovalBanner";
import { LoadingView, ErrorView } from "../components/StateViews";

export default function TransferPage() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const numericCaseId = Number(caseId);

  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [decided, setDecided] = useState<"APPROVED" | "REJECTED" | null>(null);

  const { data: caseDetails, loading: loadingCase, error: errorCase, reload: reloadCase } = useApi(
    () => getRescueCaseDetails(numericCaseId),
    [numericCaseId]
  );

  const facilityId = caseDetails?.case.facility_id;
  const medicineId = caseDetails?.case.medicine_id;

  const { data: transferRec, loading: loadingRec, error: errorRec, reload: reloadRec } = useApi(
    async () => {
      if (!facilityId || !medicineId) return null;
      return recommendTransfer(facilityId, medicineId);
    },
    [facilityId, medicineId]
  );

  const loading = loadingCase || (Boolean(facilityId) && loadingRec);
  const error = errorCase || errorRec;
  const rec = transferRec || caseDetails?.transfer_recommendation;

  async function handleDecision(decision: "APPROVED" | "REJECTED") {
    setSubmitting(true);
    try {
      await submitFeedback({
        case_id: numericCaseId,
        officer_decision: decision,
        notes: notes.trim() || undefined,
      });
      setDecided(decision);
    } catch {
      /* Handled gracefully */
    } finally {
      setSubmitting(false);
    }
  }

  const isNoDonorOrNotNeeded =
    rec && (rec.status === "no_safe_donor_available" || rec.status === "NOT_NEEDED");

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Transfer recommendation · Case #{caseId}</span>
          <h1>Proposed rescue transfer</h1>
        </div>
      </div>

      <ApprovalBanner text="Officer approval required — this transfer will not move until you approve it." />

      {loading && <LoadingView label="Calculating recommendation" />}
      {error && <ErrorView message={error} onRetry={() => { reloadCase(); reloadRec(); }} />}

      {rec && (
        <TiltCard flat>
          <div className="transfer-route">
            <div className="transfer-node">
              <div className="node-role">Donor Facility</div>
              <div className="node-name">
                {rec.donor_facility_name || rec.donor_facility_id || "None"}
              </div>
            </div>
            <span className="transfer-arrow">→</span>
            <div className="transfer-node">
              <div className="node-role">Recipient Facility</div>
              <div className="node-name">
                {rec.recipient_facility_name || rec.recipient_facility_id}
              </div>
            </div>
          </div>

          <div className="grid-2" style={{ margin: "20px 0" }}>
            <div>
              <div className="kpi-label">Quantity & Distance</div>
              <p style={{ fontWeight: 700, fontSize: "1.1rem" }}>
                {rec.quantity} units · {rec.distance_km} km
              </p>
            </div>
            <div>
              <div className="kpi-label">Target Cover</div>
              <p style={{ fontWeight: 700, fontSize: "1.1rem" }}>
                {rec.covers_days} days of demand
              </p>
            </div>
          </div>

          {rec.quantity > 0 && (
            <div style={{ marginBottom: 18 }}>
              <div className="kpi-label" style={{ marginBottom: 8 }}>
                Proposed Transfer Volume
              </div>
              <VialBar
                value={rec.quantity}
                max={Math.max(rec.quantity, 100)}
                safetyThreshold={rec.quantity * 0.3}
                riskLevel="OK"
                label="Transfer Units"
              />
            </div>
          )}

          <div style={{ margin: "16px 0", padding: 14, background: "var(--glass-fill)", borderRadius: 12 }}>
            <div className="kpi-label" style={{ marginBottom: 4 }}>Fairness Proof & Logic</div>
            <p style={{ color: "var(--ink-800)", fontWeight: 500, fontSize: "var(--fs-small)" }}>
              {rec.fairness_proof}
            </p>
          </div>

          {rec.reason && (
            <p style={{ marginTop: 12, color: "var(--ink-700)", fontSize: "var(--fs-small)" }}>
              {rec.reason}
            </p>
          )}

          {rec.alternative_considered && (
            <div className="verify-note" style={{ marginTop: 14 }}>
              <strong>Alternative Considered:</strong> {rec.alternative_considered}
            </div>
          )}

          {isNoDonorOrNotNeeded ? (
            <div className="report-item warning" style={{ marginTop: 20 }}>
              No transfer can be executed: {rec.reason}
            </div>
          ) : decided ? (
            <div
              style={{
                marginTop: 20,
                padding: 14,
                borderRadius: 10,
                fontWeight: 700,
                background: decided === "APPROVED" ? "var(--risk-low-bg)" : "var(--risk-critical-bg)",
                color: decided === "APPROVED" ? "var(--risk-low)" : "var(--risk-critical)",
              }}
            >
              Decision recorded: {decided}.{" "}
              {notes && <span style={{ fontWeight: 400 }}>("{notes}")</span>}
              <div style={{ marginTop: 12 }}>
                <button className="btn btn-ghost" onClick={() => navigate("/rescue-queue")}>
                  Back to queue
                </button>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--glass-border-soft)" }}>
              <div className="field" style={{ marginBottom: 14 }}>
                <label htmlFor="officer-notes">Officer Review Notes (Optional)</label>
                <input
                  id="officer-notes"
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Enter reasoning or approval notes..."
                />
              </div>
              <div className="action-row">
                <button
                  className="btn btn-approve"
                  disabled={submitting}
                  onClick={() => handleDecision("APPROVED")}
                >
                  Approve transfer
                </button>
                <button
                  className="btn btn-danger"
                  disabled={submitting}
                  onClick={() => handleDecision("REJECTED")}
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </TiltCard>
      )}
    </>
  );
}
