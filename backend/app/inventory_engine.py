from typing import List, Optional
import math
from app.schemas import InventoryStatusOut
from app.stock_truth_engine import compute_stock_truth_score, TRUTH_THRESHOLD

CRITICAL_DAYS = 3.0
WATCH_DAYS = 7.0
DEFAULT_LOOKBACK_DAYS = 14

def compute_inventory_status(
    facility_id: str,
    medicine_id: str,
    opening_stock: float,
    received: float,
    issued: float,
    issued_history: List[float],
    safety_stock_days: int = 5,
    lookback_window_days: int = DEFAULT_LOOKBACK_DAYS,
    truth_score: Optional[float] = None,
    days_since_last_report: float = 0.0,
    expected_interval: float = 2.0,
    actual_reports_received: Optional[int] = None,
    days_elapsed: float = 1.0
) -> InventoryStatusOut:
    """
    Computes current stock status according to Module 3 (Section 5) formulas.
    
    Integrates with Module 5 (Stock Truth Score Engine) when truth_score is not explicitly provided.
    
    Status classification:
    - truth_score < TRUTH_THRESHOLD (50): "UNKNOWN — verify"
    - days_remaining <= 3: "CRITICAL"
    - days_remaining <= 7: "WATCH"
    - else: "OK"
    """
    # 1. Input Validation (Section 5B Edge Cases)
    if opening_stock < 0 or received < 0 or issued < 0:
        raise ValueError(f"Stock quantities cannot be negative. Got opening={opening_stock}, received={received}, issued={issued}")
    
    if issued > (opening_stock + received):
        raise ValueError(f"Issued quantity ({issued}) cannot exceed opening stock + received ({opening_stock + received})")
    
    for idx, val in enumerate(issued_history):
        if val < 0:
            raise ValueError(f"Historical issued quantity at index {idx} cannot be negative: {val}")

    # 2. Current Stock Calculation
    current_stock = opening_stock + received - issued

    # 3. Demand and History Calculation
    insufficient_history = False
    if len(issued_history) < 5:
        insufficient_history = True

    # Use the available history up to lookback_window_days
    recent_history = issued_history[-lookback_window_days:] if issued_history else []
    
    if recent_history:
        effective_days = max(len(recent_history), 1)
        avg_daily_demand = sum(recent_history) / float(effective_days)
    else:
        avg_daily_demand = 0.0

    # 4. Compute Real Stock Truth Score if not explicitly passed
    if truth_score is None:
        reports_count = actual_reports_received if actual_reports_received is not None else len(issued_history)
        truth_res = compute_stock_truth_score(
            days_since_last_report=days_since_last_report,
            expected_interval=expected_interval,
            actual_reports_received=reports_count,
            window_days=lookback_window_days,
            opening_stock=opening_stock,
            received=received,
            reported_closing=current_stock,
            avg_daily_demand=avg_daily_demand,
            days_elapsed=days_elapsed
        )
        truth_score = truth_res.total

    # 5. Days Remaining & Safety Stock
    if avg_daily_demand > 0:
        days_remaining = current_stock / avg_daily_demand
    else:
        days_remaining = float('inf')

    safety_stock = safety_stock_days * avg_daily_demand

    # 6. Status & Reasoning Determination
    reasons = []

    if truth_score < TRUTH_THRESHOLD:
        status = "UNKNOWN — verify"
        reasons.append(f"Stock Truth Score ({truth_score:.1f}) is below threshold ({TRUTH_THRESHOLD}) — physical verification required before trusting stock status.")
    elif days_remaining <= CRITICAL_DAYS:
        status = "CRITICAL"
        reasons.append(f"Estimated days remaining ({days_remaining:.1f} days) is <= critical threshold ({CRITICAL_DAYS} days).")
    elif days_remaining <= WATCH_DAYS:
        status = "WATCH"
        reasons.append(f"Estimated days remaining ({days_remaining:.1f} days) is <= watch threshold ({WATCH_DAYS} days).")
    else:
        status = "OK"
        if days_remaining == float('inf'):
            reasons.append("Stock level is healthy with zero recorded daily demand over lookback period.")
        else:
            reasons.append(f"Stock level is healthy ({days_remaining:.1f} days remaining).")

    if insufficient_history:
        reasons.append(f"Note: Only {len(issued_history)} days of history available (< 5 days minimum). Confidence is low.")

    if avg_daily_demand == 0.0 and len(issued_history) >= 5:
        reasons.append("Zero daily demand recorded over lookback period.")

    return InventoryStatusOut(
        facility_id=facility_id,
        medicine_id=medicine_id,
        current_stock=current_stock,
        avg_daily_demand=round(avg_daily_demand, 2),
        days_remaining=round(days_remaining, 2) if days_remaining != float('inf') else float('inf'),
        safety_stock=round(safety_stock, 2),
        status=status,
        insufficient_history=insufficient_history,
        reasoning=" ".join(reasons)
    )
