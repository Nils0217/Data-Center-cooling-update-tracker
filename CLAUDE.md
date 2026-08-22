# Project Rules & Scraper Configurations

## 1. Bright Data Scraper Studio Targets
- **Target Mode:** Dynamic / Manual user ingestion supported.
- **Default Targets:**
  - `https://submer.com/smartpodx-spec`
  - `https://coolit.com/dlc-server-spec`
- **Manual Input:** Operators can supply custom vendor URLs and spec payloads via Tab 4 of the Streamlit UI or pass JSON directly via `scrape_ingest.py '<json_string>'`.

## 2. Auto-Repair & Drift Protocol
- If vendor HTML changes, invoke Scraper Studio Auto-Repair to recalculate selectors[cite: 1, 2].
- Output repaired data into `scrape_ingest.py` as Change Request A[cite: 1, 2].

## 3. Data Contract Verification Policies
- PUE range: `1.0 <= PUE <= 3.0`[cite: 1, 2]
- WUE range: `WUE >= 0.0`[cite: 1, 2]
- Capacity & Load: strictly non-negative floats[cite: 1, 2]
- Auto-quarantine any record with missing mandatory keys (`name`, `pue`, `wue`, `load_kw`, `capacity_kw`, `price`)[cite: 1, 2].

## 4. Serving View Policy
- No data is written directly to `v_market_active` or `v_fleet_active` without Port Human Approval[cite: 1, 2].
