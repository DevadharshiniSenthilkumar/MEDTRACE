# MASTER BUILD PROMPT — MedTrace (PS-03-S2: Predicting Medicine Stockouts Before They Happen)

> Paste this entire prompt into your AI coding tool (Antigravity, Claude Code, Cursor, etc.) with an empty `medtrace/` folder open. It describes the FULL product — every module, every API, every page, every novelty feature, and every safety rule from the blueprint — so the agent can build it end-to-end instead of just Phase 1.

---

## 0. Role and Ground Rules

You are a senior full-stack engineer building a hackathon-grade but production-structured web app called **MedTrace**. Follow these rules at all times:

- Use **Python FastAPI** for the backend, **React + Vite + Axios + Plotly** for the frontend, **SQLite** for storage, **Pandas/NumPy** for data processing. No paid APIs, no external hospital hardware, no real patient/government data.
- Every forecast, score, and recommendation must be **explainable** (show the numbers and the reasoning), never a black box.
- MedTrace is a **decision-support tool**, not an autonomous system. It must never claim to diagnose, never claim to auto-transfer medicine, and every risky action must require **explicit officer approval**.
- Language discipline everywhere in UI copy, API messages, and logs: say **"possible stockout"**, **"verification required"**, **"officer approval required"** — never "confirmed stockout" or "medicine has been transferred."
- Never state real-world accuracy numbers unless computed on clearly labeled synthetic/test data, and never claim the prototype has already helped real patients.
- Any "transfer" the system recommends is a **recommendation only**; it must display a disclaimer that real deployments require compliance with medicine quality, cold-chain, expiry, and government-policy rules.
- Build in the phase order in Section 7, but this prompt's scope is the **entire product**, not just Phase 1 — keep building through all phases unless told to stop.
- After each phase, report: files changed, exact terminal commands to run/test, tests performed, and known limitations.
- **The backend is the product. The frontend is a thin client.** All forecasting, scoring, risk classification, surplus matching, fairness checks, and root-cause logic MUST live in the backend engines (Section 5 / 5A), fully testable via `/docs` and `pytest` with zero frontend running. The React app must contain **no business logic** — it only calls endpoints and renders what they return. If you find yourself computing a score, a status label, or a recommendation inside a React component, stop and move that logic to the correct backend engine file instead.
- Every backend engine must be a plain, importable Python function/class with typed inputs and outputs (Pydantic models), independent of FastAPI, so it can be unit-tested in isolation without spinning up the server.
- Every engine must validate its own inputs and raise clear, typed exceptions (not silent `None`s or crashes) for bad data — see Section 5B for the exact edge cases to handle.

---

## 1. One-Line Product Definition

MedTrace predicts medicine shortages, checks whether the reported stock data can be trusted, finds nearby safe surplus, and recommends an officer-approved rescue action before patients are turned away.

**Hidden problem MedTrace solves (must be visible in the product, not just the pitch):** medicine, information, and decisions are disconnected. A "stock = 0" reading can mean a real shortage OR a stale/missing report. A "healthy" facility might be sitting on unusable near-expiry stock while a nearby facility runs dry. Repeated alerts at one facility may mean a procurement problem, not a forecasting failure.

---

## 2. Tech Stack (use exactly this, do not over-engineer)

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + Vite + Axios + Plotly | Dashboard, rescue queue, trend charts |
| Backend | Python FastAPI | REST API + auto docs at `/docs` |
| Data processing | Pandas + NumPy | CSV parsing, stock/demand math |
| Forecasting | Weighted moving average / explainable rules | No deep learning for MVP |
| Database | SQLite | Feedback, recommendations, case history |
| Optimisation | Deterministic scoring rules (OR-Tools optional later) | Keep it explainable |
| Version control | Git + GitHub | Single source of truth — no parallel builds in other tools |

---

## 3. Final Project Structure

Create exactly this structure inside `medtrace/`:

