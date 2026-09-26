import type {
  HealthCheckResponse,
  DemoDataGenerationResponse,
  UploadReport,
  DashboardSummaryOut,
  FacilityOut,
  FacilityDetailOut,
  FacilityMedicineAnalysisOut,
  RescueCaseOut,
  RescueCaseDetailsResponse,
  TransferRecommendation,
  SimulateVerificationIn,
  SimulateVerificationOut,
  FeedbackIn,
  FeedbackOut,
  FeedbackHistoryItemOut,
  SurplusSummaryOut,
  RootCauseOut,
} from "../types/api";

export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new ApiError(
      "Could not reach the MedTrace backend. Confirm it's running and reachable.",
      0
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as unknown as T;
  return (await response.json()) as T;
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiError(
      "Could not reach the MedTrace backend. Confirm it's running and reachable.",
      0
    );
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

/* ------------------------------------------------------------------ */
/* API Service Functions                                             */
/* ------------------------------------------------------------------ */

export function getHealth(): Promise<HealthCheckResponse> {
  return request<HealthCheckResponse>("/health");
}

export function generateDemoData(): Promise<DemoDataGenerationResponse> {
  return request<DemoDataGenerationResponse>("/generate-demo-data", { method: "POST" });
}

export function uploadInventory(file: File): Promise<UploadReport> {
  const formData = new FormData();
  formData.append("file", file);
  return requestForm<UploadReport>("/upload-inventory", formData);
}

export function getDashboardSummary(): Promise<DashboardSummaryOut> {
  return request<DashboardSummaryOut>("/dashboard-summary");
}

export function getFacilities(): Promise<FacilityOut[]> {
  return request<FacilityOut[]>("/facilities");
}

export function getFacilityDetails(facilityId: string): Promise<FacilityDetailOut> {
  return request<FacilityDetailOut>(
    `/facilities/${encodeURIComponent(facilityId)}`
  );
}

export function getFacilityMedicineAnalysis(
  facilityId: string,
  medicineId: string
): Promise<FacilityMedicineAnalysisOut> {
  return request<FacilityMedicineAnalysisOut>(
    `/facilities/${encodeURIComponent(facilityId)}/medicines/${encodeURIComponent(
      medicineId
    )}`
  );
}

export function getRescueQueue(): Promise<RescueCaseOut[]> {
  return request<RescueCaseOut[]>("/rescue-queue");
}

export function getRescueCaseDetails(caseId: number): Promise<RescueCaseDetailsResponse> {
  return request<RescueCaseDetailsResponse>(
    `/rescue-cases/${encodeURIComponent(caseId)}`
  );
}

export function recommendTransfer(
  facilityId: string,
  medicineId: string
): Promise<TransferRecommendation> {
  return request<TransferRecommendation>(
    `/recommend-transfer?facility_id=${encodeURIComponent(
      facilityId
    )}&medicine_id=${encodeURIComponent(medicineId)}`,
    { method: "POST" }
  );
}

export function simulateVerification(
  payload: SimulateVerificationIn
): Promise<SimulateVerificationOut> {
  return request<SimulateVerificationOut>("/simulate-verification", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitFeedback(
  payload: FeedbackIn
): Promise<FeedbackOut> {
  return request<FeedbackOut>("/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFeedbackHistory(): Promise<FeedbackHistoryItemOut[]> {
  return request<FeedbackHistoryItemOut[]>("/feedback");
}

export function getSurplusSummary(): Promise<SurplusSummaryOut> {
  return request<SurplusSummaryOut>("/surplus");
}

export function getRootCauses(): Promise<RootCauseOut[]> {
  return request<RootCauseOut[]>("/root-causes").catch(() => []);
}
