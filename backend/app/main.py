from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sqlite3
import csv
import io
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
    RescueCaseOut,
    FacilityOut,
    FacilityDetailOut,
    UploadErrorWarning,
    UploadReport,
    FeedbackIn,
    FeedbackOut,
    FeedbackHistoryItemOut,
    SurplusSummaryOut
)
from app.synthetic_data import generate_demo_dataset
from app.inventory_engine import compute_inventory_status
from app.forecast_engine import compute_demand_forecast
from app.stock_truth_engine import compute_stock_truth_score
from app.stockout_risk_engine import compute_stockout_risk, save_rescue_case
from app.surplus_engine import find_eligible_donors, find_near_expiry_matches, get_all_surplus_and_near_expiry
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

@app.get("/facilities", response_model=List[FacilityOut], summary="List All Facilities")
def get_facilities():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT facility_id, name, lat, lon, facility_type, is_remote, reporting_interval_days FROM facilities ORDER BY facility_id;")
    rows = cursor.fetchall()
    conn.close()
    return [
        FacilityOut(
            facility_id=r["facility_id"],
            name=r["name"],
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            facility_type=r["facility_type"],
            is_remote=bool(r["is_remote"]),
            reporting_interval_days=int(r["reporting_interval_days"])
        )
        for r in rows
    ]