```
medtrace/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── synthetic_data.py
│   │   ├── validator.py
│   │   ├── inventory_engine.py
│   │   ├── forecast_engine.py
│   │   ├── stock_truth_engine.py
│   │   ├── stockout_risk_engine.py
│   │   ├── surplus_engine.py
│   │   ├── transfer_optimizer.py
│   │   ├── root_cause_engine.py
│   │   └── database.py
│   ├── data/
│   │   ├── facilities.csv
│   │   ├── medicine_config.csv
│   │   └── inventory_records.csv
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/api.js
│   ├── .env
│   └── package.json
├── README.md
└── .gitignore
```

---

## 4. Core End-to-End Workflow

```
Health officer uploads data OR clicks "Load Demo Data"
        ↓
MedTrace validates the data
        ↓
Calculates current stock + demand forecast
        ↓
Computes Stock Truth Score (is the report even trustworthy?)
        ↓
Classifies stockout risk (confidence-weighted)
        ↓
Searches for safe surplus / near-expiry matches nearby
        ↓
Recommends a fair rescue transfer OR "verify stock first"
        ↓
Officer approves / rejects / requests verification
        ↓
Feedback + outcome saved → feeds Root-Cause Engine
```

Build every module below so this pipeline runs completely, end-to-end, on demo data.

---

## 5. Every Module — Full Functional Spec

### Module 1 — Demo Data Generator (`synthetic_data.py`) — MUST
- Generate **20 fictional PHCs** with lat/long, type (PHC/donor/remote), and a defined safety-stock policy per facility.
- Generate **8 essential medicines** (e.g., insulin, ORS, anti-TB drugs, antivenom, antibiotics, plus 3 more), each with unit size, shelf life, and reorder point.
- Generate **90 days of daily inventory + issue records** per facility × medicine.
- Deliberately seed the following **hidden cases** into the data so the demo can showcase them:
  - a real, fast-approaching stockout,
  - a phantom/stale report (stock looks like 0 but reporting simply stopped),
  - a hidden surplus facility nearby,
  - near-expiry stock sitting unused,
  - a sudden demand spike,
  - a chronic/repeat stockout facility (procurement pattern),
  - an unfair-transfer trap (nearest donor is actually a protected remote facility).
- Expose via `POST /generate-demo-data`.

### Module 2 — CSV Upload + Validator (`validator.py`) — MUST
- Accept uploaded CSVs matching `facilities.csv`, `medicine_config.csv`, `inventory_records.csv` schemas.
- Validate: date formats/ranges, non-negative quantities, duplicate rows, missing/late reports, and stock-balance mismatches (opening + received − issued ≠ closing).
- Return a structured validation report (errors, warnings, row references) — never silently "fix" bad data.
- Expose via `POST /upload-inventory`.

### Module 3 — Inventory Status Engine (`inventory_engine.py`) — MUST
- Compute current stock, average daily demand, days-of-stock-remaining, safety stock level, and a status label (`OK`, `WATCH`, `CRITICAL`, `UNKNOWN — verify`).
- `UNKNOWN — verify` is used whenever the Stock Truth Score (Module 5) is too low to trust a `0` or near-zero reading.
- **Exact logic to implement:**
  ```
  current_stock       = opening_stock + received − issued   (rolling, from inventory_records)
  avg_daily_demand     = sum(issued over lookback_window_days) / lookback_window_days   # default lookback = 14 days
  days_remaining       = current_stock / avg_daily_demand   if avg_daily_demand > 0 else float('inf')
  safety_stock         = medicine_config.safety_stock_days * avg_daily_demand   # per facility-medicine
  status:
      if truth_score < TRUTH_THRESHOLD (see Module 5):       "UNKNOWN — verify"
      elif days_remaining <= CRITICAL_DAYS (default 3):      "CRITICAL"
      elif days_remaining <= WATCH_DAYS (default 7):         "WATCH"
      else:                                                  "OK"
  ```
- Handle `avg_daily_demand == 0` explicitly (no divide-by-zero) — treat as "insufficient demand history," not as "infinite days remaining" being a good thing.

