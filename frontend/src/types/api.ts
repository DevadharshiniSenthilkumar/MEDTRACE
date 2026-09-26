/**
 * Ground truth API types for MedTrace Frontend.
 * Matches backend/app/schemas.py and OpenAPI spec field-for-field.
 */

export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "OK" | "UNKNOWN — verify" | string;

export interface HealthCheckResponse {
  status: string;
  app: string;
  version: string;
}

export interface FacilityOut {
  facility_id: string;
  name: string;
  lat: number;
  lon: number;
  facility_type: string;
  is_remote?: boolean;
  reporting_interval_days?: number;
}

export interface MedicineOut {
  medicine_id: string;
  name: string;
  unit: string;
  shelf_life_days: number;
  safety_stock_days?: number;
  reorder_point_days?: number;
}

export interface InventoryRecordOut {
  record_id?: number | null;
  facility_id: string;
  medicine_id: string;
  record_date: string;
  opening_stock: number;
  received?: number;
  issued?: number;
  closing_stock: number;
  batch_expiry_date?: string | null;
  is_reported?: boolean;
}

export interface InventoryStatusOut {
  facility_id: string;
  medicine_id: string;
  current_stock: number;
  avg_daily_demand: number;
  days_remaining: number;
  safety_stock: number;
  status: string;
  insufficient_history?: boolean;
  reasoning: string;
}

export interface ForecastOut {
  forecast_per_day: number;
  forecast_7day: number;
  trend_flag: string;
  weights_used: number[];
  last_14_days: number[];
  insufficient_history?: boolean;
  reasoning: string;
}

export interface StockTruthOut {
  recency_score: number;
  completeness_score: number;
  consistency_score: number;
  total: number;
  reason: string;
}

export interface RiskOut {
  risk_level: string;
  confidence: number;
  recommended_action: string;
  reasoning: string;
}

export interface FacilityMedicineAnalysisOut {
  facility_id: string;
  medicine_id: string;
  inventory_status: InventoryStatusOut;
  demand_forecast: ForecastOut;
  stock_truth: StockTruthOut;
  risk_assessment: RiskOut;
}

export interface FacilityDetailOut {
  facility: FacilityOut;
  medicines: FacilityMedicineAnalysisOut[];
}

export interface DashboardSummaryOut {
  total_facilities: number;
  total_medicines: number;
  total_inventory_records: number;
  facilities_at_risk: number;
  critical_stockouts: number;
  watch_stockouts: number;
  unverified_reports: number;
  ok_status_count: number;
  disclaimer?: string;
}

export interface DemoDataGenerationResponse {
  status: string;
  facilities_count: number;
  medicines_count: number;
  inventory_records_count: number;
  seeded_cases: string[];
  message: string;
}

export interface RescueCaseOut {
  case_id: number;
  facility_id: string;
  medicine_id: string;
  risk_level: string;
  confidence: number;
  stock_truth_score: number;
  recommended_action: string;
  created_at: string;
  status: string;
}

export interface TransferRecommendation {
  status?: string;
  donor_facility_id?: string | null;
  donor_facility_name?: string | null;
  recipient_facility_id: string;
  recipient_facility_name?: string | null;
  quantity: number;
  distance_km: number;
  reason: string;
  fairness_proof: string;
  alternative_considered?: string | null;
  covers_days: number;
}

export interface SimulateVerificationIn {
  case_id: number;
  corrected_physical_count: number;
  notes?: string | null;
}

export interface SimulationStatePair {
  analysis: FacilityMedicineAnalysisOut;
  recommendation: TransferRecommendation;
}

export interface SimulateVerificationOut {
  case_id: number;
  status_action: string; // CANCELLED, RE_REVIEW_REQUIRED, UPDATED
  reasoning: string;
  before: SimulationStatePair;
  after: SimulationStatePair;
}

export interface RescueCaseDetailsResponse {
  case: RescueCaseOut;
  analysis: FacilityMedicineAnalysisOut;
  transfer_recommendation: TransferRecommendation;
}

export interface UploadErrorWarning {
  row: number;
  message: string;
}

export interface UploadReport {
  rows_processed: number;
  accepted: boolean;
  errors: UploadErrorWarning[];
  warnings: UploadErrorWarning[];
}

export interface FeedbackIn {
  case_id: number;
  officer_decision: "APPROVED" | "REJECTED" | "VERIFIED" | string;
  notes?: string | null;
}

export interface FeedbackOut {
  feedback_id: number;
  case_id: number;
  officer_decision: string;
  notes?: string | null;
  decided_at: string;
}

export interface FeedbackHistoryItemOut {
  feedback_id: number;
  case_id: number;
  facility_id?: string | null;
  medicine_id?: string | null;
  risk_level?: string | null;
  officer_decision: string;
  notes?: string | null;
  decided_at: string;
}

export interface SurplusItemOut {
  facility_id: string;
  facility_name: string;
  medicine_id: string;
  medicine_name: string;
  current_stock: number;
  safety_stock: number;
  donor_surplus: number;
  stock_truth_score: number;
  latest_record_date?: string | null;
  batch_expiry_date?: string | null;
}

export interface NearExpiryCandidate {
  holding_facility_id: string;
  holding_facility_name: string;
  recipient_facility_id: string;
  recipient_facility_name: string;
  medicine_id: string;
  batch_expiry_date: string;
  days_to_expiry: number;
  days_remaining_holding: number;
  recipient_risk_level: string;
  distance_km: number;
}

export interface SurplusSummaryOut {
  eligible_surplus: SurplusItemOut[];
  near_expiry_candidates: NearExpiryCandidate[];
}

export interface RootCauseOut {
  facility_id: string;
  medicine_id: string;
  pattern_label: string;
  evidence: string;
}
