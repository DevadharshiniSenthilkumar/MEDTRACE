import pytest
from app.stockout_risk_engine import compute_stockout_risk
from app.schemas import RiskOut

def test_unverified_override_on_low_truth_score():
    """Test low Stock Truth Score (< 50) overrides CRITICAL days_remaining to UNVERIFIED."""
    # 1.0 day remaining would normally be CRITICAL, but truth_score is 40.0 (< 50)
    res = compute_stockout_risk(
        days_remaining=1.0,
        trend_flag="stable",
        stock_truth_score=40.0,
        data_points=14
    )
    assert res.risk_level == "UNVERIFIED"
    assert res.recommended_action == "verify_physical_stock"
    assert res.confidence == 0.40
    assert "below threshold" in res.reasoning

def test_critical_risk_classification():
    """Test days_remaining <= 2 with high truth score returns CRITICAL risk."""
    res = compute_stockout_risk(
        days_remaining=1.5,
        trend_flag="stable",
        stock_truth_score=95.0,
        data_points=14
    )
    assert res.risk_level == "CRITICAL"
    assert res.recommended_action == "consider_transfer"
    assert res.confidence == 0.95

def test_rising_trend_risk_bump():
    """Test rising trend bumps MEDIUM risk to HIGH risk."""
    res = compute_stockout_risk(
        days_remaining=8.0,  # Normally MEDIUM (5 < days <= 10)
        trend_flag="rising",
        stock_truth_score=90.0,
        data_points=14
    )
    assert res.risk_level == "HIGH"
    assert res.recommended_action == "consider_transfer"

def test_critical_capped_at_critical():
    """Test rising trend does not bump past CRITICAL risk."""
    res = compute_stockout_risk(
        days_remaining=1.0,  # CRITICAL
        trend_flag="rising",
        stock_truth_score=100.0,
        data_points=14
    )
    assert res.risk_level == "CRITICAL"
    assert res.recommended_action == "consider_transfer"

def test_partial_history_confidence_discount():
    """Test history < 14 days discounts confidence score proportionally."""
    # truth_score = 100, 7 days history out of 14 => confidence = 100/100 * (7/14) = 0.50
    res = compute_stockout_risk(
        days_remaining=4.0,
        trend_flag="stable",
        stock_truth_score=100.0,
        data_points=7
    )
    assert res.confidence == 0.50

def test_invalid_truth_score_rejection():
    """Test out-of-bounds truth score raises ValueError."""
    with pytest.raises(ValueError, match="between 0 and 100"):
        compute_stockout_risk(days_remaining=5.0, trend_flag="stable", stock_truth_score=150.0, data_points=14)