### Module 4 — Demand Forecast Engine (`forecast_engine.py`) — MUST
- Forecast next 7-day demand using an **explainable weighted moving average** (recent days weighted higher).
- Output must include the formula/weights used and the last N data points, so the number is never a black box.
- **Exact logic to implement:**
  ```
  Given the last N=14 days of daily issued quantities [d1..d14] (d14 = most recent):
  weight_i           = i   (so day 14 gets weight 14, day 1 gets weight 1) — linear decay, simplest to explain
  forecast_per_day   = sum(weight_i * d_i for i in 1..14) / sum(weight_i for i in 1..14)
  forecast_7day      = forecast_per_day * 7
  trend_flag         = "rising" if avg(last 3 days) > 1.2 * avg(days 4-14)
                        "falling" if avg(last 3 days) < 0.8 * avg(days 4-14)
                        else "stable"
  ```
- Response payload must include: `forecast_per_day`, `forecast_7day`, `trend_flag`, `weights_used`, and the raw `last_14_days` series (for the Plotly chart) — never return just a bare number.
- If fewer than 5 days of history exist, return `insufficient_history: true` and fall back to a simple average, clearly labeled as low-confidence.

### Module 5 — Stock Truth / Reporting-Gap Engine (`stock_truth_engine.py`) — MUST / CORE NOVELTY
- Compute a **Stock Truth Score (0–100)** based on: recency of last report, completeness of the reporting window, and consistency between reported and expected stock trend.
- Flag **reporting gaps**: if a facility shows "0 usage" or "0 stock" but hasn't reported in N days, classify it as a **possible phantom stockout**, not a confirmed one.
- Output must include a plain-language reason string (e.g., "Last report 9 days ago, expected every 2 days — treat stock=0 as unverified").
- **Exact logic to implement** — three weighted sub-scores summing to a 0–100 total:
  ```
  recency_score (0-40):
      days_since_last_report = today - last_report_date
      expected_interval      = facility.reporting_interval_days   (e.g., 2)
      ratio                  = days_since_last_report / expected_interval
      recency_score = 40                         if ratio <= 1
                     = 40 * (2 - ratio)           if 1 < ratio < 2      (linear decay)
                     = 0                          if ratio >= 2

  completeness_score (0-30):
      expected_reports_in_window = window_days / expected_interval
      actual_reports_received    = count of non-missing reports in window
      completeness_score = 30 * (actual_reports_received / expected_reports_in_window), capped at 30

  consistency_score (0-30):
      expected_closing = opening_stock + received - (avg_daily_demand * days_elapsed)
      deviation_pct    = abs(reported_closing - expected_closing) / max(expected_closing, 1)
      consistency_score = 30                     if deviation_pct <= 0.1
                         = 30 * (1 - deviation_pct)  if 0.1 < deviation_pct < 1
                         = 0                      if deviation_pct >= 1

  stock_truth_score = recency_score + completeness_score + consistency_score   # 0-100
  TRUTH_THRESHOLD    = 50   # below this, treat any low-stock reading as unverified, not real
  ```
- Always return the three sub-scores separately (not just the total) so the Case Detail page can show the breakdown described in Section 7.

### Module 6 — Stockout Risk Engine (`stockout_risk_engine.py`) — MUST
- Combine days-of-stock-remaining, forecast trend, and Stock Truth Score into a single **risk level** (Low / Medium / High / Critical) with a **confidence score**.
- Low Stock Truth Score must cap the action to "verification required," even if days-remaining looks critical.
- **Exact logic to implement** — a risk matrix, not a single formula, so it stays explainable:
  ```
  if stock_truth_score < TRUTH_THRESHOLD:
      risk_level = "UNVERIFIED"          # never "Critical" on unverified data
      recommended_action = "verify_physical_stock"
      confidence = stock_truth_score / 100

  else:
      if days_remaining <= 2:            risk_level = "CRITICAL"
      elif days_remaining <= 5:          risk_level = "HIGH"
      elif days_remaining <= 10:         risk_level = "MEDIUM"
      else:                              risk_level = "LOW"

      if trend_flag == "rising":         bump risk_level up one level (min once)
      recommended_action = "consider_transfer" if risk_level in ("CRITICAL","HIGH") else "monitor"
      confidence = min(1.0, stock_truth_score/100 * (1 if data_points>=14 else data_points/14))
  ```
