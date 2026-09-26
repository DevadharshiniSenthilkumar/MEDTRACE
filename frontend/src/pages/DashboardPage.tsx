import { useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { getDashboardSummary } from "../services/api";
import ApprovalBanner from "../components/ApprovalBanner";
import KpiCard from "../components/KpiCard";
import TiltCard from "../components/TiltCard";
import { LoadingView, ErrorView } from "../components/StateViews";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(getDashboardSummary);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Overview</span>
          <h1>Dashboard</h1>
        </div>
      </div>

      <ApprovalBanner text="Officer approval required — MedTrace recommends, it never authorizes or moves stock automatically." />

      {loading && <LoadingView label="Loading dashboard summary" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && (
        <div className="stack" style={{ gap: 24 }}>
          <div className="kpi-grid">
            <KpiCard
              label="Facilities at risk"
              value={data.facilities_at_risk}
              sub={`of ${data.total_facilities} tracked facilities`}
              accent
            />
            <KpiCard
              label="Critical vs watch stockouts"
              value={`${data.critical_stockouts} / ${data.watch_stockouts}`}
              sub="Critical & Watch items requiring attention"
            />
            <KpiCard
              label="Unverified stock reports"
              value={data.unverified_reports}
              sub="Require physical count verification"
            />
            <KpiCard
              label="OK status count"
              value={data.ok_status_count}
              sub={`Stable stock levels across facilities`}
            />
          </div>

          <TiltCard flat>
            <h3 className="section-title">Navigation & Tools</h3>
            <div className="grid-2">
              <button
                className="btn btn-primary"
                onClick={() => navigate("/rescue-queue")}
              >
                Go to Rescue Queue
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => navigate("/surplus")}
              >
                Surplus & Expiry Explorer
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => navigate("/root-causes")}
              >
                Root-Cause Analysis
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => navigate("/history")}
              >
                Officer Feedback & History
              </button>
            </div>
          </TiltCard>
        </div>
      )}
    </>
  );
}