@app.get("/facilities/{facility_id}", response_model=FacilityDetailOut, summary="Get Facility Details with Medicine Analysis")
def get_facility_details(facility_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT facility_id, name, lat, lon, facility_type, is_remote, reporting_interval_days FROM facilities WHERE facility_id = ?;", (facility_id,))
    fac_row = cursor.fetchone()
    if not fac_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found.")

    facility_out = FacilityOut(
        facility_id=fac_row["facility_id"],
        name=fac_row["name"],
        lat=float(fac_row["lat"]),
        lon=float(fac_row["lon"]),
        facility_type=fac_row["facility_type"],
        is_remote=bool(fac_row["is_remote"]),
        reporting_interval_days=int(fac_row["reporting_interval_days"])
    )

    cursor.execute("SELECT DISTINCT medicine_id FROM inventory_records WHERE facility_id = ?;", (facility_id,))
    med_rows = cursor.fetchall()
    conn.close()

    med_analyses = []
    for r in med_rows:
        try:
            analysis = get_facility_medicine_analysis(facility_id, r["medicine_id"])
            med_analyses.append(analysis)
        except Exception:
            continue

    return FacilityDetailOut(
        facility=facility_out,
        medicines=med_analyses
    )

@app.post("/upload-inventory", response_model=UploadReport, summary="Upload Inventory Records via CSV")
async def upload_inventory(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        return UploadReport(
            rows_processed=0,
            accepted=False,
            errors=[UploadErrorWarning(row=0, message="CSV file is empty.")],
            warnings=[]
        )

    try:
        decoded_text = contents.decode("utf-8-sig")
    except Exception as e:
        return UploadReport(
            rows_processed=0,
            accepted=False,
            errors=[UploadErrorWarning(row=0, message=f"Failed to decode file encoding: {str(e)}")],
            warnings=[]
        )

    reader = csv.DictReader(io.StringIO(decoded_text))
    if not reader.fieldnames:
        return UploadReport(
            rows_processed=0,
            accepted=False,
            errors=[UploadErrorWarning(row=0, message="CSV file has no header row.")],
            warnings=[]
        )

    field_map = {name.strip().lower(): name for name in reader.fieldnames if name}
    required_fields = ["facility_id", "medicine_id", "record_date", "opening_stock", "received", "issued"]
    missing_fields = [f for f in required_fields if f not in field_map]
    if missing_fields:
        return UploadReport(
            rows_processed=0,
            accepted=False,
            errors=[UploadErrorWarning(row=0, message=f"Missing required CSV column(s): {', '.join(missing_fields)}")],
            warnings=[]
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT facility_id FROM facilities;")
    valid_fac_ids = {r["facility_id"] for r in cursor.fetchall()}
    cursor.execute("SELECT medicine_id FROM medicine_config;")
    valid_med_ids = {r["medicine_id"] for r in cursor.fetchall()}

    rows_processed = 0
    errors: List[UploadErrorWarning] = []
    warnings: List[UploadErrorWarning] = []
    records_to_insert = []

    seen_in_batch = set()

    for idx, row in enumerate(reader, start=1):
        rows_processed += 1
        fac_id = (row.get(field_map["facility_id"]) or "").strip()
        med_id = (row.get(field_map["medicine_id"]) or "").strip()
        rec_date = (row.get(field_map["record_date"]) or "").strip()
        opening_str = row.get(field_map["opening_stock"])
        received_str = row.get(field_map["received"])
        issued_str = row.get(field_map["issued"])
        expiry_key = field_map.get("batch_expiry_date")
        exp_date = (row.get(expiry_key) or "").strip() if expiry_key else None

        if not fac_id or not med_id or not rec_date:
            errors.append(UploadErrorWarning(row=idx, message="Row contains empty facility_id, medicine_id, or record_date."))
            continue

        try:
            datetime.strptime(rec_date, "%Y-%m-%d")
        except ValueError:
            errors.append(UploadErrorWarning(row=idx, message=f"Invalid record_date '{rec_date}'. Date must be in YYYY-MM-DD format."))
            continue

        if valid_fac_ids and fac_id not in valid_fac_ids:
            errors.append(UploadErrorWarning(row=idx, message=f"Facility '{fac_id}' does not exist."))
            continue

        if valid_med_ids and med_id not in valid_med_ids:
            errors.append(UploadErrorWarning(row=idx, message=f"Medicine '{med_id}' does not exist."))
            continue

        try:
            opening = float(opening_str)
            received = float(received_str) if received_str is not None and str(received_str).strip() != "" else 0.0
            issued = float(issued_str) if issued_str is not None and str(issued_str).strip() != "" else 0.0
        except (ValueError, TypeError):
            errors.append(UploadErrorWarning(row=idx, message="Numerical fields (opening_stock, received, issued) must be valid numbers."))
            continue

        if opening < 0 or received < 0 or issued < 0:
            errors.append(UploadErrorWarning(row=idx, message="Stock quantities cannot be negative."))
            continue

        cursor.execute("""
            SELECT 1 FROM inventory_records
            WHERE facility_id = ? AND medicine_id = ? AND record_date = ?;
        """, (fac_id, med_id, rec_date))
        if cursor.fetchone():
            errors.append(UploadErrorWarning(
                row=idx,
                message=f"Duplicate inventory record for facility '{fac_id}', medicine '{med_id}', and date '{rec_date}' (UNIQUE constraint)."
            ))
            continue

        key = (fac_id, med_id, rec_date)
        if key in seen_in_batch:
            errors.append(UploadErrorWarning(
                row=idx,
                message=f"Duplicate inventory record in CSV batch for facility '{fac_id}', medicine '{med_id}', and date '{rec_date}'."
            ))
            continue
        seen_in_batch.add(key)

        closing = opening + received - issued

        records_to_insert.append((fac_id, med_id, rec_date, opening, received, issued, closing, exp_date))

    if rows_processed == 0:
        conn.close()
        return UploadReport(
            rows_processed=0,
            accepted=False,
            errors=[UploadErrorWarning(row=0, message="CSV file contains no data rows.")],
            warnings=[]
        )

    accepted = len(errors) == 0

    if accepted and records_to_insert:
        for r in records_to_insert:
            cursor.execute("""
                INSERT INTO inventory_records (facility_id, medicine_id, record_date, opening_stock, received, issued, closing_stock, batch_expiry_date, is_reported)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
            """, r)
        conn.commit()

    conn.close()

    return UploadReport(
        rows_processed=rows_processed,
        accepted=accepted,
        errors=errors,
        warnings=warnings
    )

@app.post("/feedback", response_model=FeedbackOut, summary="Submit Officer Feedback for a Rescue Case")
def submit_feedback(payload: FeedbackIn):
    if payload.officer_decision not in ("APPROVED", "REJECTED", "VERIFIED"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid officer decision '{payload.officer_decision}'. Must be APPROVED, REJECTED, or VERIFIED."
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT case_id FROM rescue_cases WHERE case_id = ?;", (payload.case_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Rescue case with ID {payload.case_id} not found.")

    cursor.execute("""
        INSERT INTO feedback (case_id, officer_decision, notes)
        VALUES (?, ?, ?);
    """, (payload.case_id, payload.officer_decision, payload.notes))
    conn.commit()

    feedback_id = cursor.lastrowid
    cursor.execute("SELECT feedback_id, case_id, officer_decision, notes, decided_at FROM feedback WHERE feedback_id = ?;", (feedback_id,))
    row = cursor.fetchone()
    conn.close()

    return FeedbackOut(
        feedback_id=row["feedback_id"],
        case_id=row["case_id"],
        officer_decision=row["officer_decision"],
        notes=row["notes"],
        decided_at=str(row["decided_at"])
    )

@app.get("/feedback", response_model=List[FeedbackHistoryItemOut], summary="Get All Officer Feedback History")
def get_feedback_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.feedback_id, f.case_id, r.facility_id, r.medicine_id, r.risk_level, f.officer_decision, f.notes, f.decided_at
        FROM feedback f
        LEFT JOIN rescue_cases r ON f.case_id = r.case_id
        ORDER BY f.decided_at DESC, f.feedback_id DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        FeedbackHistoryItemOut(
            feedback_id=r["feedback_id"],
            case_id=r["case_id"],
            facility_id=r["facility_id"],
            medicine_id=r["medicine_id"],
            risk_level=r["risk_level"],
            officer_decision=r["officer_decision"],
            notes=r["notes"],
            decided_at=str(r["decided_at"])
        )
        for r in rows
    ]

@app.get("/surplus", response_model=SurplusSummaryOut, summary="Get Standalone Surplus and Expiry Data")
def get_surplus_summary():
    conn = get_db_connection()
    res = get_all_surplus_and_near_expiry(conn)
    conn.close()
    return SurplusSummaryOut(**res)

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

def get_transfer_recommendation_for_case(
    conn: sqlite3.Connection,
    facility_id: str,
    medicine_id: str,
    case_status: str,
    risk_level: str
) -> Dict[str, Any]:
    if case_status == "OPEN" and risk_level in ("CRITICAL", "HIGH"):
        return optimize_rescue_transfer(conn, recipient_facility_id=facility_id, medicine_id=medicine_id)
    else:
        return {
            "status": "NOT_NEEDED",
            "reason": f"No transfer recommended: Case status is '{case_status}' and risk level is '{risk_level}'.",
            "donor_facility_id": None,
            "donor_facility_name": None,
            "recipient_facility_id": facility_id,
            "recipient_facility_name": None,
            "quantity": 0.0,
            "distance_km": 0.0,
            "fairness_proof": "N/A",
            "alternative_considered": None,
            "covers_days": 0.0
        }

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
    before_risk_level = before_analysis["risk_assessment"]["risk_level"]
    before_rec = get_transfer_recommendation_for_case(
        conn=conn,
        facility_id=fac_id,
        medicine_id=med_id,
        case_status=existing_status,
        risk_level=before_risk_level
    )

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
    after_risk_level = after_analysis["risk_assessment"]["risk_level"]
    after_status = after_analysis["inventory_status"]["status"]
    after_days_rem = after_analysis["inventory_status"]["days_remaining"]

    # Determine status action
    if existing_status == "APPROVED":
        status_action = "RE_REVIEW_REQUIRED"
        new_case_status = "RE_REVIEW_REQUIRED"
        cursor.execute("UPDATE rescue_cases SET status = 'RE_REVIEW_REQUIRED', risk_level = ? WHERE case_id = ?;", (after_risk_level, payload.case_id))
        reasoning = (
            f"Officer submitted physical count {payload.corrected_physical_count}. "
            f"Case was already APPROVED (transfer in motion) — flagged for officer re-review rather than auto-cancelled."
        )
    else:
        if after_risk_level in ("LOW", "OK") or after_status == "OK" or after_days_rem > 10.0:
            status_action = "CANCELLED"
            new_case_status = "CANCELLED"
            cursor.execute("UPDATE rescue_cases SET status = 'CANCELLED', risk_level = ? WHERE case_id = ?;", (after_risk_level, payload.case_id))
            reasoning = (
                f"Counterfactual simulator result: Physical stock verified as {payload.corrected_physical_count} units "
                f"(days remaining: {after_days_rem:.1f}). Risk reduced from {before_analysis['risk_assessment']['risk_level']} "
                f"to {after_risk_level}. Transfer is no longer needed and has been CANCELLED."
            )
        else:
            status_action = "UPDATED"
            new_case_status = "OPEN"
            cursor.execute("UPDATE rescue_cases SET status = 'OPEN', risk_level = ? WHERE case_id = ?;", (after_risk_level, payload.case_id))
            reasoning = (
                f"Counterfactual simulator result: Physical stock updated to {payload.corrected_physical_count} units. "
                f"Risk level is now {after_risk_level} (Truth Score: {after_analysis['stock_truth']['total']:.1f})."
            )

    conn.commit()

    after_rec = get_transfer_recommendation_for_case(
        conn=conn,
        facility_id=fac_id,
        medicine_id=med_id,
        case_status=new_case_status,
        risk_level=after_risk_level
    )

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
    current_status = case_dict.get("status", "OPEN")

    analysis = get_facility_medicine_analysis(fac_id, med_id)
    current_risk_level = analysis.risk_assessment.risk_level

    transfer_rec = get_transfer_recommendation_for_case(
        conn=conn,
        facility_id=fac_id,
        medicine_id=med_id,
        case_status=current_status,
        risk_level=current_risk_level
    )
    conn.close()

    return {
        "case": case_dict,
        "analysis": analysis,
        "transfer_recommendation": transfer_rec
    }
