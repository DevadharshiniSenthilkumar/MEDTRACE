from typing import List, Optional
from app.schemas import ForecastOut

def compute_demand_forecast(issued_history: List[float]) -> ForecastOut:
    """
    Module 4: Demand Forecast Engine (Section 5, PROJECT_SPEC.md)
    
    Forecasts next 7-day demand using an explainable weighted moving average (linear decay weights).
    
    Exact logic:
    - Given last N=14 days of daily issued quantities [d1..d14] (d14 = most recent):
      weight_i = i (linear weights 1..14)
      forecast_per_day = sum(weight_i * d_i) / sum(weight_i)
      forecast_7day = forecast_per_day * 7
      trend_flag = "rising" if avg(last 3 days) > 1.2 * avg(days 4-14) [earlier days]
                    "falling" if avg(last 3 days) < 0.8 * avg(days 4-14)
                    else "stable"
    - If fewer than 5 days of history exist, return insufficient_history: True and fall back to simple average.
    - Full precision is maintained throughout calculations, and final values are rounded independently for display.
    """
    # 1. Edge Case & Input Validation (Section 5B)
    for idx, val in enumerate(issued_history):
        if val < 0:
            raise ValueError(f"Issued quantity in history cannot be negative at index {idx}: {val}")

    data_points = len(issued_history)
    insufficient_history = data_points < 5

    if data_points == 0:
        return ForecastOut(
            forecast_per_day=0.0,
            forecast_7day=0.0,
            trend_flag="stable",
            weights_used=[],
            last_14_days=[],
            insufficient_history=True,
            reasoning="No historical issue records available for demand forecasting."
        )

    # Consider up to last 14 days
    window = issued_history[-14:]
    n_window = len(window)

    if insufficient_history:
        # Fallback to simple unweighted average for < 5 data points
        raw_forecast_per_day = sum(window) / float(n_window)
        raw_forecast_7day = raw_forecast_per_day * 7.0

        forecast_per_day = round(raw_forecast_per_day, 2)
        forecast_7day = round(raw_forecast_7day, 2)
        trend_flag = "stable"
        weights_used = [1.0] * n_window
        reasoning = (
            f"Insufficient history ({data_points} days < 5 minimum). "
            f"Using simple unweighted daily average of {forecast_per_day:.2f} units/day (low confidence)."
        )
    else:
        # Weighted moving average with linear weights 1..n_window
        weights = [float(i + 1) for i in range(n_window)]
        total_weight = sum(weights)
        weighted_sum = sum(w * d for w, d in zip(weights, window))
        
        raw_forecast_per_day = weighted_sum / total_weight
        raw_forecast_7day = raw_forecast_per_day * 7.0

        forecast_per_day = round(raw_forecast_per_day, 2)
        forecast_7day = round(raw_forecast_7day, 2)
        weights_used = weights

        # Trend flag calculation: compare avg(last 3 days) vs avg(earlier days: days 4..14)
        last_3 = window[-3:]
        earlier = window[:-3]

        avg_last_3 = sum(last_3) / 3.0
        avg_earlier = sum(earlier) / float(len(earlier)) if earlier else 0.0

        if avg_earlier > 0:
            if avg_last_3 > 1.2 * avg_earlier:
                trend_flag = "rising"
            elif avg_last_3 < 0.8 * avg_earlier:
                trend_flag = "falling"
            else:
                trend_flag = "stable"
        else:
            if avg_last_3 > 0:
                trend_flag = "rising"
            else:
                trend_flag = "stable"

        reasoning = (
            f"7-day demand forecast calculated using {n_window}-day weighted moving average "
            f"(linear decay weights {int(weights[0])}..{int(weights[-1])}). "
            f"Daily forecast: {forecast_per_day:.2f}, 7-day total: {forecast_7day:.2f}. "
            f"Trend identified as '{trend_flag}' based on recent vs earlier window demand."
        )

    return ForecastOut(
        forecast_per_day=forecast_per_day,
        forecast_7day=forecast_7day,
        trend_flag=trend_flag,
        weights_used=weights_used,
        last_14_days=window,
        insufficient_history=insufficient_history,
        reasoning=reasoning
    )
