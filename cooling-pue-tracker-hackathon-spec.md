# Project: Zero-Downtime Data Center Cooling & PUE/WUE Tracker
### "The Change-Request Factory"

## 0. The Core Reframe: One Factory, Two Change-Request Types

The hackathon brief asks for a factory that can "take a **product brief or change request**, assemble the right context, coordinate agents and tools, produce working software, **verify the result**, and keep humans in control where it matters."

This project runs exactly one factory pipeline, fed by two different triggers:

- **Change Request A — System-generated:** Bright Data Scraper Studio detects a vendor page's HTML structure changed, auto-repairs the scraper, and submits the repaired data as a change request.
- **Change Request B — User-generated:** An operator clicks "Simulate Adding This Equipment" in the app. This is itself a product brief: *"what happens to our data center if we add unit X?"*

Both requests go through the **same** three gates: context assembly → verification (data contract test) → human approval in Port. Only after approval does either request get to change something a user sees. This is the piece the previous drafts were missing — without it, the project is a monitored pipeline, not a factory that verifies and controls what it produces.

---

## 1. Project Context & Objectives

**Goal:** A factory that keeps a data center cooling-hardware intelligence product alive and trustworthy as both the outside world (vendor websites) and the inside world (your own equipment roster) change.

**Two dashboards, one factory:**
- **Dashboard 1 — Market View:** vendor equipment comparison (PUE, WUE, price, load, capacity), sourced by Bright Data Scraper Studio.
- **Dashboard 2 — Fleet View:** your current data center's baseline equipment (entered manually — this data lives nowhere on the public web) plus a live "what-if" simulation of adding a new unit, showing the resulting delta in blended PUE/WUE, remaining capacity, and load.

**Problem Statement:** Vendor spec pages change without notice, and internal fleet changes need the same rigor: nothing should update a live dashboard without being verified and approved.

---

## 2. Judging Alignment (self-check before building)

| Prize | What judges look for | How this project delivers it |
|---|---|---|
| 🏆 Grand Prize (all 3 tools) | Seamless combination of Port, Bright Data Scraper Studio, SigNoz | One Port workflow, fed by Bright Data (Change Request A) and the app itself (Change Request B), fully traced in SigNoz |
| Best Port Integration | Clear workspace: goals, technical choices, risk factors, cataloged services | Blueprints for `Equipment` and `ChangeRequest`, a single `change-request-review` workflow, one Approval Action |
| Best Bright Data Integration | Terminal workflow, scraper rules file, working auto-repair | Scraper Studio invoked from terminal; config in `CLAUDE.md`; live repair demo feeds Change Request A |
| Best SigNoz Integration | Active tracing, log collection, metrics across endpoints/jobs | Critical path instrumented: scrape → drift detect → repair → **verify** → approve, for both request types |

**"Verify the result" — the piece most projects skip:** every change request, regardless of type, runs a data-contract test before it can reach a human for approval:
- Type checks (numeric fields are actually numeric)
- Range checks (PUE plausible ~1.0–3.0, WUE plausible ≥0, non-negative capacity/load)
- For Type B specifically: the *computed* blended PUE/WUE after adding equipment must itself stay within plausible bounds — this catches bad arithmetic, not just bad scraped data.

A request that fails verification is auto-rejected and logged; it never reaches the human approval queue. This is the "produce working software, verify the result" loop made concrete.

---

## 3. Tech Stack

- **Data Extraction:** Bright Data Scraper Studio (terminal-invoked)
- **Orchestration & Governance:** Port (Context Lake, one Workflow, one Approval Action)
- **Observability:** SigNoz + OpenTelemetry SDK, critical path only
- **Data Processing:** Python (pandas, json, requests, opentelemetry-api)
- **Data Warehouse:** DuckDB
- **Presentation Layer:** Streamlit — two pages, Dashboard 1 and Dashboard 2

---

## 4. Data Model (DuckDB)

- `baseline_equipment` — manually entered current fleet: `equipment_id, name, pue, wue, price, load_kw, capacity_kw`
- `vendor_equipment_raw` — scraped vendor specs (Bright Data output)
- `quarantine` — malformed scraped records
- `change_requests` — `id, type (A|B), payload, verification_result, status (pending/approved/rejected), reviewed_by, timestamp`
- `v_market_active` — Blue/Green served view for Dashboard 1
- `v_fleet_active` — Blue/Green served view for Dashboard 2 (current fleet + any approved additions)

---

## 5. Architecture & Implementation Steps

