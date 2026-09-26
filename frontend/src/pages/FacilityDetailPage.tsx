import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { useApi } from "../hooks/useApi";
import { getFacilityDetails } from "../services/api";
import TiltCard from "../components/TiltCard";
import RiskPill from "../components/RiskPill";
import { TruthScoreBadge } from "../components/TruthScoreBadge";
import { LoadingView, ErrorView } from "../components/StateViews";
import { FacilityIcon } from "../components/icons";
import type { FacilityMedicineAnalysisOut } from "../types/api";

export default function FacilityDetailPage() {
  const { facilityId = "" } = useParams<{ facilityId: string }>();
  const { data, loading, error, reload } = useApi(
    () => getFacilityDetails(facilityId),
    [facilityId]
  );
  const [selected, setSelected] = useState<FacilityMedicineAnalysisOut | null>(null);

  const active = selected ?? data?.medicines?.[0] ?? null;

  return (
    <>
      <div className="page-head">
        <div>
          <span className="page-eyebrow">Facility Detail</span>
          <div className="facility-head" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FacilityIcon size={22} />
            <h1>{data ? data.facility.name : "Facility detail"}</h1>
          </div>
          {data && (
            <p className="page-sub">
              ID: {data.facility.facility_id} | Type: {data.facility.facility_type}{" "}
              {data.facility.is_remote ? "• Remote Facility" : ""}
            </p>
          )}
        </div>
      </div>

      {loading && <LoadingView label="Loading facility details" />}
      {error && <ErrorView message={error} onRetry={reload} />}

      {data && (
        <div className="stack">
          {active && (
            <TiltCard flat>
              <h3 className="section-title">
                Medicine: {active.medicine_id} — Stock vs. Safety Threshold
              </h3>
              <div className="chart-wrap" style={{ height: "300px", width: "100%", marginTop: "1rem" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: "Current stock", value: active.inventory_status.current_stock },
                      { name: "7-day forecast", value: active.demand_forecast.forecast_7day },
                    ]}
                  >
                    <CartesianGrid stroke="var(--glass-border-soft)" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--ink-500)" }} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--ink-500)" }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--glass-fill-strong)",
                        border: "1px solid var(--glass-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <ReferenceLine
                      y={active.inventory_status.safety_stock}
                      stroke="var(--ink-900)"
                      strokeDasharray="6 4"
                      label={{
                        value: "Safety threshold",
                        position: "right",
                        fontSize: 11,
                        fill: "var(--ink-700)",
                      }}
                    />
                    <Bar dataKey="value" fill="var(--teal-500)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </TiltCard>
          )}

          <TiltCard flat>
            <h3 className="section-title">Medicines at this facility</h3>
            <table className="mt-table">
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Stock</th>
                  <th>Safety Stock</th>
                  <th>Demand (avg/day)</th>
                  <th>7-day forecast</th>
                  <th>Truth score</th>
                  <th>Days remaining</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.medicines.map((m) => (
                  <tr
                    key={m.medicine_id}
                    className="mt-row-link"
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelected(m)}
                  >
                    <td style={{ fontWeight: m.medicine_id === active?.medicine_id ? "bold" : "normal" }}>
                      {m.medicine_id}
                    </td>
                    <td style={{ fontFamily: "var(--font-data)" }}>{m.inventory_status.current_stock}</td>
                    <td style={{ fontFamily: "var(--font-data)" }}>{m.inventory_status.safety_stock}</td>
                    <td style={{ fontFamily: "var(--font-data)" }}>{m.inventory_status.avg_daily_demand}</td>
                    <td style={{ fontFamily: "var(--font-data)" }}>{m.demand_forecast.forecast_7day}</td>
                    <td>
                      <TruthScoreBadge score={m.stock_truth.total} />
                    </td>
                    <td style={{ fontFamily: "var(--font-data)" }}>{m.inventory_status.days_remaining}</td>
                    <td>
                      <RiskPill level={m.risk_assessment.risk_level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TiltCard>
        </div>
      )}
    </>
  );
}
