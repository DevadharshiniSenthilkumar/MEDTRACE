import pytest
from app.forecast_engine import compute_demand_forecast
from app.schemas import ForecastOut

def test_known_weighted_forecast_stable():
    """Test known constant input series yields exact weighted average and stable trend."""
    # 14 days of constant 10.0 units/day
    history = [10.0] * 14
    res = compute_demand_forecast(history)
    
    assert res.forecast_per_day == 10.0
    assert res.forecast_7day == 70.0
    assert res.trend_flag == "stable"
    assert res.insufficient_history is False
    assert len(res.weights_used) == 14
    assert res.weights_used == [float(i + 1) for i in range(14)]

def test_rising_trend_detection():
    """Test recent demand spike triggers 'rising' trend flag."""
    # 11 days of 5.0, followed by 3 days of 20.0
    # earlier avg = 5.0, last 3 avg = 20.0 > 1.2 * 5.0 (6.0) -> rising
    history = [5.0] * 11 + [20.0, 20.0, 20.0]
    res = compute_demand_forecast(history)

    assert res.trend_flag == "rising"
    # Weighted calculation: (1..11)*5 + (12+13+14)*20 = 66*5 + 39*20 = 330 + 780 = 1110
    # Total weight = 105 => 1110 / 105 = 10.5714... -> 10.57 per day
    # Full precision 7-day forecast: (1110 / 105) * 7 = 74.0 exactly
    assert res.forecast_per_day == 10.57
    assert res.forecast_7day == 74.0

def test_falling_trend_detection():
    """Test recent demand drop triggers 'falling' trend flag."""
    # 11 days of 20.0, followed by 3 days of 5.0
    # earlier avg = 20.0, last 3 avg = 5.0 < 0.8 * 20.0 (16.0) -> falling
    history = [20.0] * 11 + [5.0, 5.0, 5.0]
    res = compute_demand_forecast(history)

    assert res.trend_flag == "falling"

def test_insufficient_history_fallback():
    """Test < 5 days of history returns insufficient_history=True and unweighted fallback."""
    history = [10.0, 20.0, 30.0]  # 3 days < 5 minimum
    res = compute_demand_forecast(history)

    assert res.insufficient_history is True
    # Unweighted average = (10+20+30)/3 = 20.0
    assert res.forecast_per_day == 20.0
    assert res.forecast_7day == 140.0
    assert "Insufficient history" in res.reasoning

def test_empty_history():
    """Test empty history list handled gracefully."""
    res = compute_demand_forecast([])
    assert res.insufficient_history is True
    assert res.forecast_per_day == 0.0
    assert res.forecast_7day == 0.0
    assert res.trend_flag == "stable"

def test_negative_quantity_rejection():
    """Test negative quantity in history raises ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        compute_demand_forecast([10.0, -5.0, 10.0, 10.0, 10.0])
