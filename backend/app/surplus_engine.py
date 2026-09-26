import math
from datetime import datetime
from typing import List, Dict, Any, Optional
import sqlite3
from app.stock_truth_engine import compute_stock_truth_score

TRUTH_THRESHOLD = 50.0

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula using lat/lon of both facilities
    (standard great-circle distance calculation, Earth radius = 6371.0 km).
    """
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(R * c, 2)


def get_facility_stock_and_truth(conn: sqlite3.Connection, facility_id: str, medicine_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT facility_id, name, lat, lon, reporting_interval_days FROM facilities WHERE facility_id = ?;", (facility_id,))
    fac_row = cursor.fetchone()
    if not fac_row:
        return None

    cursor.execute("SELECT safety_stock_days FROM medicine_config WHERE medicine_id = ?;", (medicine_id,))
    med_row = cursor.fetchone()
    if not med_row:
        return None

    safety_stock_days = float(med_row["safety_stock_days"])
    expected_interval = float(fac_row["reporting_interval_days"])

    cursor.execute("""
        SELECT opening_stock, received, issued, closing_stock, is_reported, record_date, batch_expiry_date
        FROM inventory_records
        WHERE facility_id = ? AND medicine_id = ?
        ORDER BY record_date ASC;
    """, (facility_id, medicine_id))
    records = cursor.fetchall()
    if not records:
        return None

    latest_record = records[-1]
    opening = float(latest_record["opening_stock"])
    received = float(latest_record["received"])
    issued = float(latest_record["issued"])
    closing = float(latest_record["closing_stock"])

    window_records = records[-14:]
    history = [float(r["issued"]) for r in window_records]
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

    current_stock = closing
    safety_stock = safety_stock_days * avg_demand
    donor_surplus = current_stock - safety_stock

    return {
        "facility_id": fac_row["facility_id"],
        "name": fac_row["name"],
        "lat": float(fac_row["lat"]),
        "lon": float(fac_row["lon"]),
        "current_stock": current_stock,
        "avg_daily_demand": avg_demand,
        "safety_stock": safety_stock,
        "donor_surplus": donor_surplus,
        "stock_truth_score": truth_out.total,
        "latest_record_date": latest_record["record_date"],
        "batch_expiry_date": latest_record["batch_expiry_date"]
    }


def find_eligible_donors(conn: sqlite3.Connection, recipient_facility_id: str, medicine_id: str) -> List[Dict[str, Any]]:
    """
    For each candidate donor facility carrying the same medicine as a facility in need:
        donor_surplus = donor.current_stock - donor.safety_stock
        eligible = (donor_surplus > 0) AND (donor.stock_truth_score >= 50)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lon FROM facilities WHERE facility_id = ?;", (recipient_facility_id,))
    rec_fac = cursor.fetchone()
    if not rec_fac:
        return []

    rec_lat = float(rec_fac["lat"])
    rec_lon = float(rec_fac["lon"])

    cursor.execute("SELECT DISTINCT facility_id FROM inventory_records WHERE medicine_id = ? AND facility_id != ?;", (medicine_id, recipient_facility_id))
    donor_fac_ids = [row["facility_id"] for row in cursor.fetchall()]

    eligible_donors = []
    for d_id in donor_fac_ids:
        info = get_facility_stock_and_truth(conn, d_id, medicine_id)
        if not info:
            continue

        surplus = info["donor_surplus"]
        truth_score = info["stock_truth_score"]

        d_km = distance_km(rec_lat, rec_lon, info["lat"], info["lon"])
        info["distance_km"] = d_km

        # Rule: donor_surplus > 0 AND donor.stock_truth_score >= 50
        if surplus > 0 and truth_score >= TRUTH_THRESHOLD:
            info["eligible"] = True
            eligible_donors.append(info)

    return eligible_donors


