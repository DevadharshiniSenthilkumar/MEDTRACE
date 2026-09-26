from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sqlite3
from datetime import datetime

from app.database import init_db, get_db_connection
from app.schemas import (
    DashboardSummaryOut,
    DemoDataGenerationResponse,
    InventoryStatusOut,
    ForecastOut,
    StockTruthOut,
    RiskOut,
    FacilityMedicineAnalysisOut,
    TransferRecommendation,
    SimulateVerificationIn,
    SimulateVerificationOut,
    RescueCaseOut
)
from app.synthetic_data import generate_demo_dataset
from app.inventory_engine import compute_inventory_status
from app.forecast_engine import compute_demand_forecast
from app.stock_truth_engine import compute_stock_truth_score
from app.stockout_risk_engine import compute_stockout_risk, save_rescue_case
from app.surplus_engine import find_eligible_donors, find_near_expiry_matches
from app.transfer_optimizer import optimize_rescue_transfer

app = FastAPI(
    title="MedTrace API",
    description="Decision support system for medicine stockout prevention",
    version="1.0.0"
)

class HealthCheckResponse(BaseModel):
    status: str
    app: str
    version: str

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health", response_model=HealthCheckResponse, summary="Health Check")
def get_health():
    return HealthCheckResponse(
        status="ok",
        app="MedTrace Backend",
        version="1.0.0"
    )

@app.post("/generate-demo-data", response_model=DemoDataGenerationResponse, summary="Generate Demo Data")
def generate_demo_data():
    try:
        response = generate_demo_dataset()
        # Seed/persist initial risk cases for all facility-medicine pairs
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT facility_id FROM facilities;")
        fac_ids = [r["facility_id"] for r in cursor.fetchall()]
        cursor.execute("SELECT medicine_id FROM medicine_config;")
        med_ids = [r["medicine_id"] for r in cursor.fetchall()]

        for f_id in fac_ids:
            for m_id in med_ids:
                try:
                    analysis = get_facility_medicine_analysis(f_id, m_id)
                    save_rescue_case(
                        conn=conn,
                        facility_id=f_id,
                        medicine_id=m_id,
                        risk_level=analysis.risk_assessment.risk_level,
                        confidence=analysis.risk_assessment.confidence,
                        stock_truth_score=analysis.stock_truth.total,
                        recommended_action=analysis.risk_assessment.recommended_action
                    )
                except Exception:
                    continue
        conn.close()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate demo data: {str(e)}")

