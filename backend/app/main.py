from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
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
    FacilityMedicineAnalysisOut
)
from app.synthetic_data import generate_demo_dataset
from app.inventory_engine import compute_inventory_status
from app.forecast_engine import compute_demand_forecast
from app.stock_truth_engine import compute_stock_truth_score
from app.stockout_risk_engine import compute_stockout_risk

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
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate demo data: {str(e)}")

@app.get("/dashboard-summary", response_model=DashboardSummaryOut, summary="Dashboard Summary KPIs")
def get_dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total counts
    cursor.execute("SELECT COUNT(*) FROM facilities;")
    total_facilities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicine_config;")
    total_medicines = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inventory_records;")
    total_inventory_records = cursor.fetchone()[0]

    if total_inventory_records == 0:
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

    # 2. Evaluate current status per facility x medicine pair
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

            # Calculate actual reported records in 14-day window
            window_records = records[-14:]
            history = [r["issued"] for r in window_records]
            actual_reports_received = sum(1 for r in window_records if r["is_reported"])

            # Determine days since last report
            reported_records = [r for r in records if r["is_reported"]]
            if reported_records:
                last_rep_date_str = reported_records[-1]["record_date"]
                latest_date_str = latest_record["record_date"]
                d_last = datetime.strptime(last_rep_date_str, "%Y-%m-%d")
                d_latest = datetime.strptime(latest_date_str, "%Y-%m-%d")
                days_since_last_report = float((d_latest - d_last).days)
            else:
                days_since_last_report = 10.0  # High stale penalty if no reports

            avg_demand = sum(history) / float(max(len(history), 1)) if history else 0.0

            # Compute real Stock Truth Score (Module 5)
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
    conn.close()

    if not records:
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

    return FacilityMedicineAnalysisOut(
        facility_id=facility_id,
        medicine_id=medicine_id,
        inventory_status=inventory_out,
        demand_forecast=forecast_out,
        stock_truth=truth_out,
        risk_assessment=risk_out
    )