- `confidence` must always be returned alongside `risk_level` — a HIGH risk with 40% confidence must be visibly different in the UI from a HIGH risk with 95% confidence.

### Module 7 — Surplus + Expiry Engine (`surplus_engine.py`) — MUST
- Search nearby facilities (by distance) for **safe transferable surplus** — stock above their own safety threshold only.
- Separately identify **near-expiry usable stock** anywhere in the network that could be redirected to a high-demand facility instead of being wasted.
- **Exact logic to implement:**
  ```
  distance_km(fac_a, fac_b) = haversine(fac_a.lat, fac_a.lon, fac_b.lat, fac_b.lon)

  for each candidate donor facility with the same medicine:
      donor_surplus = donor.current_stock - donor.safety_stock
      eligible = donor_surplus > 0 and donor.stock_truth_score >= TRUTH_THRESHOLD
      # a donor with an untrustworthy report can never be used as a source — must verify first too

  near_expiry_candidates = [
      batch for batch in inventory_batches
      if batch.days_to_expiry <= NEAR_EXPIRY_WINDOW (default 45)
      and batch.facility.days_remaining_for_this_stock > batch.days_to_expiry  # i.e., will expire unused
  ]
  match near_expiry_candidates to any facility in MEDIUM/HIGH/CRITICAL risk for that medicine,
  ranked by (shortest days_to_expiry first, then shortest distance)
  ```
- A donor is only ever "eligible" if its own Stock Truth Score clears the threshold — an unverifiable donor cannot be used as a rescue source.

### Module 8 — Rescue Transfer Optimiser (`transfer_optimizer.py`) — MUST / WOW FEATURE
- Recommend: donor facility, recipient facility, quantity, reason, distance, and any warnings.
- **Fairness rule**: never draw a donor below its own protected safety stock, even if it's the closest option — must actively pick a farther-but-fair donor over a closer-but-unfair one, and explain why.
- **Counterfactual simulator**: accept an officer-submitted physical count via `POST /simulate-verification`; recompute Stock Truth Score, risk, and recommendation; if the new data removes the need for a transfer, **cancel it** and say why.
- **Exact logic to implement:**
  ```
  For each eligible donor (from Module 7):
      max_safe_transfer = donor.current_stock - donor.safety_stock
      quantity          = min(max_safe_transfer, recipient.avg_daily_demand * TARGET_COVER_DAYS (default 7))
      donor_score       = (quantity_available_weight * 0.4)
                         + (1/max(distance_km,1) * 0.4)
                         + (donor.stock_truth_score/100 * 0.2)
      # rank all eligible donors by donor_score DESC, pick the top one — NOT simply the nearest

  fairness_check:
      assert donor.current_stock - quantity >= donor.safety_stock   # hard constraint, never violated
      if the nearest donor fails this check, it must be skipped and the reason logged/returned
      (e.g., "PHC C is closer (3km) but transferring would drop it below its own safety stock;
       recommending PHC B (8km) instead, which stays safely above threshold.")

  recommendation payload = {donor, recipient, quantity, distance_km, reason, fairness_proof,
                             alternative_considered (if any donor was skipped for fairness), 
                             covers_days = quantity / recipient.avg_daily_demand}
  ```
- `POST /simulate-verification` must literally re-run Modules 3, 5, 6, 7, 8 in sequence with the corrected count and return a `before` / `after` diff object — this is what powers the counterfactual UI moment, so the backend must produce it directly, not the frontend.

### Module 9 — Root-Cause Engine (`root_cause_engine.py`) — ADVANCED
- Detect facilities with **repeated** stockout risk over time and label the likely cause: procurement delay, reorder-point too low, genuine demand growth, chronic reporting failure, or distribution/logistics problem.
- Expose via `GET /root-causes`.

### Module 10 — Dashboard + Feedback (frontend + `feedback` table) — MUST
- Rescue queue, case detail view, counterfactual simulator UI, officer approval/rejection, and feedback capture that loops back into Module 9.

---

## 5A. Data Models & Database Schema (build this before any engine logic)

**SQLite tables (`database.py`) — create with explicit DDL, not just ORM auto-generation:**

