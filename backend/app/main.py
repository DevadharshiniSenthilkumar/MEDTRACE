from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import sqlite3

from app.database import init_db, get_db_connection
from app.schemas import (
    DashboardSummaryOut,
    DemoDataGenerationResponse,
    InventoryStatusOut
)
from app.synthetic_data import generate_demo_dataset
from app.inventory_engine import compute_inventory_status

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
    cursor.execute("SELECT facility_id, is_remote FROM facilities;")
    facilities = {row["facility_id"]: row for row in cursor.fetchall()}

    cursor.execute("SELECT medicine_id, safety_stock_days FROM medicine_config;")
    medicines = {row["medicine_id"]: row for row in cursor.fetchall()}

    facilities_at_risk_set = set()
    critical_count = 0
    watch_count = 0
    unverified_count = 0
    ok_count = 0

    for fac_id in facilities.keys():
        for med_id, med_info in medicines.items():
            safety_stock_days = med_info["safety_stock_days"]

            # Query recent 14 records for this fac_id, med_id sorted by date
            cursor.execute("""
                SELECT opening_stock, received, issued, is_reported, record_date
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
            is_reported = bool(latest_record["is_reported"])

            # Issued history over lookback window (last 14 days)
            history = [r["issued"] for r in records[-14:]]

            # In Phase 1, truth_score defaults to 100 unless report is false
            truth_score = 100.0 if is_reported else 40.0

            status_out = compute_inventory_status(
                facility_id=fac_id,
                medicine_id=med_id,
                opening_stock=opening,
                received=received,
                issued=issued,
                issued_history=history,
                safety_stock_days=safety_stock_days,
                truth_score=truth_score
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
