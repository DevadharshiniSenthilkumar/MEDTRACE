import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import TiltCard from "../components/TiltCard";
import RiskPill from "../components/RiskPill";
import ApprovalBanner from "../components/ApprovalBanner";
import { simulateVerification, ApiError } from "../services/api";
import type { SimulateVerificationOut } from "../types/api";

export default function SimulatorPage() {
  const { caseId = "" } = useParams();
  const numericCaseId = Number(caseId);

  const [count, setCount] = useState("");
  const [result, setResult] = useState<SimulateVerificationOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSimulation(e: React.FormEvent) {
    e.preventDefault();
    const physical_count = Number(count);
    if (Number.isNaN(physical_count) || physical_count < 0) {
      setError("Enter a valid physical count.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await simulateVerification({
        case_id: numericCaseId,
        corrected_physical_count: physical_count,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Simulation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Counterfactual simulator</span>
          <h1>Verify physical count</h1>
          <p className="page-sub">
            Enter what an officer counted on the shelf. This shows what
            would change based on physical verification.
          </p>
        </div>
      </div>

      <ApprovalBanner text="This is a simulation only — officer approval is still required to act on any resulting recommendation." />

      <TiltCard flat>
        <form onSubmit={runSimulation}>
          <div className="field">
            <label htmlFor="physical-count">New physical stock count</label>
            <input
              id="physical-count"
              type="number"
              min={0}
              value={count}
              onChange={(e) => setCount(e.target.value)}
              placeholder="e.g. 120"
              required
            />
            <span className="field-hint">Units actually counted at the facility shelf.</span>
          </div>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Simulating…" : "Run Simulation"}
          </button>
          {error && (
            <p style={{ color: "var(--risk-critical)", marginTop: 10, fontSize: "var(--fs-small)" }}>
              {error}
            </p>
          )}
        </form>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              style={{ marginTop: 24 }}
            >
              <div className="sim-compare">
                <motion.div
                  className="sim-panel"
                  initial={{ scale: 0.94 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.35 }}
                >
                  <div className="sim-tag">Before Simulation</div>
                  <div className="sim-score">
                    Truth: {Math.round(result.before.analysis.stock_truth.total)}
                  </div>
                  <div style={{ margin: "10px 0" }}>
                    <RiskPill level={result.before.analysis.risk_assessment.risk_level} />
                  </div>
                  <div className="kpi-sub">
                    {result.before.analysis.inventory_status.days_remaining.toFixed(1)} days remaining
                  </div>
                  <div className="kpi-sub" style={{ marginTop: 4 }}>
                    Transfer Status: {result.before.recommendation.status ?? "None"}
                  </div>
                </motion.div>

                <div className="sim-arrow">→</div>

                <motion.div
                  className="sim-panel"
                  initial={{ scale: 0.9, boxShadow: "0 0 0 rgba(0,0,0,0)" }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.45, delay: 0.15 }}
                  style={{
                    background:
                      result.status_action === "CANCELLED"
                        ? "var(--risk-low-bg)"
                        : result.status_action === "RE_REVIEW_REQUIRED"
                        ? "var(--risk-high-bg)"
                        : "var(--base-300)",
                  }}
                >
                  <div className="sim-tag">After Simulation</div>
                  <div className="sim-score">
                    Truth: {Math.round(result.after.analysis.stock_truth.total)}
                  </div>
                  <div style={{ margin: "10px 0" }}>
                    <RiskPill level={result.after.analysis.risk_assessment.risk_level} />
                  </div>
                  <div className="kpi-sub">
                    {result.after.analysis.inventory_status.days_remaining.toFixed(1)} days remaining
                  </div>
                  <div className="kpi-sub" style={{ marginTop: 4 }}>
                    Transfer Status: {result.after.recommendation.status ?? "None"}
                  </div>
                </motion.div>
              </div>

              {result.status_action === "RE_REVIEW_REQUIRED" && (
                <div className="report-item warning" style={{ marginTop: 16, fontWeight: 700 }}>
                  This case has an approved transfer already in motion — officer re-review required.
                </div>
              )}

              {result.status_action === "CANCELLED" && (
                <div className="report-item" style={{ marginTop: 16, fontWeight: 700, background: "var(--risk-low-bg)", color: "var(--risk-low)" }}>
                  Transfer no longer needed — risk reduced to safe levels.
                </div>
              )}

              <p className="sim-narrative" style={{ marginTop: 14 }}>
                {result.reasoning}
              </p>

              <Link
                className="btn btn-ghost"
                style={{ marginTop: 16, display: "inline-flex" }}
                to={`/cases/${caseId}`}
              >
                Back to Case Details
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </TiltCard>
    </>
  );
}
