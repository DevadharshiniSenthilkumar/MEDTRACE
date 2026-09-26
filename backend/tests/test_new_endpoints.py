import io
import pytest
from fastapi.testclient import TestClient

from app.main import app, generate_demo_data
from app.database import get_db_connection

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_demo_data():
    generate_demo_data()

def test_get_facilities_happy_path():
    response = client.get("/facilities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "facility_id" in first
    assert "name" in first
    assert "lat" in first
    assert "lon" in first
    assert "facility_type" in first

def test_get_facility_details_happy_path():
    # Fetch first valid facility_id
    res_facs = client.get("/facilities")
    fac_id = res_facs.json()[0]["facility_id"]

    response = client.get(f"/facilities/{fac_id}")
    assert response.status_code == 200
    data = response.json()
    assert "facility" in data
    assert data["facility"]["facility_id"] == fac_id
    assert "medicines" in data
    assert isinstance(data["medicines"], list)

def test_get_facility_details_unknown_facility():
    response = client.get("/facilities/FAC_UNKNOWN_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_upload_inventory_happy_path():
    res_facs = client.get("/facilities")
    fac_id = res_facs.json()[0]["facility_id"]

    csv_content = (
        f"facility_id,medicine_id,record_date,opening_stock,received,issued,batch_expiry_date\n"
        f"{fac_id},MED_001,2027-05-15,100,50,10,2027-12-31\n"
    )
    file_obj = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/upload-inventory",
        files={"file": ("inventory.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["rows_processed"] == 1
    assert report["accepted"] is True
    assert len(report["errors"]) == 0

def test_upload_inventory_empty_csv_edge_case():
    file_obj = io.BytesIO(b"")
    response = client.post(
        "/upload-inventory",
        files={"file": ("empty.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["rows_processed"] == 0
    assert report["accepted"] is False
    assert len(report["errors"]) > 0
    assert "empty" in report["errors"][0]["message"].lower()

def test_upload_inventory_invalid_facility_edge_case():
    csv_content = (
        "facility_id,medicine_id,record_date,opening_stock,received,issued\n"
        "FAC_NON_EXISTENT,MED_001,2026-09-25,100,50,10\n"
    )
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    response = client.post(
        "/upload-inventory",
        files={"file": ("invalid.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["rows_processed"] == 1
    assert report["accepted"] is False
    assert len(report["errors"]) == 1
    assert "does not exist" in report["errors"][0]["message"]

def test_submit_feedback_happy_path():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id FROM rescue_cases LIMIT 1;")
    row = c.fetchone()
    conn.close()
    assert row is not None, "Expected seeded rescue case"
    case_id = row["case_id"]

    response = client.post(
        "/feedback",
        json={"case_id": case_id, "officer_decision": "APPROVED", "notes": "Approved for emergency dispatch."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["officer_decision"] == "APPROVED"
    assert data["notes"] == "Approved for emergency dispatch."
    assert "feedback_id" in data

def test_submit_feedback_invalid_decision_edge_case():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id FROM rescue_cases LIMIT 1;")
    case_id = c.fetchone()["case_id"]
    conn.close()

    response = client.post(
        "/feedback",
        json={"case_id": case_id, "officer_decision": "INVALID_DECISION", "notes": "Test"}
    )
    assert response.status_code == 400
    assert "invalid officer decision" in response.json()["detail"].lower()

def test_submit_feedback_unknown_case_edge_case():
    response = client.post(
        "/feedback",
        json={"case_id": 9999999, "officer_decision": "VERIFIED", "notes": "Test"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_surplus_happy_path():
    response = client.get("/surplus")
    assert response.status_code == 200
    data = response.json()
    assert "eligible_surplus" in data
    assert "near_expiry_candidates" in data
    assert isinstance(data["eligible_surplus"], list)
    assert isinstance(data["near_expiry_candidates"], list)

def test_upload_inventory_negative_quantity_edge_case():
    res_facs = client.get("/facilities")
    fac_id = res_facs.json()[0]["facility_id"]

    csv_content = (
        "facility_id,medicine_id,record_date,opening_stock,received,issued\n"
        f"{fac_id},MED_001,2026-09-25,100,-5,10\n"
    )
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    response = client.post(
        "/upload-inventory",
        files={"file": ("negative.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["accepted"] is False
    assert len(report["errors"]) == 1
    assert "cannot be negative" in report["errors"][0]["message"].lower()

def test_upload_inventory_malformed_date_edge_case():
    res_facs = client.get("/facilities")
    fac_id = res_facs.json()[0]["facility_id"]

    csv_content = (
        "facility_id,medicine_id,record_date,opening_stock,received,issued\n"
        f"{fac_id},MED_001,25-09-2026,100,5,10\n"
    )
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    response = client.post(
        "/upload-inventory",
        files={"file": ("bad_date.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["accepted"] is False
    assert len(report["errors"]) == 1
    assert "yyyy-mm-dd" in report["errors"][0]["message"].lower() or "invalid record_date" in report["errors"][0]["message"].lower()

def test_upload_inventory_duplicate_record_edge_case():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT facility_id, medicine_id, record_date FROM inventory_records LIMIT 1;")
    row = c.fetchone()
    conn.close()
    assert row is not None

    fac_id = row["facility_id"]
    med_id = row["medicine_id"]
    rec_date = row["record_date"]

    csv_content = (
        "facility_id,medicine_id,record_date,opening_stock,received,issued\n"
        f"{fac_id},{med_id},{rec_date},100,5,10\n"
    )
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    response = client.post(
        "/upload-inventory",
        files={"file": ("duplicate.csv", file_obj, "text/csv")}
    )
    assert response.status_code == 200
    report = response.json()
    assert report["accepted"] is False
    assert len(report["errors"]) == 1
    assert "duplicate" in report["errors"][0]["message"].lower() or "unique" in report["errors"][0]["message"].lower()

def test_get_surplus_zero_eligible_donors_edge_case():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE inventory_records SET opening_stock = 0, closing_stock = 0;")
    conn.commit()
    conn.close()

    response = client.get("/surplus")
    assert response.status_code == 200
    data = response.json()
    assert "eligible_surplus" in data
    assert data["eligible_surplus"] == []

    generate_demo_data()

def test_get_feedback_history():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM feedback;")
    conn.commit()

    c.execute("SELECT case_id FROM rescue_cases LIMIT 2;")
    cases = c.fetchall()
    conn.close()

    res_empty = client.get("/feedback")
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    client.post("/feedback", json={"case_id": cases[0]["case_id"], "officer_decision": "APPROVED", "notes": "First feedback"})
    client.post("/feedback", json={"case_id": cases[1]["case_id"], "officer_decision": "VERIFIED", "notes": "Second feedback"})

    res_history = client.get("/feedback")
    assert res_history.status_code == 200
    history = res_history.json()
    assert len(history) == 2
    assert history[0]["officer_decision"] in ("APPROVED", "VERIFIED")
    assert "case_id" in history[0]

