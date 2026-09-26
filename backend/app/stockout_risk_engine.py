from typing import Optional
import sqlite3
from app.schemas import RiskOut

TRUTH_THRESHOLD = 50.0

def compute_stockout_risk(
    days_remaining: float,
    trend_flag: str,
    stock_truth_score: float,
    data_points: int
) -> RiskOut:
    """
    Module 6: Stockout Risk Engine (Section 5, PROJECT_SPEC.md)
    
    Combines days-of-stock-remaining, forecast trend, and Stock Truth Score into a single risk level
    (LOW, MEDIUM, HIGH, CRITICAL, or UNVERIFIED) with a confidence score.
    """
    # 1. Edge Case & Input Validation (Section 5B)
    if stock_truth_score < 0.0 or stock_truth_score > 100.0:
        raise ValueError(f"stock_truth_score must be between 0 and 100. Got: {stock_truth_score}")
    if days_remaining < 0.0 and days_remaining != float('inf'):
        raise ValueError(f"days_remaining cannot be negative: {days_remaining}")
    if data_points < 0:
        raise ValueError(f"data_points cannot be negative: {data_points}")

    # 2. Risk Evaluation
    if stock_truth_score < TRUTH_THRESHOLD:
        risk_level = "UNVERIFIED"
        recommended_action = "verify_physical_stock"
        confidence = round(stock_truth_score / 100.0, 2)
        reasoning = (
            f"Stock Truth Score ({stock_truth_score:.1f}) is below threshold ({TRUTH_THRESHOLD}). "
            f"Risk classified as UNVERIFIED. Action required: verify physical stock before taking action. "
            f"(Confidence: {confidence * 100:.0f}%)"
        )
    else:
        if days_remaining <= 2.0:
            risk_level = "CRITICAL"
        elif days_remaining <= 5.0:
            risk_level = "HIGH"
        elif days_remaining <= 10.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        initial_risk = risk_level
        if trend_flag == "rising":
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            elif risk_level == "MEDIUM":
                risk_level = "HIGH"
            elif risk_level == "HIGH":
                risk_level = "CRITICAL"

        recommended_action = "consider_transfer" if risk_level in ("CRITICAL", "HIGH") else "monitor"
        
        history_factor = 1.0 if data_points >= 14 else (data_points / 14.0)
        confidence = min(1.0, (stock_truth_score / 100.0) * history_factor)
        confidence = round(confidence, 2)

        trend_note = f" (bumped from {initial_risk} due to rising demand trend)" if trend_flag == "rising" and initial_risk != risk_level else ""
        days_str = "infinite" if days_remaining == float('inf') else f"{days_remaining:.1f}"

        reasoning = (
            f"Days remaining: {days_str} days. Evaluated risk level: {risk_level}{trend_note}. "
            f"Recommended action: '{recommended_action}'. Confidence: {confidence * 100:.0f}% "
            f"(Truth Score: {stock_truth_score:.1f}, Data Points: {data_points})."
        )

    return RiskOut(
        risk_level=risk_level,
        confidence=confidence,
        recommended_action=recommended_action,
        reasoning=reasoning
    )


def save_rescue_case(
    conn: sqlite3.Connection,
    facility_id: str,
    medicine_id: str,
    risk_level: str,
    confidence: float,
    stock_truth_score: float,
    recommended_action: str
) -> int:
    """
    PERSISTENCE: Every computed risk case from the Stockout Risk Engine must now be saved
    into the rescue_cases table.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT case_id FROM rescue_cases
        WHERE facility_id = ? AND medicine_id = ? AND status = 'OPEN'
        ORDER BY created_at DESC LIMIT 1;
    """, (facility_id, medicine_id))
    existing = cursor.fetchone()
    if existing:
        case_id = existing["case_id"]
        cursor.execute("""
            UPDATE rescue_cases
            SET risk_level = ?, confidence = ?, stock_truth_score = ?, recommended_action = ?
            WHERE case_id = ?;
        """, (risk_level, confidence, stock_truth_score, recommended_action, case_id))
        conn.commit()
        return case_id
    else:
        cursor.execute("""
            INSERT INTO rescue_cases (facility_id, medicine_id, risk_level, confidence, stock_truth_score, recommended_action, status)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN');
        """, (facility_id, medicine_id, risk_level, confidence, stock_truth_score, recommended_action))
        conn.commit()
        return cursor.lastrowid
