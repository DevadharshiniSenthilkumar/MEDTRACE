from typing import Dict, Any, List, Optional
import sqlite3
from app.surplus_engine import find_eligible_donors, get_facility_stock_and_truth

def optimize_rescue_transfer(
    conn: sqlite3.Connection,
    recipient_facility_id: str,
    medicine_id: str
) -> Dict[str, Any]:
    """
    Module 8 — Rescue Transfer Optimiser
    
    Ranks eligible donors using:
    donor_score = (quantity_available_weight * 0.4)
                + ((1 / max(distance_km, 1)) * 0.4)
                + ((donor.stock_truth_score / 100) * 0.2)
    where quantity_available_weight is normalized to [0.0, 1.0] relative to max eligible surplus.
    
    HARD CONSTRAINT (Fairness Rule):
    Evaluates whether candidate donor can supply the recipient's FULL 7-day target rescue quantity
    (needed_quantity) without dropping below its own safety stock:
        assert (donor.current_stock - needed_quantity) >= donor.safety_stock
    If this assertion fails, the donor is SKIPPED entirely for fairness, and the system moves to the next best donor.
    """
    recipient_info = get_facility_stock_and_truth(conn, recipient_facility_id, medicine_id)
    if not recipient_info:
        return {
            "status": "no_safe_donor_available",
            "reason": f"Recipient facility '{recipient_facility_id}' or medicine '{medicine_id}' not found.",
            "donor_facility_id": None,
            "recipient_facility_id": recipient_facility_id,
            "quantity": 0.0,
            "distance_km": 0.0,
            "fairness_proof": "N/A",
            "alternative_considered": None,
            "covers_days": 0.0
        }

    rec_avg_demand = recipient_info["avg_daily_demand"]
    target_cover_days = 7.0
    needed_quantity = rec_avg_demand * target_cover_days

    eligible_donors = find_eligible_donors(conn, recipient_facility_id, medicine_id)

    if not eligible_donors:
        return {
            "status": "no_safe_donor_available",
            "reason": (
                f"No safe donor available for {recipient_info['name']}. Every nearby facility is either "
                f"untrustworthy (Stock Truth Score < 50) or has no surplus above its safety stock."
            ),
            "donor_facility_id": None,
            "recipient_facility_id": recipient_facility_id,
            "quantity": 0.0,
            "distance_km": 0.0,
            "fairness_proof": "No donor met safety & truth criteria.",
            "alternative_considered": None,
            "covers_days": 0.0
        }

    max_surplus = max(d["donor_surplus"] for d in eligible_donors)

    # Score candidates
    scored_donors = []
    for d in eligible_donors:
        max_safe_transfer = max(0.0, d["current_stock"] - d["safety_stock"])
        quantity = min(max_safe_transfer, needed_quantity if needed_quantity > 0 else max_safe_transfer)

        qty_weight = (d["donor_surplus"] / max_surplus) if max_surplus > 0 else 1.0
        qty_weight = min(1.0, max(0.0, qty_weight))

        dist_km = max(d["distance_km"], 1.0)
        truth_factor = d["stock_truth_score"] / 100.0

        donor_score = (qty_weight * 0.4) + ((1.0 / dist_km) * 0.4) + (truth_factor * 0.2)

        d_entry = dict(d)
        d_entry["max_safe_transfer"] = max_safe_transfer
        d_entry["quantity"] = quantity
        d_entry["donor_score"] = round(donor_score, 4)
        scored_donors.append(d_entry)

    # Rank ALL eligible donors by donor_score descending
    scored_donors.sort(key=lambda x: x["donor_score"], reverse=True)

    # Find physically nearest donor
    nearest_donor = min(scored_donors, key=lambda x: x["distance_km"])

    selected_donor = None
    alternative_considered = None

    for candidate in scored_donors:
        req_quantity = needed_quantity if needed_quantity > 0 else candidate["quantity"]

        # HARD CONSTRAINT / FAIRNESS RULE ASSERTION:
        # Check if donor's remaining stock stays >= safety_stock if full requested rescue quantity is transferred
        remaining_stock_if_transferred = candidate["current_stock"] - req_quantity
        is_fair = remaining_stock_if_transferred >= (candidate["safety_stock"] - 1e-6)

        try:
            assert is_fair, (
                f"Fairness assertion failed for {candidate['name']}: transferring requested {req_quantity:.1f} units "
                f"leaves remaining stock {remaining_stock_if_transferred:.1f} < safety stock threshold {candidate['safety_stock']:.1f}."
            )
        except AssertionError:
            alternative_considered = (
                f"{candidate['name']} is closer ({candidate['distance_km']:.1f}km) but transferring "
                f"the required {req_quantity:.1f} units would drop it below its own safety stock ({candidate['safety_stock']:.1f}); "
                f"skipping for fairness."
            )
            continue

        selected_donor = candidate
        break

    # If nearest donor was skipped due to fairness constraint or score ranking, log in alternative_considered
    if selected_donor and nearest_donor["facility_id"] != selected_donor["facility_id"] and not alternative_considered:
        near_req = needed_quantity if needed_quantity > 0 else nearest_donor["quantity"]
        near_remaining = nearest_donor["current_stock"] - near_req
        if near_remaining < (nearest_donor["safety_stock"] - 1e-6):
            alternative_considered = (
                f"{nearest_donor['name']} is closer ({nearest_donor['distance_km']:.1f}km) but transferring "
                f"the required {near_req:.1f} units would drop it below its own safety stock ({nearest_donor['safety_stock']:.1f}); "
                f"recommending {selected_donor['name']} ({selected_donor['distance_km']:.1f}km) instead, which stays safely above threshold."
            )
        else:
            alternative_considered = (
                f"{nearest_donor['name']} is closer ({nearest_donor['distance_km']:.1f}km), but "
                f"{selected_donor['name']} scored higher overall (Score: {selected_donor['donor_score']:.3f} vs {nearest_donor['donor_score']:.3f}) "
                f"due to larger surplus and higher data trust."
            )

    if not selected_donor:
        return {
            "status": "no_safe_donor_available",
            "reason": "All candidate donors failed the hard safety stock fairness check for the full requested quantity.",
            "donor_facility_id": None,
            "recipient_facility_id": recipient_facility_id,
            "quantity": 0.0,
            "distance_km": 0.0,
            "fairness_proof": "N/A",
            "alternative_considered": alternative_considered,
            "covers_days": 0.0
        }

    quantity = round(selected_donor["quantity"], 1)
    covers_days = round(quantity / rec_avg_demand, 1) if rec_avg_demand > 0 else 7.0
    fairness_proof = (
        f"Donor '{selected_donor['name']}' current stock ({selected_donor['current_stock']:.1f}) - transfer quantity ({quantity:.1f}) "
        f"= {selected_donor['current_stock'] - quantity:.1f} >= safety stock ({selected_donor['safety_stock']:.1f}). "
        f"Fairness threshold preserved."
    )

    reason = (
        f"Recommending transfer of {quantity:.1f} units from {selected_donor['name']} ({selected_donor['distance_km']:.1f}km) "
        f"to {recipient_info['name']}. Donor score: {selected_donor['donor_score']:.3f} (Surplus weight: 0.4, Distance weight: 0.4, "
        f"Truth weight: 0.2). Target cover: {covers_days:.1f} days."
    )

    return {
        "status": "RECOMMENDED",
        "donor_facility_id": selected_donor["facility_id"],
        "donor_facility_name": selected_donor["name"],
        "recipient_facility_id": recipient_facility_id,
        "recipient_facility_name": recipient_info["name"],
        "quantity": quantity,
        "distance_km": selected_donor["distance_km"],
        "reason": reason,
        "fairness_proof": fairness_proof,
        "alternative_considered": alternative_considered,
        "covers_days": covers_days
    }