@app.get("/dashboard-summary", response_model=DashboardSummaryOut, summary="Dashboard Summary KPIs")
def get_dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM facilities;")
    total_facilities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicine_config;")
    total_medicines = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inventory_records;")
    total_inventory_records = cursor.fetchone()[0]

    if total_inventory_records == 0:
        conn.close()
        return DashboardSummaryOut(
            total_facilities=total_facilities,
            total_medicines=total_medicines,
            total_inventory_records=0,
            facilities_at_risk=0,
            critical_stockouts=0,
            watch_stockouts=0,
            unverified_reports=0,
            ok_status_count=0
        )

    cursor.execute("SELECT facility_id, reporting_interval_days FROM facilities;")
    facilities = {row["facility_id"]: row for row in cursor.fetchall()}

    cursor.execute("SELECT medicine_id, safety_stock_days FROM medicine_config;")
    medicines = {row["medicine_id"]: row for row in cursor.fetchall()}

    facilities_at_risk_set = set()
    critical_count = 0
    watch_count = 0
    unverified_count = 0
    ok_count = 0

    for fac_id, fac_info in facilities.items():
        expected_interval = float(fac_info["reporting_interval_days"])

        for med_id, med_info in medicines.items():
            safety_stock_days = med_info["safety_stock_days"]

            cursor.execute("""
                SELECT opening_stock, received, issued, closing_stock, is_reported, record_date
                FROM inventory_records
                WHERE facility_id = ? AND medicine_id = ?
                ORDER BY record_date ASC;
            """, (fac_id, med_id))
            
            records = cursor.fetchall()
            if not records:
                continue

            latest_record = records[-1]
            opening = latest_record["opening_stock"]
            received = latest_record["received"]
            issued = latest_record["issued"]
            closing = latest_record["closing_stock"]

            window_records = records[-14:]
            history = [r["issued"] for r in window_records]
            actual_reports_received = sum(1 for r in window_records if r["is_reported"])

            reported_records = [r for r in records if r["is_reported"]]
            if reported_records:
                last_rep_date_str = reported_records[-1]["record_date"]
                latest_date_str = latest_record["record_date"]
                d_last = datetime.strptime(last_rep_date_str, "%Y-%m-%d")
                d_latest = datetime.strptime(latest_date_str, "%Y-%m-%d")
                days_since_last_report = float((d_latest - d_last).days)
            else:
                days_since_last_report = 10.0

            avg_demand = sum(history) / float(max(len(history), 1)) if history else 0.0

            truth_out = compute_stock_truth_score(
                days_since_last_report=days_since_last_report,
                expected_interval=expected_interval,
                actual_reports_received=actual_reports_received,
                window_days=14,
                opening_stock=opening,
                received=received,
                reported_closing=closing,
                avg_daily_demand=avg_demand
            )

            status_out = compute_inventory_status(
                facility_id=fac_id,
                medicine_id=med_id,
                opening_stock=opening,
                received=received,
                issued=issued,
                issued_history=history,
                safety_stock_days=safety_stock_days,
                truth_score=truth_out.total
            )

            if status_out.status == "CRITICAL":
                critical_count += 1
                facilities_at_risk_set.add(fac_id)
            elif status_out.status == "WATCH":
                watch_count += 1
                facilities_at_risk_set.add(fac_id)
            elif status_out.status == "UNKNOWN — verify":
                unverified_count += 1
                facilities_at_risk_set.add(fac_id)
            else:
                ok_count += 1

    conn.close()

    return DashboardSummaryOut(
        total_facilities=total_facilities,
        total_medicines=total_medicines,
        total_inventory_records=total_inventory_records,
        facilities_at_risk=len(facilities_at_risk_set),
        critical_stockouts=critical_count,
        watch_stockouts=watch_count,
        unverified_reports=unverified_count,
        ok_status_count=ok_count
    )

