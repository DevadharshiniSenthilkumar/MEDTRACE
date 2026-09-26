import pytest
from app.inventory_engine import compute_inventory_status
from app.schemas import InventoryStatusOut

def test_normal_status_ok():
    """Test stock level with > 7 days remaining returns OK status."""
    # Opening 100, received 0, issued 10 -> current_stock = 90
    # History of 10 daily issues = avg 10/day
    # Days remaining = 90 / 10 = 9 days -> OK (>7 days)
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=100.0,
        received=0.0,
        issued=10.0,
        issued_history=[10.0] * 10,
        safety_stock_days=5,
        truth_score=100.0
    )
    assert res.status == "OK"
    assert res.current_stock == 90.0
    assert res.avg_daily_demand == 10.0
    assert res.days_remaining == 9.0
    assert res.safety_stock == 50.0
    assert res.insufficient_history is False

def test_normal_status_watch():
    """Test stock level between 3 and 7 days remaining returns WATCH status."""
    # Opening 60, received 0, issued 10 -> current_stock = 50
    # History avg = 10/day
    # Days remaining = 50 / 10 = 5 days -> WATCH (3 < days <= 7)
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=60.0,
        received=0.0,
        issued=10.0,
        issued_history=[10.0] * 10,
        safety_stock_days=5,
        truth_score=100.0
    )
    assert res.status == "WATCH"
    assert res.days_remaining == 5.0

def test_normal_status_critical():
    """Test stock level <= 3 days remaining returns CRITICAL status."""
    # Opening 30, received 0, issued 10 -> current_stock = 20
    # History avg = 10/day
    # Days remaining = 20 / 10 = 2 days -> CRITICAL (<= 3 days)
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=30.0,
        received=0.0,
        issued=10.0,
        issued_history=[10.0] * 10,
        safety_stock_days=5,
        truth_score=100.0
    )
    assert res.status == "CRITICAL"
    assert res.days_remaining == 2.0

def test_zero_demand_case():
    """Test zero average daily demand handles infinity without division by zero error."""
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=50.0,
        received=0.0,
        issued=0.0,
        issued_history=[0.0] * 10,
        safety_stock_days=5,
        truth_score=100.0
    )
    assert res.status == "OK"
    assert res.avg_daily_demand == 0.0
    assert res.days_remaining == float('inf')
    assert "Zero daily demand recorded" in res.reasoning or "zero recorded daily demand" in res.reasoning

def test_negative_stock_rejection():
    """Test negative opening stock raises ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        compute_inventory_status(
            facility_id="FAC_001",
            medicine_id="MED_001",
            opening_stock=-10.0,
            received=0.0,
            issued=5.0,
            issued_history=[5.0] * 5
        )

def test_issued_exceeds_available_rejection():
    """Test issued quantity exceeding opening + received stock raises ValueError."""
    with pytest.raises(ValueError, match="cannot exceed opening stock"):
        compute_inventory_status(
            facility_id="FAC_001",
            medicine_id="MED_001",
            opening_stock=10.0,
            received=5.0,
            issued=20.0,
            issued_history=[5.0] * 5
        )

def test_low_truth_score_override():
    """Test low stock truth score (< 50) overrides risk level to UNKNOWN — verify."""
    # Days remaining is 2 days (which would normally be CRITICAL), but truth_score is 40.0 (< 50)
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=30.0,
        received=0.0,
        issued=10.0,
        issued_history=[10.0] * 10,
        safety_stock_days=5,
        truth_score=40.0
    )
    assert res.status == "UNKNOWN — verify"
    assert "Stock Truth Score (40.0) is below threshold" in res.reasoning

def test_insufficient_history_flag():
    """Test having fewer than 5 days of history flags insufficient_history=True."""
    res = compute_inventory_status(
        facility_id="FAC_001",
        medicine_id="MED_001",
        opening_stock=100.0,
        received=0.0,
        issued=10.0,
        issued_history=[10.0, 10.0, 10.0],  # 3 days history
        safety_stock_days=5
    )
    assert res.insufficient_history is True
    assert "minimum" in res.reasoning
