import { useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { getRescueQueue } from "../services/api";
import TiltCard from "../components/TiltCard";
import RiskPill from "../components/RiskPill";
import { TruthScoreBadge } from "../components/TruthScoreBadge";
import { LoadingView, ErrorView, EmptyView } from "../components/StateViews";

export default function RescueQueuePage() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(getRescueQueue);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Prioritized</span>
          <h1>Rescue queue</h1>
          <p className="page-sub">
            Ranked by urgency. Open a case to see the forecast, truth
            score breakdown, and the recommended action.
          </p>
        </div>
      </div>

      {loading && <LoadingView label="Loading rescue queue" />}
      {error && <ErrorView message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyView
          title="No active rescue cases right now."
          message="All facility medicine pairs are operating within normal safe thresholds."
        />
      )}

      {data && data.length > 0 && (
        <TiltCard flat>
          <table className="mt-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Facility</th>
                <th>Medicine</th>
                <th>Risk level</th>
                <th>Truth score</th>
                <th>Confidence</th>
                <th>Recommended action</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr
                  key={item.case_id}
                  className="mt-row-link"
                  onClick={() => navigate(`/cases/${item.case_id}`)}
                >
                  <td style={{ fontFamily: "var(--font-data)" }}>#{item.case_id}</td>
                  <td style={{ fontWeight: 600 }}>{item.facility_id}</td>
                  <td>{item.medicine_id}</td>
                  <td>
                    <RiskPill level={item.risk_level} />
                  </td>
                  <td>
                    <TruthScoreBadge score={item.stock_truth_score} />
                  </td>
                  <td style={{ fontFamily: "var(--font-data)" }}>
                    {Math.round(item.confidence)}%
                  </td>
                  <td className="queue-reasoning">{item.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TiltCard>
      )}
    </>
  );
}
