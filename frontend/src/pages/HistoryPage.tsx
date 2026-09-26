import { useApi } from "../hooks/useApi";
import { getFeedbackHistory } from "../services/api";
import TiltCard from "../components/TiltCard";
import RiskPill from "../components/RiskPill";
import { LoadingView, ErrorView, EmptyView } from "../components/StateViews";

function DecisionBadge({ decision }: { decision: string }) {
  let bg = "rgba(107, 114, 128, 0.15)";
  let color = "#4b5563";
  const upper = (decision || "").toUpperCase();

  if (upper === "APPROVED") {
    bg = "rgba(16, 185, 129, 0.15)";
    color = "#10b981";
  } else if (upper === "REJECTED") {
    bg = "rgba(239, 68, 68, 0.15)";
    color = "#ef4444";
  } else if (upper === "VERIFIED") {
    bg = "rgba(59, 130, 246, 0.15)";
    color = "#3b82f6";
  }

  return (
    <span
      style={{
        background: bg,
        color,
        padding: "4px 10px",
        borderRadius: "6px",
        fontSize: "12px",
        fontWeight: "bold",
        display: "inline-block",
      }}
    >
      {upper}
    </span>
  );
}

export default function HistoryPage() {
  const { data, loading, error, reload } = useApi(getFeedbackHistory);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Accountability Log</span>
          <h1>Feedback & History</h1>
          <p className="page-sub">
            Audit log of past officer decisions, verification overrides, and transfer approvals.
          </p>
        </div>
      </div>

      {loading && <LoadingView label="Loading decision history" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyView
          title="No officer decisions recorded yet"
          message="Approvals, rejections, and stock verification overrides will appear here once recorded."
        />
      )}

      {data && data.length > 0 && (
        <TiltCard flat>
          <table className="mt-table">
            <thead>
              <tr>
                <th>Feedback ID</th>
                <th>Case ID</th>
                <th>Facility</th>
                <th>Medicine</th>
                <th>Risk Level</th>
                <th>Officer Decision</th>
                <th>Notes</th>
                <th>Decided At</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.feedback_id}>
                  <td style={{ fontFamily: "var(--font-data)" }}>#{item.feedback_id}</td>
                  <td style={{ fontFamily: "var(--font-data)" }}>
                    {item.case_id ? `#${item.case_id}` : "N/A"}
                  </td>
                  <td>{item.facility_id || "N/A"}</td>
                  <td>{item.medicine_id || "N/A"}</td>
                  <td>
                    {item.risk_level ? (
                      <RiskPill level={item.risk_level} />
                    ) : (
                      <span className="kpi-sub">—</span>
                    )}
                  </td>
                  <td>
                    <DecisionBadge decision={item.officer_decision} />
                  </td>
                  <td style={{ fontSize: "12px", color: "var(--ink-700)", maxWidth: "240px" }}>
                    {item.notes || "No notes entered"}
                  </td>
                  <td className="kpi-sub" style={{ fontSize: "11px" }}>
                    {item.decided_at}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TiltCard>
      )}
    </>
  );
}
