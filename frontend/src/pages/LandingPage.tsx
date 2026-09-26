import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import TiltCard from "../components/TiltCard";
import HeroParallax from "../components/HeroParallax";
import { VialIcon, UploadIcon } from "../components/icons";
import { generateDemoData, uploadInventory } from "../services/api";
import type { UploadReport } from "../types/api";

export default function LandingPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [report, setReport] = useState<UploadReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleDemoData() {
    setBusy(true);
    setErrorMsg(null);
    try {
      const result = await generateDemoData();
      setReport({
        rows_processed: result.inventory_records_count,
        accepted: true,
        errors: [],
        warnings: [],
      });
    } catch (err: any) {
      setErrorMsg(err.message ?? "Could not generate demo data.");
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(file: File) {
    setBusy(true);
    setErrorMsg(null);
    try {
      const result = await uploadInventory(file);
      setReport(result);
    } catch (err: any) {
      setErrorMsg(err.message ?? "Could not upload that file.");
    } finally {
      setBusy(false);
    }
  }

  const canProceed = Boolean(report && report.accepted && report.errors.length === 0);

  return (
    <div className="landing-hero" style={{ position: "relative", overflow: "hidden" }}>
      <HeroParallax />
      <div className="brand-row" style={{ position: "relative", zIndex: 1 }}>
        <VialIcon size={30} />
        <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>MedTrace</span>
      </div>
      <div style={{ position: "relative", zIndex: 1 }}>
        <h1>Load inventory to begin</h1>
        <p className="page-sub">
          Pull in demo data to explore MedTrace, or upload your facility's
          real inventory CSV. Nothing reaches the dashboard until the
          validator has reviewed it.
        </p>
      </div>

      <div style={{ position: "relative", zIndex: 1, maxWidth: 560, width: "100%" }}>
        <TiltCard flat>
          <button
            className="btn btn-primary btn-block"
            onClick={handleDemoData}
            disabled={busy}
          >
            {busy ? "Working…" : "Load demo data"}
          </button>

          <div className="divider-or" style={{ margin: "18px 0" }}>
            or
          </div>

          <label
            className={`dropzone ${dragging ? "dragging" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const file = e.dataTransfer.files?.[0];
              if (file) handleFile(file);
            }}
          >
            <UploadIcon />
            <p style={{ marginTop: 8, fontWeight: 600, color: "var(--ink-700)" }}>
              Drop an inventory CSV here, or click to choose a file
            </p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </label>

          {errorMsg && (
            <p style={{ color: "var(--risk-critical)", marginTop: 12, fontSize: "var(--fs-small)" }}>
              {errorMsg}
            </p>
          )}

          {report && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontWeight: 700, fontSize: "var(--fs-small)" }}>
                {report.rows_processed} row{report.rows_processed === 1 ? "" : "s"}{" "}
                processed
                {report.accepted ? " — ready to proceed." : " — fix the issues below."}
              </p>
              {(report.errors.length > 0 || report.warnings.length > 0) && (
                <ul className="report-list">
                  {report.errors.map((e, i) => (
                    <li className="report-item error" key={`err-${i}`}>
                      {e.row != null && e.row > 0 ? `Row ${e.row}: ` : ""}
                      {e.message}
                    </li>
                  ))}
                  {report.warnings.map((w, i) => (
                    <li className="report-item warning" key={`warn-${i}`}>
                      {w.row != null && w.row > 0 ? `Row ${w.row}: ` : ""}
                      {w.message}
                    </li>
                  ))}
                </ul>
              )}
              <button
                className="btn btn-primary btn-block"
                style={{ marginTop: 16 }}
                disabled={!canProceed}
                onClick={() => navigate("/dashboard")}
              >
                Continue to dashboard
              </button>
            </div>
          )}
        </TiltCard>
      </div>
    </div>
  );
}
