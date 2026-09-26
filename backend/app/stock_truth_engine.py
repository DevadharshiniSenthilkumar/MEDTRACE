from typing import Optional
from app.schemas import StockTruthOut

TRUTH_THRESHOLD = 50.0

def compute_stock_truth_score(
    days_since_last_report: float,
    expected_interval: float = 2.0,
    actual_reports_received: int = 7,
    window_days: int = 14,
    opening_stock: float = 0.0,
    received: float = 0.0,
    reported_closing: float = 0.0,
    avg_daily_demand: float = 0.0,
    days_elapsed: float = 1.0
) -> StockTruthOut:
    """
    Module 5: Stock Truth / Reporting-Gap Engine (Section 5, PROJECT_SPEC.md)
    
    Computes a Stock Truth Score (0–100) based on three weighted sub-scores:
    1. Recency Score (0-40): How recent is the last report compared to expected interval.
    2. Completeness Score (0-30): Proportion of expected reports received in window.
    3. Consistency Score (0-30): Deviation between reported closing stock and expected closing stock.
    
    Total score < TRUTH_THRESHOLD (50) indicates unverified / untrustworthy report.
    """
    # 1. Edge Case & Input Validation (Section 5B)
    if days_since_last_report < 0:
        raise ValueError(f"days_since_last_report cannot be negative: {days_since_last_report}")
    if expected_interval <= 0:
        raise ValueError(f"expected_interval must be positive: {expected_interval}")
    if actual_reports_received < 0:
        raise ValueError(f"actual_reports_received cannot be negative: {actual_reports_received}")
    if window_days <= 0:
        raise ValueError(f"window_days must be positive: {window_days}")
    if opening_stock < 0 or received < 0 or reported_closing < 0 or avg_daily_demand < 0 or days_elapsed < 0:
        raise ValueError(f"Stock, demand, and elapsed values cannot be negative. Got opening={opening_stock}, received={received}, reported_closing={reported_closing}, avg_daily_demand={avg_daily_demand}, days_elapsed={days_elapsed}")

    # 2. Recency Score (0-40)
    ratio = days_since_last_report / float(expected_interval)
    if ratio <= 1.0:
        recency_score = 40.0
    elif 1.0 < ratio < 2.0:
        recency_score = 40.0 * (2.0 - ratio)
    else:
        recency_score = 0.0

    # 3. Completeness Score (0-30)
    expected_reports_in_window = float(window_days) / float(expected_interval)
    if expected_reports_in_window > 0:
        completeness_ratio = float(actual_reports_received) / expected_reports_in_window
        completeness_score = min(30.0, 30.0 * completeness_ratio)
    else:
        completeness_score = 0.0

    # 4. Consistency Score (0-30)
    expected_closing = max(0.0, opening_stock + received - (avg_daily_demand * days_elapsed))
    denom = max(expected_closing, 1.0)
    deviation_pct = abs(reported_closing - expected_closing) / denom

    if deviation_pct <= 0.1:
        consistency_score = 30.0
    elif 0.1 < deviation_pct < 1.0:
        consistency_score = 30.0 * (1.0 - deviation_pct)
    else:
        consistency_score = 0.0

    # Total Score
    total = recency_score + completeness_score + consistency_score
    total = round(max(0.0, min(100.0, total)), 1)
    recency_score = round(recency_score, 1)
    completeness_score = round(completeness_score, 1)
    consistency_score = round(consistency_score, 1)

    # 5. Reasoning String Construction
    reasons = []
    if days_since_last_report > expected_interval:
        reasons.append(
            f"Last report received {days_since_last_report:.1f} days ago (expected every {expected_interval:.1f} days)."
        )
    else:
        reasons.append(f"Report recency is optimal ({days_since_last_report:.1f} days ago).")

    if completeness_score < 30.0:
        reasons.append(
            f"Completeness is {completeness_score:.1f}/30 ({actual_reports_received} reports received vs {expected_reports_in_window:.1f} expected)."
        )
    
    if consistency_score < 30.0:
        reasons.append(
            f"Consistency score is {consistency_score:.1f}/30 (reported closing {reported_closing:.1f} deviates from expected {expected_closing:.1f})."
        )

    if total < TRUTH_THRESHOLD:
        reasons.append(f"Stock Truth Score ({total:.1f}) is below threshold ({TRUTH_THRESHOLD}) — treat stock data as UNVERIFIED.")
    else:
        reasons.append(f"Stock Truth Score ({total:.1f}) is healthy (>= {TRUTH_THRESHOLD}).")

    return StockTruthOut(
        recency_score=recency_score,
        completeness_score=completeness_score,
        consistency_score=consistency_score,
        total=total,
        reason=" ".join(reasons)
    )
