# Zero-Downtime Data Center Cooling & PUE/WUE Tracker: "The Change-Request Factory"

An enterprise-grade, agentic data-change factory engineered to solve data drift, schema vulnerability, and validation latency challenges in modern AI data centers. 

By unifying **Bright Data external web scraping**, **high-frequency IoT telemetry**, **dynamic electric grid pricing**, and **zero-downtime Blue/Green SQL views**, this platform enables operations and sustainability teams to monitor cooling hardware efficiency, simulate fleet expansions, enforce strict engineering contracts, and isolate malformed payloads without production downtime.

---

## 🏗️ System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Ingestion_Layer["1. Ingestion & Scrape Layer"]
        A1["🌐 External Vendor Sites (Submer, CoolIT, Vertiv, RefJet)"] -->|Bright Data Scraping Browser| CR_A["Change Request A (CR-A)"]
        A2["⚡ Electric Grid Pricing (CAISO, PJM, ERCOT)"] -->|Live Tariff Sync| DB_Tariffs[("DuckDB: grid_energy_tariffs")]
        A3["📡 HVAC IoT Sensor Telemetry"] -->|Streaming Ingest| DB_IoT[("DuckDB: hvac_iot_telemetry")]
        A4["👨‍💼 Data Center Operator (What-If Simulation)"] -->|User Submission| CR_B["Change Request B (CR-B)"]
    end

    subgraph Defense_Gate["2. Strict Data Contract Enforcement Gate"]
        CR_A --> Gate{"verify_change_request()"}
        CR_B --> Gate
        Gate -->|❌ Violated: Out of Bounds / Type Error| DB_Quarantine[("🛡️ DuckDB: quarantine
(Isolated Audit Box)")]
        Gate -->|✅ Verified: Physical & Financial Bounds| DB_CR[("DuckDB: change_requests
(Pending Port Approval)")]
    end

    subgraph Governance_Layer["3. Port Governance & Atomic Hot-Swap"]
        DB_CR --> PortApprove["🛡️ Port Human Approval Action
(execute_approval)"]
        PortApprove --> AtomicSwap["⚡ DuckDB Atomic View Hot-Swap"]
        AtomicSwap --> View_Market[("SQL View: v_market_active")]
        AtomicSwap --> View_Fleet[("SQL View: v_fleet_active")]
    end

    subgraph Analytics_Presentation["4. Real-Time Analytics & Observability Layer"]
        View_Market --> Tab1["📊 Tab 1: Market View (Plotly Scatter & Green Zone)"]
        View_Fleet --> Tab2["🏭 Tab 2: Fleet View (Blended PUE/WUE & ROI)"]
        DB_IoT & DB_Tariffs --> Tab3["⚡ Tab 3: HVAC IoT Anomaly Mart (PF Penalty)"]
        DB_Quarantine --> Tab5["🛡️ Tab 5: Audit Trail & Quarantine Ledger"]
        PortApprove -.->|Trace Spans| SigNoz["📈 SigNoz / OpenTelemetry Distributed Tracing"]
    end
```


---

## 🎯 What Problems Does This Factory Solve?

1. **Unreliable External Data Drift**: Vendor cooling specifications change frequently across public marketing pages and datasheets. Traditional ETL pipelines often crash when encountering layout updates or corrupted values.
2. **Zero Production Downtime Requirement**: Mission-critical sustainability dashboards cannot restart or display `NULL`/error states when data is updated.
3. **Data Quality & Physical Plausibility**: Scraping errors (e.g., negative power, PUE < 1.0, capacity smaller than load) must be automatically blocked before reaching executive metrics.
4. **Energy Inefficiency & Dynamic Tariffs**: Legacy HVAC chillers running with poor power factors (PF < 0.85) waste massive amounts of power, which must be converted into financial impact based on real-time grid rates.

---

## 📐 Engineering Data Contract Standards

> ⚠️ **IMPORTANT ADAPTABILITY NOTE:**
> The numerical ranges specified below are configured strictly for **demonstration and prototype verification** purposes within liquid-cooled and standard AI cluster environments.
> **These bounds do not fit all real-world operational conditions.** In enterprise or multi-megawatt hyperscale deployments, cooling capacity, power loads, and procurement costs can be significantly higher or lower depending on facility tier and climate. **Always search, benchmark, and configure your organization-specific acceptable thresholds in `engine.py` prior to production deployment.**

| Parameter | Demonstration Bounds | Operational / Engineering Rationale |
| --- | --- | --- |
| **PUE (Power Usage Effectiveness)** | **1.05 ~ 1.80** | Demonstrates boundary limits for modern DLC/Immersion units vs. legacy baseline chillers. |
| **WUE (Water Usage Effectiveness)** | **0.00 ~ 1.50 L/kWh** | Demonstrates air/closed-loop systems (0.00) vs. evaporative cooling towers. |
| **Cooling Load (kW)** | **30.0 ~ 500.0 kW** | Demonstration load envelope per unit/pod. |
| **Cooling Capacity (kW)** | **50.0 ~ 1000.0 kW** | Enforces physical consistency: unit capacity must be >= load. |
| **Hardware Price (USD)** | **$30,000 ~ $80,000** | Demonstration commercial equipment price envelope. |

---

## 📑 Detailed Tab-by-Tab Breakdown

### 📊 Tab 1: Market Intelligence View

* **Plotly Efficiency Frontier**: Displays an interactive scatter plot with **PUE** (X-axis), **WUE** (Y-axis), **Capacity** (Bubble Size), and **Price** (Color Scale).
* **Green Zone Highlighting**: Outlines the ultra-efficient liquid cooling zone (PUE <= 1.20, WUE <= 0.10).
* **Direct CR-B Dispatch**: Select any approved market vendor equipment and submit it directly to the What-If Simulator with a single click.
* **Roster Management**: Remove obsolete or decommissioned market units directly from DuckDB.

### 🏭 Tab 2: Fleet Intelligence & Cost/Carbon ROI Simulator

* **Current Baseline Metrics**: Displays live Blended PUE, Blended WUE, Total Thermal Load (kW), and Total Cooling Capacity (kW).
* **What-If Impact Modeling**: Calculates the mathematical impact of adding new equipment:

$$\text{Blended PUE}_{\text{new}} = \frac{\sum (\text{PUE}_i \times \text{Load}_i) + (\text{PUE}_{\text{sim}} \times \text{Load}_{\text{sim}})}{\text{Total Load}_{\text{new}}}$$


* **Environmental & Financial ROI**:
* **Annual Energy Saved (kWh/yr)**: Computed against baseline IT load across 8,760 annual operating hours.
* **OPEX Cost Savings ($/yr)**: Multiplied by current utility electricity rates.
* **Carbon Abatement (tons CO2/yr)**: Calculated using regional grid carbon intensity factors.


* **Port Direct Sign-Off**: Directly approve simulated units into the permanent baseline fleet.

### ⚡ Tab 3: HVAC IoT Energy Anomaly Analytics Mart

* **Live Grid Tariffs**: Displays real-time dynamic pricing from California CAISO, Virginia PJM, and Texas ERCOT.
* **Low Power Factor Penalty Table**: Identifies chillers running with PF < 0.85 and calculates annual financial loss:

$$\text{Annual Penalty USD} = (0.95 - \text{PF}) \times \text{Active Power (kW)} \times \text{Tariff (\$/kWh)} \times 8760$$


* **High-Frequency Ingestion**: Simulate live telemetry ingestion with power factor and load sliders, including full log deletion capabilities.

### 🎛️ Tab 4: Live Variable Drift & Bad Data Simulator (Demo Engine)

* **Grid Tariff Drift**: Inject spikes into electric tariffs to demonstrate instant recalculation across the IoT Mart.
* **Bad Data Injection Workbench**: Test 5 critical failure modes (PUE > 1.80, PUE < 1.05, Price > $80k, Capacity < Load, Negative WUE) to prove automated quarantine isolation and dashboard immunity.

### 🛡️ Tab 5: Factory Audit Trail & Quarantine Log

* **Change Request Ledger**: Comprehensive history of all CR-A and CR-B submissions, timestamps, verification statuses, and reviewer IDs.
* **Quarantine Box**: Dedicated isolation log showing full raw payloads and exact contract rejection reasons for all failed attempts.

### 🌐 Tab 6: Vendor Web Ingest (CR-A)

* **Automated Scraper**: Input any public vendor specification URL and product name to trigger Bright Data Scraping Browser extraction.
* **Port Human Gate**: Review parsed specs and approve them with one click to trigger DuckDB zero-downtime view swapping.

### ⚙️ Tab 7: Baseline Entry

* **Manual Setup**: Input initial baseline facility chillers (Chiller Alpha, cooling towers) with custom capacity, PUE, and load.

---

## 🛠️ Technology Stack

* **Ingestion & Browser Automation**: Bright Data Scraping Browser & Web Unlocker API
* **Embedded Analytics Engine**: DuckDB (Atomic Blue/Green SQL Views & In-Memory Hot-Swapping)
* **Frontend Application**: Streamlit (Python) with `streamlit-autorefresh`
* **Data Visualization**: Plotly Express & Plotly Graph Objects
* **Governance & Orchestration**: Port Blueprint Model & Action API
* **Distributed Observability**: OpenTelemetry SDK & SigNoz

---

## 🚀 Step-by-Step Execution Guide

### 1. Prerequisites & Virtual Environment

```bash
# Clone the repository and navigate into the folder
cd files

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required dependencies
pip install streamlit duckdb pandas requests opentelemetry-api opentelemetry-sdk playwright plotly streamlit-autorefresh

```

### 2. Configure Environment Variables

```bash
export BRIGHTDATA_SBR_WS_ENDPOINT="wss://brd-customer-xxxx-zone-xxxx:password@brd.superproxy.io:9222"

```

### 3. Reset Database to Clean Benchmark State

```bash
python -c '
import duckdb
con = duckdb.connect("datacenter.duckdb")
con.execute("DELETE FROM change_requests; DELETE FROM quarantine; DELETE FROM hvac_iot_telemetry; DELETE FROM vendor_equipment_raw; DELETE FROM baseline_equipment;")
con.execute("INSERT INTO baseline_equipment VALUES (\x27chiller_alpha\x27, \x27Chiller Alpha\x27, 1.45, 0.85, 65000.0, 300.0, 700.0);")
con.execute("INSERT INTO vendor_equipment_raw VALUES (\x27submer_smartpodx\x27, \x27Submer SmartPodX\x27, 1.08, 0.01, 52000.0, 120.0, 900.0, CURRENT_TIMESTAMP), (\x27coolit_dlc_server_module\x27, \x27CoolIT DLC Server Module\x27, 1.12, 0.02, 32000.0, 80.0, 850.0, CURRENT_TIMESTAMP);")
con.execute("INSERT OR REPLACE INTO grid_energy_tariffs VALUES (\x27us-west-ca\x27, \x27California CAISO Grid\x27, 0.245, 18.5, 0.28, CURRENT_TIMESTAMP), (\x27us-east-va\x27, \x27Virginia PJM Grid\x27, 0.118, 12.0, 0.42, CURRENT_TIMESTAMP), (\x27us-central-tx\x27, \x27Texas ERCOT Grid\x27, 0.135, 15.0, 0.45, CURRENT_TIMESTAMP);")
con.close()
print("✅ Benchmark clean state initialized!")
'

```

### 4. Launch Services

#### Launch Streamlit Dashboard (Production Core)

```bash
python -m streamlit run app.py

```

#### Launch Background Live Drift & Defense Engine (DEMO ONLY)

> ⚠️ **PRODUCTION NOTICE:**
> `drift_daemon.py` is a mock simulation ticker used exclusively for live hackathon demonstrations to simulate dynamic grid pricing and periodic bad-data ingestion.
> **Do not run `drift_daemon.py` in a production deployment.** In production, data changes are driven solely by scheduled Bright Data scraping runs and live IoT ingestion webhooks.

```bash
# Demo Only
python drift_daemon.py

```

```
