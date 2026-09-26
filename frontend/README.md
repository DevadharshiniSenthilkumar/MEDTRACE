# MedTrace frontend

React + Vite + TypeScript frontend for the MedTrace stockout decision-support
dashboard. Built to consume your FastAPI backend at `http://127.0.0.1:8000`
(configurable) — no mock data, every page calls a real endpoint.

## Install & run

```bash
# copy src/, index.html, package.json, vite.config.ts, tsconfig*.json,
# and .env.example into your project (or drop this whole folder in as
# frontend/), then:
npm install
cp .env.example .env.local   # adjust VITE_API_BASE_URL if needed
npm run dev
```

Start your FastAPI backend first (or in parallel) — the Landing page
needs `/generate-demo-data` or `/upload-inventory` to succeed before
there's anything to show on the dashboard.

## File tree

```
src/
  services/api.ts        one function per backend endpoint
  types/api.ts            shared response/request interfaces
  hooks/useApi.ts         loading/error/data fetch hook used by every page
  components/             Sidebar, TiltCard, RiskPill, VialBar,
                           TruthScoreBadge, ApprovalBanner, KpiCard,
                           StateViews, icons
  pages/                  the 10 routed pages
  styles/                 tokens.css, global.css, components.css, pages.css
```

## Reconcile these two things with your backend before demoing

1. **Field names in `src/types/api.ts`.** I didn't have your Pydantic
   response models, so these interfaces are inferred from the field
   names your brief mentioned (`stock_truth_score`, `days_remaining`,
   `donor_safety_threshold`, etc). If your actual JSON uses different
   keys, this is the one file to edit — every page reads through these
   types, so a rename here is a rename everywhere.

2. **Two endpoints your list didn't include.** Page 8 (Surplus & Expiry
   Explorer) and Page 10 (History) need data, but `GET /surplus` and
   `GET /history` weren't in your endpoint list. I wired them to those
   paths as a best guess — if your backend serves this data from
   `/dashboard-summary`, `/facilities`, or a different path entirely,
   update `getSurplus()` and `getHistory()` in `src/services/api.ts`.
   Both currently fail soft (empty list + empty-state UI) rather than
   erroring, so nothing breaks if the path is wrong — it just shows
   "no data yet" until you point it at the right place.

## On the "zero business logic" rule

Every number shown (stock, demand, forecast, truth score, risk level,
days remaining) comes straight from an API response — nothing is
derived from another. Two categories of arithmetic do exist in the
code, both presentational rather than business logic, so a plain grep
for `+`/`*`/`/` will surface them:

- `value / max * 100` in `VialBar.tsx` and the truth-score bars — turns
  an already-computed number into a CSS bar width. It doesn't produce
  a number that's displayed as text.
- `Math.round(...)` on truth scores and confidence — display rounding
  of a value the backend already computed, not a recomputation of it.

If you want these stricter still (e.g. bars sized only in fixed
buckets the backend returns), say so and I'll adjust.

## Design notes

Glassmorphism (frosted panels) layered on neumorphic base cards, with
pointer-based 3D tilt via Framer Motion (`TiltCard`, disabled on cards
tagged `flat` — tables and text-heavy panels — and whenever
`prefers-reduced-motion` is set). Pill/vial/blister shapes are used
literally: risk badges are pill-capsule shaped, stock levels render as
vial fills with a visible safety-threshold line. Risk colors are fixed
everywhere: CRITICAL red, HIGH amber, MEDIUM yellow, LOW/OK green.

Safety wording ("possible stockout," "verification required," "officer
approval required") is baked into `ApprovalBanner` and the copy on the
Case Detail and Transfer pages, not left to be added per page.