### Step 1 — Baseline Input (manual, 10–15 min)
Operator enters current fleet equipment directly into `baseline_equipment` (a simple Streamlit form is enough — this is intentionally not automated, since this data isn't public).

### Step 2 — Terminal-Native Extraction (Bright Data Scraper Studio)
Scrape 2 vendor spec pages (trim from 3 to 2 to fit 5 hours). Save scraper config in `CLAUDE.md`. Break one target page's structure on purpose to trigger auto-repair live.

### Step 3 — Ingestion + Quarantine (Python)
Parse scraped JSON. Missing/malformed fields → `quarantine`, never crash. A successful scrape (fresh data or a repaired scraper's output) creates a **Change Request A**.

### Step 4 — Verification (shared by both request types)
A single `verify_change_request()` function: type checks + range checks as described in Section 2. Runs before anything reaches Port's approval queue.

### Step 5 — Port: One Workflow, Two Entry Points
- Blueprints: `Equipment`, `ChangeRequest`.
- Workflow `change-request-review`: triggered either by a Bright Data repair/drift event (Type A) or a direct call from the Streamlit "Simulate Addition" button (Type B).
- On verification pass → open Approval Action for a human.
- On approval:
  - Type A → `ALTER TABLE` (Expand) on `vendor_equipment_raw`, then atomic swap of `v_market_active`.
  - Type B → insert the new equipment into `baseline_equipment`, then atomic swap of `v_fleet_active`.
- On verification fail → auto-reject, logged in `change_requests`, never reaches a human.

### Step 6 — Observability (SigNoz)
Instrument the critical path only: scrape → drift detect → repair → verify → approve/reject. Dashboard: latency, throughput, error rate, plus drift/repair/verification-failure counts as first-class metrics. One alert (repeated scrape failure) wired back into the Port workflow.

### Step 7 — The App (Streamlit)
- **Dashboard 1 (Market View):** vendor comparison table/chart from `v_market_active`.
- **Dashboard 2 (Fleet View):** current fleet from `v_fleet_active`, a picker to select a scraped vendor unit, a "Simulate Addition" button that fires Change Request B, and — after approval — the updated blended PUE/WUE/capacity/load shown as a before/after delta.

---

## 6. Demo Script (3–5 min video)

1. Terminal: Bright Data Scraper Studio run, show `CLAUDE.md` config.
2. Break a target page → show auto-repair → Change Request A appears in Port.
3. Dashboard 2: pick a new unit, click "Simulate Addition" → Change Request B appears in Port.
4. Show both requests passing verification, one human approval click each.
5. SigNoz dashboard: show the traced run for both request types side by side.
6. Both dashboards update live, zero downtime on the served views.

---

## 7. Submission Checklist

- [ ] GitHub repo, commit history, README describing the factory (not just the app)
- [ ] Demo video: terminal, Port workflow (both request types), live SigNoz, Bright Data auto-repair
- [ ] `CLAUDE.md` with scraper config committed
- [ ] Port workspace: blueprints, one workflow, one approval action
- [ ] SigNoz dashboard: critical-path latency/throughput/errors + drift/repair/verification-failure events

---

## 8. Time-Boxed Build Plan (5 hours)

| Time | Focus |
|---|---|
| 0:00–0:30 | Port MCP connection confirmed, SigNoz sample instrumented, DuckDB schema created, baseline equipment entered |
| 0:30–1:30 | Bright Data Scraper Studio terminal flow (2 vendors) + rules file + ingestion + quarantine table |
| 1:30–2:30 | Port blueprints + single `change-request-review` workflow + approval action; wire Change Request A (scrape/drift) |
| 2:30–3:30 | `verify_change_request()` shared verification function + Dashboard 2 "Simulate Addition" → Change Request B wired into same workflow |
| 3:30–4:30 | SigNoz instrumentation across critical path + dashboard + one alert back into Port |
| 4:30–5:00 | Streamlit polish (both dashboards), break something on purpose, dry-run the demo script |
| *(post-build, per agenda)* | Record demo video, finish README, submit |

---

## 9. Coding Guidelines for the Agent

- No change — of either type — reaches a served view without passing verification *and* human approval.
- Never fail hard: quarantine bad scrapes, auto-reject failed verifications, always leave a log trail.
- Every step on the critical path must be traced (SigNoz) — no silent steps.
- Keep Streamlit UI code decoupled from ingestion/orchestration logic; it only reads from `v_market_active` / `v_fleet_active`.
