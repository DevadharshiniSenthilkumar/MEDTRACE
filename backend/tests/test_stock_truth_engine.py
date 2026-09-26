import pytest
from app.stock_truth_engine import compute_stock_truth_score
from app.schemas import StockTruthOut

def test_high_truth_case():
    """Test perfect reporting yields 100.0 total truth score."""
    res = compute_stock_truth_score(
        days_since_last_report=1.0,
        expected_interval=2.0,
        actual_reports_received=7,
        window_days=14,
        opening_stock=100.0,
        received=0.0,
        reported_closing=90.0,
        avg_daily_demand=10.0,
        days_elapsed=1.0
    )
    assert res.recency_score == 40.0
    assert res.completeness_score == 30.0
    assert res.consistency_score == 30.0
    assert res.total == 100.0
    assert "healthy" in res.reason

def test_stale_report_case():
    """Test stale report (> 2x expected interval) drops recency_score to 0."""
    # Expected interval = 2 days, last report = 5 days ago (ratio = 2.5 >= 2.0)
    res = compute_stock_truth_score(
        days_since_last_report=5.0,
        expected_interval=2.0,
        actual_reports_received=7,
        window_days=14,
        opening_stock=100.0,
        received=0.0,
        reported_closing=90.0,
        avg_daily_demand=10.0,
        days_elapsed=1.0
    )
    assert res.recency_score == 0.0
    assert res.total == 60.0  # 0 + 30 + 30

def test_severely_stale_and_incomplete_case():
    """Test stale + incomplete reports drop truth score below threshold (< 50)."""
    # 6 days since report, 2/7 actual reports
    res = compute_stock_truth_score(
        days_since_last_report=6.0,
        expected_interval=2.0,
        actual_reports_received=2,
        window_days=14,
        opening_stock=100.0,
        received=0.0,
        reported_closing=90.0,
        avg_daily_demand=10.0
    )
    assert res.recency_score == 0.0
    # Completeness: 30 * (2 / 7) = 8.57 -> ~8.6
    assert res.completeness_score < 10.0
    assert res.total < 50.0
    assert "UNVERIFIED" in res.reason

def test_inconsistent_closing_stock_case():
    """Test mismatch between reported and expected closing stock degrades consistency_score."""
    # Expected closing = 100 - (10 * 1) = 90. Reported closing = 20.
    # Deviation = |20 - 90| / 90 = 70 / 90 = 0.777...
    # Consistency = 30 * (1 - 0.777...) = 6.666... -> ~6.7
    res = compute_stock_truth_score(
        days_since_last_report=1.0,
        expected_interval=2.0,
        actual_reports_received=7,
        window_days=14,
        opening_stock=100.0,
        received=0.0,
        reported_closing=20.0,
        avg_daily_demand=10.0,
        days_elapsed=1.0
    )
    assert res.consistency_score < 10.0
    assert res.total < 100.0

def test_negative_values_rejection():
    """Test negative inputs raise ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        compute_stock_truth_score(days_since_last_report=-1.0)
    
    with pytest.raises(ValueError, match="must be positive"):
        compute_stock_truth_score(days_since_last_report=1.0, expected_interval=0.0)
