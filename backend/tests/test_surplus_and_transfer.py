import sqlite3
import pytest
from datetime import datetime
from app.surplus_engine import distance_km, find_eligible_donors
from app.transfer_optimizer import optimize_rescue_transfer
from app.stockout_risk_engine import compute_stockout_risk, save_rescue_case
from app.main import simulate_verification, get_facility_medicine_analysis, generate_demo_data, get_db_connection
from app.schemas import SimulateVerificationIn

@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    conn.executescript("""
    CREATE TABLE facilities (
        facility_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        facility_type TEXT CHECK(facility_type IN ('PHC','WAREHOUSE')),
        is_remote BOOLEAN DEFAULT 0,
        reporting_interval_days INTEGER DEFAULT 2
    );

    CREATE TABLE medicine_config (
        medicine_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        shelf_life_days INTEGER NOT NULL,
        safety_stock_days INTEGER DEFAULT 5,
        reorder_point_days INTEGER DEFAULT 10
    );

    CREATE TABLE inventory_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id TEXT REFERENCES facilities(facility_id) ON DELETE CASCADE,
        medicine_id TEXT REFERENCES medicine_config(medicine_id) ON DELETE CASCADE,
        record_date DATE NOT NULL,
        opening_stock REAL NOT NULL,
        received REAL DEFAULT 0,
        issued REAL DEFAULT 0,
        closing_stock REAL NOT NULL,
        batch_expiry_date DATE,
        is_reported BOOLEAN DEFAULT 1,
        UNIQUE(facility_id, medicine_id, record_date)
    );

    CREATE TABLE rescue_cases (
        case_id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id TEXT,
        medicine_id TEXT,
        risk_level TEXT,
        confidence REAL,
        stock_truth_score REAL,
        recommended_action TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'OPEN'
    );

    CREATE TABLE feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER REFERENCES rescue_cases(case_id) ON DELETE CASCADE,
        officer_decision TEXT CHECK(officer_decision IN ('APPROVED','REJECTED','VERIFIED')),
        notes TEXT,
        decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    yield conn
    conn.close()

def test_haversine_distance():
    d = distance_km(12.9716, 77.5946, 13.0827, 80.2707)
    assert 285.0 <= d <= 295.0

def test_normal_successful_transfer(test_db):
    conn = test_db
    c = conn.cursor()
    c.execute("INSERT INTO medicine_config VALUES ('MED_001', 'Insulin', 'vial', 365, 5, 10);")
    c.execute("INSERT INTO facilities VALUES ('FAC_REC', 'Recipient PHC', 12.00, 77.00, 'PHC', 0, 2);")
    c.execute("INSERT INTO facilities VALUES ('FAC_A', 'Donor A', 12.10, 77.10, 'PHC', 0, 2);")
    
    for i in range(14):
        date_str = f"2026-09-{13+i:02d}"
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_REC', 'MED_001', ?, 10, 0, 10, 0, '2027-01-01', 1);", (date_str,))
    
    for i in range(14):
        date_str = f"2026-09-{13+i:02d}"
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_A', 'MED_001', ?, 200, 0, 10, 200, '2027-01-01', 1);", (date_str,))

    conn.commit()

    rec = optimize_rescue_transfer(conn, 'FAC_REC', 'MED_001')
    assert rec["status"] == "RECOMMENDED"
    assert rec["donor_facility_id"] == "FAC_A"
    assert rec["quantity"] == 70.0
    assert rec["covers_days"] == 7.0
    assert "Fairness threshold preserved" in rec["fairness_proof"]

def test_fairness_rule_skips_unfair_closer_donor(test_db):
    """
    Tests that optimize_rescue_transfer evaluates the fairness assertion:
      assert (donor.current_stock - needed_quantity) >= donor.safety_stock
    When FAC_C (3km away) has stock 55 (safety stock 50), transferring the requested 70 units
    leaves 55-70 = -15 < 50, failing the assertion. The optimizer catches this, skips FAC_C,
    and selects FAC_B (10km away, 200 stock) which safely satisfies the assertion.
    """
    conn = test_db
    c = conn.cursor()
    c.execute("INSERT INTO medicine_config VALUES ('MED_001', 'Insulin', 'vial', 365, 5, 10);")
    c.execute("INSERT INTO facilities VALUES ('FAC_REC', 'Recipient PHC', 12.000, 77.000, 'PHC', 0, 2);")
    c.execute("INSERT INTO facilities VALUES ('FAC_C', 'Unfair Closer Donor', 12.020, 77.020, 'PHC', 0, 2);")
    c.execute("INSERT INTO facilities VALUES ('FAC_B', 'Fair Farther Donor', 12.080, 77.080, 'PHC', 0, 2);")

    # Recipient needs 70 units (10/day * 7 days)
    for i in range(14):
        d_str = f"2026-09-{13+i:02d}"
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_REC', 'MED_001', ?, 0, 0, 10, 0, '2027-01-01', 1);", (d_str,))
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_C', 'MED_001', ?, 55, 0, 10, 55, '2027-01-01', 1);", (d_str,))
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_B', 'MED_001', ?, 200, 0, 10, 200, '2027-01-01', 1);", (d_str,))

    conn.commit()

    rec = optimize_rescue_transfer(conn, 'FAC_REC', 'MED_001')
    assert rec["status"] == "RECOMMENDED"
    assert rec["donor_facility_id"] == "FAC_B"
    assert rec["alternative_considered"] is not None
    assert "Unfair Closer Donor" in rec["alternative_considered"] or "closer" in rec["alternative_considered"]
    assert "safety stock" in rec["alternative_considered"]

def test_no_safe_donor_available(test_db):
    conn = test_db
    c = conn.cursor()
    c.execute("INSERT INTO medicine_config VALUES ('MED_001', 'Insulin', 'vial', 365, 5, 10);")
    c.execute("INSERT INTO facilities VALUES ('FAC_REC', 'Recipient PHC', 12.000, 77.000, 'PHC', 0, 2);")
    c.execute("INSERT INTO facilities VALUES ('FAC_STALE', 'Untrustworthy Donor', 12.020, 77.020, 'PHC', 0, 2);")

    for i in range(14):
        d_str = f"2026-09-{13+i:02d}"
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_REC', 'MED_001', ?, 0, 0, 10, 0, '2027-01-01', 1);", (d_str,))

    for i in range(14):
        d_str = f"2026-09-{13+i:02d}"
        is_rep = 1 if i < 4 else 0
        c.execute("INSERT INTO inventory_records VALUES (NULL, 'FAC_STALE', 'MED_001', ?, 100, 0, 10, 100, '2027-01-01', ?);", (d_str, is_rep))

    conn.commit()

    rec = optimize_rescue_transfer(conn, 'FAC_REC', 'MED_001')
    assert rec["status"] == "no_safe_donor_available"
    assert rec["donor_facility_id"] is None
    assert "No safe donor available" in rec["reason"]

def test_counterfactual_simulator_cancels_transfer():
    generate_demo_data()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id, facility_id, medicine_id FROM rescue_cases WHERE status = 'OPEN' AND risk_level IN ('CRITICAL', 'HIGH') LIMIT 1;")
    row = c.fetchone()
    assert row is not None, "Expected seeded open risk case"
    case_id = row["case_id"]
    conn.close()

    out = simulate_verification(SimulateVerificationIn(case_id=case_id, corrected_physical_count=500.0, notes="Verified stock physically present"))
    
    assert out.case_id == case_id
    assert out.status_action == "CANCELLED"
    assert "CANCELLED" in out.reasoning

def test_counterfactual_simulator_approved_case():
    generate_demo_data()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id FROM rescue_cases WHERE status = 'OPEN' LIMIT 1;")
    case_id = c.fetchone()["case_id"]

    c.execute("UPDATE rescue_cases SET status = 'APPROVED' WHERE case_id = ?;", (case_id,))
    conn.commit()
    conn.close()

    out = simulate_verification(SimulateVerificationIn(case_id=case_id, corrected_physical_count=500.0, notes="Verified while in transit"))

    assert out.status_action == "RE_REVIEW_REQUIRED"
    assert "flagged for officer re-review" in out.reasoning.lower()

def test_rescue_cases_persistence():
    generate_demo_data()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rescue_cases;")
    count = c.fetchone()[0]
    conn.close()

    assert count > 0, "rescue_cases table must contain persisted risk cases after demo data generation."