def find_near_expiry_matches(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    near_expiry_candidates = every inventory batch where:
        batch.days_to_expiry <= 45 AND
        the facility holding it will NOT consume it before it expires
        (i.e. its own days_remaining_for_this_stock exceeds days_to_expiry)
    Match these candidates to any OTHER facility currently at MEDIUM/HIGH/CRITICAL risk
    for that same medicine, ranked by:
        1st: shortest days_to_expiry
        2nd: shortest distance
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.facility_id, i.medicine_id, i.closing_stock, i.record_date, i.batch_expiry_date
        FROM inventory_records i
        INNER JOIN (
            SELECT facility_id, medicine_id, MAX(record_date) as max_date
            FROM inventory_records
            WHERE batch_expiry_date IS NOT NULL AND batch_expiry_date != ''
            GROUP BY facility_id, medicine_id
        ) latest ON i.facility_id = latest.facility_id AND i.medicine_id = latest.medicine_id AND i.record_date = latest.max_date;
    """)
    rows = cursor.fetchall()

    matches = []
    for row in rows:
        fac_id = row["facility_id"]
        med_id = row["medicine_id"]
        exp_date_str = row["batch_expiry_date"]
        rec_date_str = row["record_date"]

        try:
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d")
            rec_date = datetime.strptime(rec_date_str, "%Y-%m-%d")
            days_to_expiry = (exp_date - rec_date).days
        except Exception:
            continue

        if days_to_expiry > 45 or days_to_expiry < 0:
            continue

        info = get_facility_stock_and_truth(conn, fac_id, med_id)
        if not info:
            continue

        avg_demand = info["avg_daily_demand"]
        current_stock = info["current_stock"]

        days_remaining = (current_stock / avg_demand) if avg_demand > 0 else float('inf')

        # Will NOT consume before expiry => days_remaining > days_to_expiry
        if days_remaining <= days_to_expiry:
            continue

        cursor.execute("SELECT DISTINCT facility_id FROM inventory_records WHERE medicine_id = ? AND facility_id != ?;", (med_id, fac_id))
        other_fac_ids = [r["facility_id"] for r in cursor.fetchall()]

        from app.stockout_risk_engine import compute_stockout_risk
        from app.forecast_engine import compute_demand_forecast

        for o_id in other_fac_ids:
            o_info = get_facility_stock_and_truth(conn, o_id, med_id)
            if not o_info:
                continue

            cursor.execute("SELECT issued FROM inventory_records WHERE facility_id = ? AND medicine_id = ? ORDER BY record_date ASC;", (o_id, med_id))
            o_history = [float(r["issued"]) for r in cursor.fetchall()[-14:]]
            forecast = compute_demand_forecast(o_history)

            o_days_rem = (o_info["current_stock"] / o_info["avg_daily_demand"]) if o_info["avg_daily_demand"] > 0 else 0.0

            risk = compute_stockout_risk(
                days_remaining=o_days_rem,
                trend_flag=forecast.trend_flag,
                stock_truth_score=o_info["stock_truth_score"],
                data_points=len(o_history)
            )

            if risk.risk_level in ("MEDIUM", "HIGH", "CRITICAL"):
                d_km = distance_km(info["lat"], info["lon"], o_info["lat"], o_info["lon"])
                matches.append({
                    "holding_facility_id": fac_id,
                    "holding_facility_name": info["name"],
                    "recipient_facility_id": o_id,
                    "recipient_facility_name": o_info["name"],
                    "medicine_id": med_id,
                    "batch_expiry_date": exp_date_str,
                    "days_to_expiry": days_to_expiry,
                    "days_remaining_holding": days_remaining,
                    "recipient_risk_level": risk.risk_level,
                    "distance_km": d_km
                })

    matches.sort(key=lambda x: (x["days_to_expiry"], x["distance_km"]))
    return matches

def get_all_surplus_and_near_expiry(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT facility_id, medicine_id FROM inventory_records;")
    pairs = cursor.fetchall()
    
    cursor.execute("SELECT facility_id, name FROM facilities;")
    fac_names = {r["facility_id"]: r["name"] for r in cursor.fetchall()}
    cursor.execute("SELECT medicine_id, name FROM medicine_config;")
    med_names = {r["medicine_id"]: r["name"] for r in cursor.fetchall()}

    eligible_surplus = []
    for pair in pairs:
        f_id = pair["facility_id"]
        m_id = pair["medicine_id"]
        info = get_facility_stock_and_truth(conn, f_id, m_id)
        if not info:
            continue
        if info["donor_surplus"] > 0 and info["stock_truth_score"] >= TRUTH_THRESHOLD:
            eligible_surplus.append({
                "facility_id": f_id,
                "facility_name": fac_names.get(f_id, info["name"]),
                "medicine_id": m_id,
                "medicine_name": med_names.get(m_id, m_id),
                "current_stock": round(info["current_stock"], 1),
                "safety_stock": round(info["safety_stock"], 1),
                "donor_surplus": round(info["donor_surplus"], 1),
                "stock_truth_score": round(info["stock_truth_score"], 1),
                "latest_record_date": info["latest_record_date"],
                "batch_expiry_date": info["batch_expiry_date"]
            })

    near_expiry_matches = find_near_expiry_matches(conn)

    return {
        "eligible_surplus": eligible_surplus,
        "near_expiry_candidates": near_expiry_matches
    }