@app.get("/facilities/{facility_id}/medicines/{medicine_id}", response_model=FacilityMedicineAnalysisOut, summary="Get Facility Medicine Analysis")
def get_facility_medicine_analysis(facility_id: str, medicine_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT reporting_interval_days FROM facilities WHERE facility_id = ?;", (facility_id,))
    fac_row = cursor.fetchone()
    if not fac_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found")

    cursor.execute("SELECT safety_stock_days FROM medicine_config WHERE medicine_id = ?;", (medicine_id,))
    med_row = cursor.fetchone()
    if not med_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Medicine '{medicine_id}' not found")

    expected_interval = float(fac_row["reporting_interval_days"])
    safety_stock_days = int(med_row["safety_stock_days"])

    cursor.execute("""
        SELECT opening_stock, received, issued, closing_stock, is_reported, record_date
        FROM inventory_records
        WHERE facility_id = ? AND medicine_id = ?
        ORDER BY record_date ASC;
    """, (facility_id, medicine_id))
    records = cursor.fetchall()

    if not records:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No inventory records found for facility '{facility_id}' and medicine '{medicine_id}'")

    latest_record = records[-1]
    opening = latest_record["opening_stock"]
    received = latest_record["received"]
    issued = latest_record["issued"]
    closing = latest_record["closing_stock"]

    window_records = records[-14:]
    history = [r["issued"] for r in window_records]
    actual_reports_received = sum(1 for r in window_records if r["is_reported"])

    reported_records = [r for r in records if r["is_reported"]]
    if reported_records:
        last_rep_date_str = reported_records[-1]["record_date"]
        latest_date_str = latest_record["record_date"]
        d_last = datetime.strptime(last_rep_date_str, "%Y-%m-%d")
        d_latest = datetime.strptime(latest_date_str, "%Y-%m-%d")
        days_since_last_report = float((d_latest - d_last).days)
    else:
        days_since_last_report = 10.0

    forecast_out = compute_demand_forecast(history)
    avg_demand = forecast_out.forecast_per_day

    truth_out = compute_stock_truth_score(
        days_since_last_report=days_since_last_report,
        expected_interval=expected_interval,
        actual_reports_received=actual_reports_received,
        window_days=14,
        opening_stock=opening,
        received=received,
        reported_closing=closing,
        avg_daily_demand=avg_demand
    )

    inventory_out = compute_inventory_status(
        facility_id=facility_id,
        medicine_id=medicine_id,
        opening_stock=opening,
        received=received,
        issued=issued,
        issued_history=history,
        safety_stock_days=safety_stock_days,
        truth_score=truth_out.total
    )

    risk_out = compute_stockout_risk(
        days_remaining=inventory_out.days_remaining,
        trend_flag=forecast_out.trend_flag,
        stock_truth_score=truth_out.total,
        data_points=len(history)
    )

    # Persistence: Save computed risk case to DB
    save_rescue_case(
        conn=conn,
        facility_id=facility_id,
        medicine_id=medicine_id,
        risk_level=risk_out.risk_level,
        confidence=risk_out.confidence,
        stock_truth_score=truth_out.total,
        recommended_action=risk_out.recommended_action
    )
    conn.close()

    return FacilityMedicineAnalysisOut(
        facility_id=facility_id,
        medicine_id=medicine_id,
        inventory_status=inventory_out,
        demand_forecast=forecast_out,
        stock_truth=truth_out,
        risk_assessment=risk_out
    )

@app.post("/recommend-transfer", response_model=TransferRecommendation, summary="Recommend Rescue Transfer")
def get_recommend_transfer(
    facility_id: str = Query(..., description="Recipient facility ID"),
    medicine_id: str = Query(..., description="Medicine ID")
):
    conn = get_db_connection()
    result = optimize_rescue_transfer(conn, recipient_facility_id=facility_id, medicine_id=medicine_id)
    conn.close()
    return TransferRecommendation(**result)

@app.post("/simulate-verification", response_model=SimulateVerificationOut, summary="Counterfactual Simulator")
def simulate_verification(payload: SimulateVerificationIn):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT case_id, facility_id, medicine_id, status FROM rescue_cases WHERE case_id = ?;", (payload.case_id,))
    case_row = cursor.fetchone()
    if not case_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Rescue case with ID {payload.case_id} not found.")

    fac_id = case_row["facility_id"]
    med_id = case_row["medicine_id"]
    existing_status = case_row["status"]

    # Capture BEFORE state
    before_analysis = get_facility_medicine_analysis(fac_id, med_id).model_dump()
    before_rec = optimize_rescue_transfer(conn, recipient_facility_id=fac_id, medicine_id=med_id)

    # 1. Update latest inventory record with corrected physical count
    cursor.execute("""
        SELECT record_id, record_date, opening_stock, received, issued
        FROM inventory_records
        WHERE facility_id = ? AND medicine_id = ?
        ORDER BY record_date DESC LIMIT 1;
    """, (fac_id, med_id))
    latest_rec = cursor.fetchone()
    if not latest_rec:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No inventory records for facility {fac_id} & medicine {med_id}")

    record_id = latest_rec["record_id"]
    cursor.execute("""
        UPDATE inventory_records
        SET opening_stock = ?, closing_stock = ?, is_reported = 1
        WHERE record_id = ?;
    """, (payload.corrected_physical_count, payload.corrected_physical_count, record_id))
    conn.commit()

    # Re-run 5-step pipeline: Inventory -> Stock Truth -> Risk -> Surplus -> Transfer Optimizer
    after_analysis = get_facility_medicine_analysis(fac_id, med_id).model_dump()
    after_rec = optimize_rescue_transfer(conn, recipient_facility_id=fac_id, medicine_id=med_id)

    # Determine status action
    if existing_status == "APPROVED":
        status_action = "RE_REVIEW_REQUIRED"
        cursor.execute("UPDATE rescue_cases SET status = 'RE_REVIEW_REQUIRED' WHERE case_id = ?;", (payload.case_id,))
        reasoning = (
            f"Officer submitted physical count {payload.corrected_physical_count}. "
            f"Case was already APPROVED (transfer in motion) — flagged for officer re-review rather than auto-cancelled."
        )
    else:
        after_risk_level = after_analysis["risk_assessment"]["risk_level"]
        after_status = after_analysis["inventory_status"]["status"]
        after_days_rem = after_analysis["inventory_status"]["days_remaining"]

        if after_risk_level in ("LOW", "OK") or after_status == "OK" or after_days_rem > 10.0:
            status_action = "CANCELLED"
            cursor.execute("UPDATE rescue_cases SET status = 'CANCELLED' WHERE case_id = ?;", (payload.case_id,))
            reasoning = (
                f"Counterfactual simulator result: Physical stock verified as {payload.corrected_physical_count} units "
                f"(days remaining: {after_days_rem:.1f}). Risk reduced from {before_analysis['risk_assessment']['risk_level']} "
                f"to {after_risk_level}. Transfer is no longer needed and has been CANCELLED."
            )
        else:
            status_action = "UPDATED"
            cursor.execute("UPDATE rescue_cases SET status = 'OPEN' WHERE case_id = ?;", (payload.case_id,))
            reasoning = (
                f"Counterfactual simulator result: Physical stock updated to {payload.corrected_physical_count} units. "
                f"Risk level is now {after_risk_level} (Truth Score: {after_analysis['stock_truth']['total']:.1f})."
            )

    conn.commit()
    conn.close()

    return SimulateVerificationOut(
        case_id=payload.case_id,
        status_action=status_action,
        reasoning=reasoning,
        before={"analysis": before_analysis, "recommendation": before_rec},
        after={"analysis": after_analysis, "recommendation": after_rec}
    )

@app.get("/rescue-queue", response_model=List[RescueCaseOut], summary="Get Active Rescue Queue")
def get_rescue_queue():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT case_id, facility_id, medicine_id, risk_level, confidence, stock_truth_score, recommended_action, created_at, status
        FROM rescue_cases
        WHERE status IN ('OPEN', 'RE_REVIEW_REQUIRED')
        ORDER BY
            CASE risk_level
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'UNVERIFIED' THEN 3
                WHEN 'MEDIUM' THEN 4
                ELSE 5
            END,
            created_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        RescueCaseOut(
            case_id=r["case_id"],
            facility_id=r["facility_id"],
            medicine_id=r["medicine_id"],
            risk_level=r["risk_level"],
            confidence=float(r["confidence"]),
            stock_truth_score=float(r["stock_truth_score"]),
            recommended_action=r["recommended_action"],
            created_at=str(r["created_at"]),
            status=r["status"]
        )
        for r in rows
    ]

@app.get("/rescue-cases/{case_id}", summary="Get Case Details")
def get_rescue_case_details(case_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rescue_cases WHERE case_id = ?;", (case_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Case ID {case_id} not found.")

    case_dict = dict(row)
    fac_id = case_dict["facility_id"]
    med_id = case_dict["medicine_id"]

    analysis = get_facility_medicine_analysis(fac_id, med_id)
    transfer_rec = optimize_rescue_transfer(conn, recipient_facility_id=fac_id, medicine_id=med_id)
    conn.close()

    return {
        "case": case_dict,
        "analysis": analysis,
        "transfer_recommendation": transfer_rec
    }