```sql
CREATE TABLE facilities (
    facility_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    facility_type TEXT CHECK(facility_type IN ('PHC','WAREHOUSE')),
    is_remote BOOLEAN DEFAULT 0,          -- protected from unfair transfers
    reporting_interval_days INTEGER DEFAULT 2
);

CREATE TABLE medicine_config (
    medicine_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    shelf_life_days INTEGER NOT NULL,
    safety_stock_days INTEGER DEFAULT 5,
    reorder_point_days INTEGER DEFAULT 10
);

CREATE TABLE inventory_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id TEXT REFERENCES facilities(facility_id),
    medicine_id TEXT REFERENCES medicine_config(medicine_id),
    record_date DATE NOT NULL,
    opening_stock REAL NOT NULL,
    received REAL DEFAULT 0,
    issued REAL DEFAULT 0,
    closing_stock REAL NOT NULL,
    batch_expiry_date DATE,
    is_reported BOOLEAN DEFAULT 1,        -- false = inferred/missing report
    UNIQUE(facility_id, medicine_id, record_date)
);

CREATE TABLE rescue_cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id TEXT, medicine_id TEXT,
    risk_level TEXT, confidence REAL, stock_truth_score REAL,
    recommended_action TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'OPEN'            -- OPEN / APPROVED / REJECTED / CANCELLED_BY_VERIFICATION
);

CREATE TABLE feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER REFERENCES rescue_cases(case_id),
    officer_decision TEXT CHECK(officer_decision IN ('APPROVED','REJECTED','VERIFIED')),
    notes TEXT, decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Pydantic models (`app/schemas.py`)** — define these and use them as the `response_model` on every FastAPI route, never return raw dicts:
`FacilityOut`, `MedicineOut`, `InventoryStatusOut` (stock, demand, days_remaining, safety_stock, status), `ForecastOut` (forecast_per_day, forecast_7day, trend_flag, weights_used, last_14_days), `StockTruthOut` (recency_score, completeness_score, consistency_score, total, reason), `RiskOut` (risk_level, confidence, recommended_action), `SurplusMatch`, `TransferRecommendation` (donor, recipient, quantity, distance_km, reason, fairness_proof, alternative_considered, covers_days), `SimulationDiff` (before, after), `RootCauseOut` (facility_id, medicine_id, pattern_label, evidence), `FeedbackIn`.

---

## 5B. Backend Error Handling & Edge Cases (must be explicitly handled, not left to crash)

Implement and unit-test each of these — they are exactly the situations a real health-data system hits:

- **Division by zero**: `avg_daily_demand == 0` in days-remaining and forecast calculations.
- **Missing/late reports**: facility hasn't reported in N days — must feed into the Stock Truth Score, not just be skipped.
- **Negative or impossible values**: negative stock, issued > opening+received on a given day, duplicate `(facility_id, medicine_id, date)` rows in an upload.
- **New facility/medicine with no history**: fewer than 5 days of data — forecast and risk must return `insufficient_history` rather than a misleadingly confident number.
- **No eligible donor found**: Module 7/8 must return `no_safe_donor_available` with the reason (e.g., "all nearby facilities are below their own safety stock") rather than an empty 200 response.
- **Conflicting concurrent uploads**: re-uploading a CSV for a date range that already exists — must upsert with a clear "N rows overwritten" response, never silently duplicate.
- **Verification contradicts an already-approved transfer**: if `POST /simulate-verification` is called after a case was already `APPROVED`, flag it for officer re-review rather than silently cancelling something already in motion.
- **Malformed CSV**: wrong columns, wrong types, extra columns — the validator (Module 2) must return row-level errors, never a raw stack trace.

---

## 5C. Backend Testing Requirements

- Write `pytest` unit tests per engine under `backend/tests/`, each with small hand-crafted fixtures (not the full synthetic dataset) so expected outputs can be calculated by hand and asserted exactly:
  - `test_inventory_engine.py` — normal case, zero-demand case, negative-stock rejection.
  - `test_forecast_engine.py` — known input series → known weighted output, insufficient-history fallback.
  - `test_stock_truth_engine.py` — high-truth case, stale-report case, inconsistent-closing-stock case.
  - `test_stockout_risk_engine.py` — verifies UNVERIFIED overrides CRITICAL when truth score is low.
  - `test_surplus_engine.py` — donor correctly excluded when its own truth score is low.
  - `test_transfer_optimizer.py` — fairness constraint is never violated; farther-but-fair donor chosen over closer-but-unfair one.
  - `test_root_cause_engine.py` — repeated risk correctly labeled by pattern.
- Write one **integration test** that runs the full pipeline (Section 4) end-to-end on the generated demo data and asserts that the seeded hidden cases (Section 5, Module 1) are each correctly surfaced with the right recommended action.
- All engine tests must be runnable and passing with the backend server **not running** — pure Python function calls only.

---

## 6. Full API Plan

| Method & Endpoint | Purpose |
|---|---|
| `GET /health` | Check backend is running |
| `POST /generate-demo-data` | Generate/load fictional PHC + medicine datasets (Module 1) |
| `POST /upload-inventory` | Upload and validate inventory CSV (Module 2) |
| `GET /dashboard-summary` | Aggregate counts for the dashboard header |
| `GET /facilities` | List all facilities |
| `GET /facilities/{facility_id}` | Facility summary |
| `GET /facilities/{facility_id}/medicines/{medicine_id}` | Stock, demand, forecast, truth score, trend data |
| `GET /rescue-queue` | Ranked list of stockout-risk cases |
| `GET /rescue-cases/{case_id}` | Full evidence + recommended action for one case |
| `POST /recommend-transfer` | Donor–recipient transfer recommendation (Module 8) |
| `POST /simulate-verification` | Recalculate after physical-count/report verification (counterfactual) |
| `POST /feedback` | Store officer's decision (approve/reject/verify) |
| `GET /root-causes` | Chronic risk explanations (Module 9) |

Every endpoint returning a risk, score, or recommendation must include a `reasoning` field in plain language, not just a number.

---

## 7. Frontend — Page-by-Page Flow

Build these as React pages under `src/pages/`, each wired to its API calls via `src/services/api.js`.

1. **Landing / Load Data Page**
   - "Load Demo Data" button → `POST /generate-demo-data`; or drag-and-drop CSV upload → `POST /upload-inventory`.
   - Shows the validator report (errors/warnings) before letting the user proceed.

2. **Dashboard (Home)**
   - Calls `GET /dashboard-summary`.
   - KPI cards: facilities at risk, possible-vs-verified stockouts, active rescue recommendations, near-expiry surplus available.
   - Prominent **"Officer approval required"** banner, always visible.

3. **Rescue Queue Page**
   - Calls `GET /rescue-queue`.
   - Table/cards ranked by risk, each showing: facility, medicine, days remaining, risk level, Stock Truth Score badge (color-coded), and a one-line reasoning snippet.
   - Clicking a row opens the Case Detail page.

4. **Case Detail Page**
   - Calls `GET /rescue-cases/{case_id}`.
   - Shows: forecast chart (Plotly), Stock Truth Score breakdown (recency/completeness/consistency), risk + confidence, and the recommended action.
   - If Stock Truth Score is low → shows "Verification required" state instead of a transfer button.
   - "Verify Physical Count" button → opens the Counterfactual Simulator.

5. **Transfer Recommendation Panel** (part of Case Detail, or its own page)
   - Calls `POST /recommend-transfer`.
   - Shows donor, recipient, quantity, distance, reason, and the **fairness proof** (donor's remaining stock stays above its safety threshold).
   - "Approve" / "Reject" buttons → `POST /feedback`.

6. **Counterfactual Simulator Modal/Page**
   - Officer enters a new physical count → `POST /simulate-verification`.
   - Shows before/after: Stock Truth Score, risk level, and whether the transfer was cancelled or confirmed — this is the core "wow" demo moment.

7. **Facility Detail Page**
   - Calls `GET /facilities/{facility_id}` and the medicine-level endpoint.
   - Per-medicine table: stock, demand, forecast, Stock Truth Score, days remaining, status.
   - Distinguishes real facilities' safety-stock line on every chart.

8. **Surplus & Expiry Explorer Page**
   - Visual map or list of facilities with safe surplus and near-expiry stock (Module 7), so officers can proactively spot redistribution opportunities, not just reactive alerts.

9. **Root-Cause Page**
   - Calls `GET /root-causes`.
   - Lists facilities with repeat risk and their likely labeled cause (procurement / reorder-point / demand / reporting / distribution).

10. **Feedback / History Page**
    - Log of past officer decisions, outcomes, and whether a counterfactual later proved the original alert right or wrong — this closes the loop and builds trust in the system over time.

---

## 8. Novelty Features Checklist (must be visibly demonstrable in the UI, not just in the backend)

- [ ] **Stock Truth Score** shown as a distinct, color-coded badge everywhere stock is displayed.
- [ ] **Reporting-gap detector** visibly changes the recommended action to "verify" instead of "transfer."
- [ ] **Rescue optimiser** explains donor choice, including cases where it picks a farther-but-fair donor.
- [ ] **Expiry-to-need matching** surfaced as its own explorer, not buried in a table.
- [ ] **Fairness rule** proof text/graphic on every transfer recommendation.
- [ ] **Counterfactual simulator** with a clear before/after showing a cancelled transfer.
- [ ] **Chronic-risk root-cause labeling**, distinct from "just a bad forecast."

---

## 9. Build Order (build in this sequence; do not build later-phase items early)

| Phase | Build | Do NOT build yet |
|---|---|---|
| 1 — Foundation | `/health`, demo data generator, inventory status engine, `/dashboard-summary` | Frontend, login, maps, chatbot |
| 2 — Core novelty | Forecast engine, Stock Truth Score, reporting-gap detection, stockout risk engine | Complex ML/deep learning |
| 3 — Rescue action | Surplus engine, expiry matching, transfer optimiser, counterfactual simulator | Automatic (non-approved) transfers |
| 4 — Frontend | All 10 pages in Section 7, wired to the API | Mobile app, payments, chatbots |
| 5 — Polish | Root-cause page, presentation copy, tests, backup demo recording | New features not in the demo script |

---

## 10. Acceptance / Demo Checklist

- [ ] One synthetic dataset containing at least 3 strong hidden-case stories (real stockout, phantom stockout, chronic risk).
- [ ] Backend fully browsable and testable via FastAPI Swagger docs (`/docs`).
- [ ] Working dashboard with a functioning rescue queue.
- [ ] Stock Truth Score visibly displayed on every relevant view.
- [ ] At least one transfer recommendation shown with its donor-safety fairness proof.
- [ ] At least one counterfactual simulation that changes a recommendation live in the UI.
- [ ] "Officer approval required" disclaimer visible on every action-taking screen.
- [ ] No claims of medical diagnosis, automatic transfer, or real-world accuracy/impact anywhere in the UI or copy.
- [ ] **Every engine passes its `pytest` suite (Section 5C) independently of the frontend and the running server.**
- [ ] **Every FastAPI route uses a typed `response_model` (Section 5A)** — no raw dicts returned from any endpoint.
- [ ] **All edge cases in Section 5B are handled with typed errors, not stack traces**, verified by hitting each one manually via `/docs`.
- [ ] The React app contains zero scoring/risk/forecast math — confirm by grepping the frontend for any arithmetic on stock/demand values; there should be none.

---

## 11. Final Instruction to the Agent

Build MedTrace exactly as specified above, phase by phase, inside the `medtrace/` project structure in Section 3. **Treat Sections 5, 5A, 5B, and 5C as the real spec — get the backend engines, schemas, edge cases, and tests fully correct and independently verifiable via `/docs` and `pytest` before spending significant time on frontend styling.** The frontend in Section 7 only needs to be clean and functional enough to demonstrate the backend correctly; it is not the deliverable. After completing each phase, report: files changed, exact terminal commands to run and test the result, tests performed (paste actual pytest output), and known limitations. Do not skip the Stock Truth Score, the fairness rule, or the counterfactual simulator — these three are the product's core differentiators, and their correctness must be provable in the backend test suite, then simply displayed by the UI, never computed there.
