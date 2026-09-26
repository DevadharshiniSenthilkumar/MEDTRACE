from pydantic import BaseModel, Field
from typing import List, Optional

class FacilityOut(BaseModel):
    facility_id: str
    name: str
    lat: float
    lon: float
    facility_type: str
    is_remote: bool = False
    reporting_interval_days: int = 2

class MedicineOut(BaseModel):
    medicine_id: str
    name: str
    unit: str
    shelf_life_days: int
    safety_stock_days: int = 5
    reorder_point_days: int = 10

class InventoryRecordOut(BaseModel):
    record_id: Optional[int] = None
    facility_id: str
    medicine_id: str
    record_date: str
    opening_stock: float
    received: float = 0.0
    issued: float = 0.0
    closing_stock: float
    batch_expiry_date: Optional[str] = None
    is_reported: bool = True

class InventoryStatusOut(BaseModel):
    facility_id: str
    medicine_id: str
    current_stock: float
    avg_daily_demand: float
    days_remaining: float
    safety_stock: float
    status: str  # OK, WATCH, CRITICAL, UNKNOWN — verify
    insufficient_history: bool = False
    reasoning: str

class DashboardSummaryOut(BaseModel):
    total_facilities: int
    total_medicines: int
    total_inventory_records: int
    facilities_at_risk: int
    critical_stockouts: int
    watch_stockouts: int
    unverified_reports: int
    ok_status_count: int
    disclaimer: str = "MedTrace is a decision-support tool. Officer approval required for any stock transfer or action."

class DemoDataGenerationResponse(BaseModel):
    status: str
    facilities_count: int
    medicines_count: int
    inventory_records_count: int
    seeded_cases: List[str]
    message: str

class ForecastOut(BaseModel):
    forecast_per_day: float
    forecast_7day: float
    trend_flag: str
    weights_used: List[float]
    last_14_days: List[float]
    insufficient_history: bool = False
    reasoning: str

class StockTruthOut(BaseModel):
    recency_score: float
    completeness_score: float
    consistency_score: float
    total: float
    reason: str

class RiskOut(BaseModel):
    risk_level: str
    confidence: float
    recommended_action: str
    reasoning: str

class FacilityMedicineAnalysisOut(BaseModel):
    facility_id: str
    medicine_id: str
    inventory_status: InventoryStatusOut
    demand_forecast: ForecastOut
    stock_truth: StockTruthOut
    risk_assessment: RiskOut

class TransferRecommendation(BaseModel):
    status: str = "RECOMMENDED"
    donor_facility_id: Optional[str] = None
    donor_facility_name: Optional[str] = None
    recipient_facility_id: str
    recipient_facility_name: Optional[str] = None
    quantity: float
    distance_km: float
    reason: str
    fairness_proof: str
    alternative_considered: Optional[str] = None
    covers_days: float

class SimulateVerificationIn(BaseModel):
    case_id: int
    corrected_physical_count: float
    notes: Optional[str] = None

class SimulateVerificationOut(BaseModel):
    case_id: int
    status_action: str  # CANCELLED, RE_REVIEW_REQUIRED, UPDATED
    reasoning: str
    before: dict
    after: dict

class RescueCaseOut(BaseModel):
    case_id: int
    facility_id: str
    medicine_id: str
    risk_level: str
    confidence: float
    stock_truth_score: float
    recommended_action: str
    created_at: str
    status: str

class RootCauseOut(BaseModel):
    facility_id: str
    medicine_id: str
    pattern_label: str
    evidence: str

class FeedbackIn(BaseModel):
    case_id: int
    officer_decision: str  # APPROVED, REJECTED, VERIFIED
    notes: Optional[str] = None

class FacilityDetailOut(BaseModel):
    facility: FacilityOut
    medicines: List[FacilityMedicineAnalysisOut]

class UploadErrorWarning(BaseModel):
    row: int
    message: str

class UploadReport(BaseModel):
    rows_processed: int
    accepted: bool
    errors: List[UploadErrorWarning]
    warnings: List[UploadErrorWarning]

class FeedbackOut(BaseModel):
    feedback_id: int
    case_id: int
    officer_decision: str
    notes: Optional[str] = None
    decided_at: str

class SurplusItemOut(BaseModel):
    facility_id: str
    facility_name: str
    medicine_id: str
    medicine_name: str
    current_stock: float
    safety_stock: float
    donor_surplus: float
    stock_truth_score: float
    latest_record_date: Optional[str] = None
    batch_expiry_date: Optional[str] = None

class SurplusSummaryOut(BaseModel):
    eligible_surplus: List[SurplusItemOut]
    near_expiry_candidates: List[dict]

class FeedbackHistoryItemOut(BaseModel):
    feedback_id: int
    case_id: int
    facility_id: Optional[str] = None
    medicine_id: Optional[str] = None
    risk_level: Optional[str] = None
    officer_decision: str
    notes: Optional[str] = None
    decided_at: str


