import datetime
import random
import pandas as pd
from pathlib import Path
from app.database import get_db_connection, clear_demo_data
from app.schemas import DemoDataGenerationResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def generate_demo_dataset() -> DemoDataGenerationResponse:
    """
    Generates synthetic data for 20 facilities, 8 essential medicines,
    and 90 days of daily inventory records per facility-medicine pair.
    Clears previous demo data first so it can be called repeatedly.
    """
    clear_demo_data()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Facilities (20 total: 17 PHCs, 3 Warehouses, some marked remote)
    facilities_data = [
        # ID, Name, Lat, Lon, Type, Is_Remote, Reporting_Interval_Days
        ("FAC_001", "Central District Warehouse", 12.9716, 77.5946, "WAREHOUSE", False, 1),
        ("FAC_002", "North Regional Store", 13.0352, 77.5970, "WAREHOUSE", False, 1),
        ("FAC_003", "East Zone Depot", 12.9698, 77.7500, "WAREHOUSE", False, 1),
        ("FAC_004", "PHC Indiranagar", 12.9784, 77.6408, "PHC", False, 2),
        ("FAC_005", "PHC Jayanagar", 12.9250, 77.5938, "PHC", False, 2),
        ("FAC_006", "PHC Malleshwaram", 13.0031, 77.5643, "PHC", False, 2),
        ("FAC_007", "PHC Koramangala", 12.9352, 77.6245, "PHC", False, 2),
        ("FAC_008", "PHC Whitefield", 12.9698, 77.7499, "PHC", False, 2),
        ("FAC_009", "PHC Yelahanka", 13.1007, 77.5963, "PHC", False, 2),
        ("FAC_010", "PHC Hebbal", 13.0358, 77.5970, "PHC", False, 2),
        ("FAC_011", "PHC Rajajinagar", 12.9982, 77.5530, "PHC", False, 2),
        ("FAC_012", "PHC Banashankari", 12.9255, 77.5468, "PHC", False, 2),
        ("FAC_013", "PHC Electronic City", 12.8452, 77.6602, "PHC", False, 2),
        ("FAC_014", "PHC Marathahalli", 12.9591, 77.6974, "PHC", False, 2),
        ("FAC_015", "PHC Kengeri (Remote)", 12.9081, 77.4842, "PHC", True, 3),   # Protected Remote
        ("FAC_016", "PHC Anekal (Remote)", 12.7103, 77.6974, "PHC", True, 4),    # Protected Remote
        ("FAC_017", "PHC Nelamangala (Remote)", 13.0984, 77.3948, "PHC", True, 4),# Protected Remote
        ("FAC_018", "PHC Hoskote", 13.0725, 77.7981, "PHC", False, 2),
        ("FAC_019", "PHC Devanahalli", 13.2482, 77.7127, "PHC", False, 3),
        ("FAC_020", "PHC Doddaballapur", 13.2925, 77.5428, "PHC", False, 3),
    ]

    # 2. Medicines (8 essential medicines)
    medicines_data = [
        # ID, Name, Unit, Shelf Life Days, Safety Stock Days, Reorder Point Days
        ("MED_001", "Insulin (Human 100IU/ml)", "Vial", 365, 7, 14),
        ("MED_002", "ORS (Oral Rehydration Salts)", "Sachet", 730, 5, 10),
        ("MED_003", "Rifampicin (Anti-TB 150mg)", "Tablet", 540, 10, 20),
        ("MED_004", "Polyvalent Antivenom", "Vial", 365, 5, 10),
        ("MED_005", "Amoxicillin 500mg", "Capsule", 730, 5, 10),
        ("MED_006", "Paracetamol 500mg", "Tablet", 1095, 3, 7),
        ("MED_007", "Metformin 500mg", "Tablet", 1095, 5, 10),
        ("MED_008", "Atorvastatin 10mg", "Tablet", 730, 5, 10),
    ]

    # Insert Facilities and Medicines
    conn = get_db_connection()
    cursor = conn.cursor()

    for fac in facilities_data:
        cursor.execute(
            "INSERT INTO facilities (facility_id, name, lat, lon, facility_type, is_remote, reporting_interval_days) VALUES (?, ?, ?, ?, ?, ?, ?)",
            fac
        )

    for med in medicines_data:
        cursor.execute(
            "INSERT INTO medicine_config (medicine_id, name, unit, shelf_life_days, safety_stock_days, reorder_point_days) VALUES (?, ?, ?, ?, ?, ?)",
            med
        )

    # 3. Generate 90 days of Inventory Records (today - 89 days to today)
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=89)

    inventory_records = []
    seeded_case_notes = []

    # Map for initial stock and daily demand baseline per medicine
    demand_baseline = {
        "MED_001": 15.0,  # Insulin
        "MED_002": 50.0,  # ORS
        "MED_003": 20.0,  # Anti-TB
        "MED_004": 5.0,   # Antivenom
        "MED_005": 40.0,  # Amoxicillin
        "MED_006": 100.0, # Paracetamol
        "MED_007": 30.0,  # Metformin
        "MED_008": 25.0,  # Atorvastatin
    }

    random.seed(42)  # Deterministic generation for reproducible demo

    for fac in facilities_data:
        fac_id = fac[0]
        fac_type = fac[4]

        for med in medicines_data:
            med_id = med[0]
            base_demand = demand_baseline[med_id]

            # Initial opening stock at start_date
            if fac_type == "WAREHOUSE":
                current_stock = base_demand * 60  # Warehouses hold larger stock
            else:
                current_stock = base_demand * 15  # PHCs hold 15 days stock

            for d in range(90):
                rec_date = start_date + datetime.timedelta(days=d)

                # Standard daily demand with noise
                daily_issued = max(0.0, round(random.normalvariate(base_demand, base_demand * 0.15), 1))
                received = 0.0
                is_reported = True

                # SEEDED HIDDEN CASES

                # Case 1: Fast-approaching stockout at FAC_004 (PHC Indiranagar) for Insulin (MED_001) in last 5 days
                if fac_id == "FAC_004" and med_id == "MED_001":
                    if d >= 80:
                        daily_issued = 35.0  # Increased consumption
                    if d == 85:
                        current_stock = 45.0  # Depleting stock rapidly

                # Case 2: Phantom / Stale Report at FAC_005 (PHC Jayanagar) for ORS (MED_002)
                # Reporting stopped 10 days ago (d >= 80, is_reported = False)
                if fac_id == "FAC_005" and med_id == "MED_002" and d >= 80:
                    is_reported = False
                    if d == 80:
                        current_stock = 0.0  # Appears as 0 stock in stale reports

                # Case 3: Hidden Surplus at nearby FAC_001 (Warehouse) & FAC_006 (PHC Malleshwaram) for Insulin
                if fac_id == "FAC_006" and med_id == "MED_001":
                    current_stock = max(current_stock, 500.0)  # Large surplus

                # Case 4: Near-expiry stock at FAC_007 (PHC Koramangala) for Antivenom (MED_004)
                batch_expiry = None
                if fac_id == "FAC_007" and med_id == "MED_004":
                    # Expiring in 30 days from today
                    batch_expiry = (today + datetime.timedelta(days=30)).isoformat()
                else:
                    # Default expiry 300 days out
                    batch_expiry = (today + datetime.timedelta(days=300)).isoformat()

                # Case 5: Sudden demand spike at FAC_008 (PHC Whitefield) for Amoxicillin (MED_005)
                if fac_id == "FAC_008" and med_id == "MED_005" and d >= 85:
                    daily_issued = base_demand * 3.5

                # Case 6: Chronic/repeat stockout facility at FAC_009 (PHC Yelahanka) for Anti-TB (MED_003)
                if fac_id == "FAC_009" and med_id == "MED_003" and d % 15 == 0:
                    current_stock = 5.0  # Dips repeatedly

                # Case 7: Unfair-transfer trap - FAC_015 is remote and close to FAC_004, but protected
                if fac_id == "FAC_015" and med_id == "MED_001":
                    current_stock = 150.0  # Holds stock but is remote (is_remote=True)

                # Automatic resupply logic if stock drops below 2 days (except for seeded stockout cases)
                if current_stock - daily_issued < base_demand * 2 and not (fac_id == "FAC_004" and med_id == "MED_001" and d >= 85):
                    if fac_type == "WAREHOUSE":
                        received = base_demand * 40
                    else:
                        received = base_demand * 12

                opening = current_stock
                # Ensure issued doesn't exceed opening + received
                daily_issued = min(daily_issued, opening + received)
                closing = opening + received - daily_issued

                inventory_records.append((
                    fac_id, med_id, rec_date.isoformat(), opening, received, daily_issued, closing, batch_expiry, is_reported
                ))

                # Update current_stock for next day
                current_stock = closing

    cursor.executemany("""
        INSERT INTO inventory_records
        (facility_id, medicine_id, record_date, opening_stock, received, issued, closing_stock, batch_expiry_date, is_reported)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, inventory_records)

    conn.commit()
    conn.close()

    # Save to CSV files in backend/data/
    df_fac = pd.DataFrame(facilities_data, columns=["facility_id", "name", "lat", "lon", "facility_type", "is_remote", "reporting_interval_days"])
    df_med = pd.DataFrame(medicines_data, columns=["medicine_id", "name", "unit", "shelf_life_days", "safety_stock_days", "reorder_point_days"])
    df_inv = pd.DataFrame(inventory_records, columns=["facility_id", "medicine_id", "record_date", "opening_stock", "received", "issued", "closing_stock", "batch_expiry_date", "is_reported"])

    df_fac.to_csv(DATA_DIR / "facilities.csv", index=False)
    df_med.to_csv(DATA_DIR / "medicine_config.csv", index=False)
    df_inv.to_csv(DATA_DIR / "inventory_records.csv", index=False)

    seeded_cases = [
        "Seeded Real Fast Stockout: FAC_004 (PHC Indiranagar) - Insulin (MED_001)",
        "Seeded Phantom/Stale Report: FAC_005 (PHC Jayanagar) - ORS (MED_002)",
        "Seeded Safe Surplus: FAC_006 (PHC Malleshwaram) - Insulin (MED_001)",
        "Seeded Near-Expiry Stock: FAC_007 (PHC Koramangala) - Antivenom (MED_004)",
        "Seeded Sudden Demand Spike: FAC_008 (PHC Whitefield) - Amoxicillin (MED_005)",
        "Seeded Chronic Stockout: FAC_009 (PHC Yelahanka) - Anti-TB (MED_003)",
        "Seeded Unfair Transfer Trap: FAC_015 (PHC Kengeri Remote) - Insulin (MED_001)"
    ]

    return DemoDataGenerationResponse(
        status="success",
        facilities_count=len(facilities_data),
        medicines_count=len(medicines_data),
        inventory_records_count=len(inventory_records),
        seeded_cases=seeded_cases,
        message="Demo data successfully generated and loaded into database & CSVs."
    )
