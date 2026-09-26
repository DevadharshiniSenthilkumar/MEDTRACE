import sqlite3
import os
from pathlib import Path

# DB Path configuration: backend/data/medtrace.db
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "medtrace.db"

def get_db_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS facilities (
        facility_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        facility_type TEXT CHECK(facility_type IN ('PHC','WAREHOUSE')),
        is_remote BOOLEAN DEFAULT 0,
        reporting_interval_days INTEGER DEFAULT 2
    );

    CREATE TABLE IF NOT EXISTS medicine_config (
        medicine_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        shelf_life_days INTEGER NOT NULL,
        safety_stock_days INTEGER DEFAULT 5,
        reorder_point_days INTEGER DEFAULT 10
    );

    CREATE TABLE IF NOT EXISTS inventory_records (
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

    CREATE TABLE IF NOT EXISTS rescue_cases (
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

    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER REFERENCES rescue_cases(case_id) ON DELETE CASCADE,
        officer_decision TEXT CHECK(officer_decision IN ('APPROVED','REJECTED','VERIFIED')),
        notes TEXT,
        decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def clear_demo_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Clear tables in reverse dependency order
    cursor.execute("DELETE FROM feedback;")
    cursor.execute("DELETE FROM rescue_cases;")
    cursor.execute("DELETE FROM inventory_records;")
    cursor.execute("DELETE FROM medicine_config;")
    cursor.execute("DELETE FROM facilities;")
    conn.commit()
    conn.close()
