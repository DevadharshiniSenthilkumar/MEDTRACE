import { useParams, useNavigate, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useApi } from "../hooks/useApi";
import { getRescueCaseDetails } from "../services/api";
import TiltCard from "../components/TiltCard";
import RiskPill from "../components/RiskPill";
import { TruthScoreBreakdownBars } from "../components/TruthScoreBadge";
import ApprovalBanner from "../components/ApprovalBanner";
import { LoadingView, ErrorView } from "../components/StateViews";

export default function CaseDetailPage() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const numericCaseId = Number(caseId);

  const { data, loading, error, reload } = useApi(
    () => getRescueCaseDetails(numericCaseId),
    [numericCaseId]
  );

  const forecastChartData = data?.analysis.demand_forecast.last_14_days.map((val, idx) => ({
    day: `Day ${idx + 1}`,
    issued: val,
    forecast: data.analysis.demand_forecast.forecast_per_day,
  })) ?? [];

  const truthScore = data?.analysis.stock_truth.total ?? 0;
  const riskLevel = data?.analysis.risk_assessment.risk_level ?? "OK";
  const isTruthLow = truthScore < 50;
  const isHighRisk = riskLevel === "CRITICAL" || riskLevel === "HIGH";

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Rescue case #{caseId}</span>
          <h1>
            {data
              ? `${data.analysis.medicine_id} · ${data.analysis.facility_id}`
              : "Case detail"}
          </h1>
        </div>
      </div>

      <ApprovalBanner text="Officer approval required before any transfer is confirmed." />

      {loading && <LoadingView label="Loading case details" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && (
        <div className="stack" style={{ gap: 20 }}>
          <div className="case-meta-grid">
            <TiltCard flat>
              <div className="meta-block">
                <div className="kpi-label">Days remaining</div>
                <div className="kpi-value">
                  {data.analysis.inventory_status.days_remaining.toFixed(1)}
                </div>
              </div>
            </TiltCard>
            <TiltCard flat>
              <div className="meta-block">
                <div className="kpi-label">Risk level</div>
                <RiskPill level={data.analysis.risk_assessment.risk_level} />
                <div className="kpi-sub" style={{ marginTop: 6 }}>
                  Confidence: {Math.round(data.analysis.risk_assessment.confidence)}%
                </div>
              </div>
            </TiltCard>
            <TiltCard flat>
              <div className="meta-block">
                <div className="kpi-label">Current stock</div>
                <div className="kpi-value">
                  {data.analysis.inventory_status.current_stock.toFixed(0)}
                </div>
                <div className="kpi-sub">
                  Safety stock: {data.analysis.inventory_status.safety_stock.toFixed(0)}
                </div>
              </div>
            </TiltCard>
          </div>

          <TiltCard flat>
            <h3 className="section-title">Demand forecast (14-Day History & Rate)</h3>
            <div className="chart-wrap" style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecastChartData}>
                  <CartesianGrid stroke="var(--glass-border-soft)" strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "var(--ink-500)" }} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--ink-500)" }} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--glass-fill-strong)",
                      border: "1px solid var(--glass-border)",
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="issued"
                    stroke="var(--teal-600)"
                    strokeWidth={2.5}
                    dot={true}
                    name="Daily Issued"
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="var(--blue-600)"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    dot={false}
                    name="Forecast per day"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="kpi-sub" style={{ marginTop: 10 }}>
              {data.analysis.demand_forecast.reasoning}
            </p>
          </TiltCard>

          <div className="grid-2">
            <TiltCard flat>
              <h3 className="section-title">
                Stock Truth Score: {Math.round(truthScore)} / 100
              </h3>
              <TruthScoreBreakdownBars breakdown={data.analysis.stock_truth} />
              <p className="kpi-sub" style={{ marginTop: 12 }}>
                {data.analysis.stock_truth.reason}
              </p>
            </TiltCard>

            <TiltCard flat>
              <h3 className="section-title">Recommended Action</h3>
              <p style={{ color: "var(--ink-700)", fontWeight: 500, fontSize: "0.95rem" }}>
                {data.analysis.risk_assessment.recommended_action}
              </p>

              {isTruthLow ? (
                <div style={{ marginTop: 16 }}>
                  <div
                    className="report-item error"
                    style={{ marginBottom: 14, fontWeight: 600 }}
                  >
                    Verification required — stock truth score too low to trust this reading.
                  </div>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => navigate(`/cases/${caseId}/simulate`)}
                  >
                    Verify Physical Count
                  </button>
                </div>
              ) : (
                <div className="stack" style={{ marginTop: 16, gap: 10 }}>
                  {isHighRisk && (
                    <Link
                      className="btn btn-primary btn-block"
                      to={`/cases/${caseId}/transfer`}
                    >
                      View Transfer Recommendation
                    </Link>
                  )}
                  <button
                    className="btn btn-ghost btn-block"
                    onClick={() => navigate(`/cases/${caseId}/simulate`)}
                  >
                    Verify Physical Count
                  </button>
                </div>
              )}
            </TiltCard>
          </div>
        </div>
      )}
    </>
  );
}
