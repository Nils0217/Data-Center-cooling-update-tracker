import streamlit as st
import duckdb
import time
import json
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from engine import submit_change_request, tracer

st.set_page_config(
    page_title="Cooling & PUE Factory",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

count = st_autorefresh(interval=10000, limit=None, key="live_drift_ticker")

st.markdown("""
<style>
    @media (max-width: 768px) {
        .stMetric { padding: 10px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] { font-size: 0.85rem; padding: 6px 8px; }
    }
</style>
""", unsafe_allow_html=True)

def get_db():
    return duckdb.connect("datacenter.duckdb")

def execute_approval(cr_id: str, approver: str = "Operator (UI)"):
    with get_db() as con:
        with tracer.start_as_current_span("port_approval_action"):
            row = con.execute("SELECT type, payload, status FROM change_requests WHERE id = ?", (cr_id,)).fetchone()
            if not row:
                return False, "Change Request not found."
            
            cr_type, payload_str, status = row
            if status != "pending_approval":
                return False, f"Request is already {status}."

            payload = json.loads(payload_str)
            eq_id = payload["name"].lower().replace(" ", "_")

            if cr_type == "A":
                con.execute("""
                    INSERT OR REPLACE INTO vendor_equipment_raw 
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (eq_id, payload["name"], payload["pue"], payload["wue"], payload["price"], payload["load_kw"], payload["capacity_kw"]))

            elif cr_type == "B":
                con.execute("""
                    INSERT OR REPLACE INTO baseline_equipment 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (eq_id, payload["name"], payload["pue"], payload["wue"], payload["price"], payload["load_kw"], payload["capacity_kw"]))

            con.execute(
                "UPDATE change_requests SET status = 'approved', reviewed_by = ? WHERE id = ?",
                (approver, cr_id)
            )
            return True, f"Approved {payload['name']} successfully!"

tabs = st.tabs([
    "📊 Market View (Live 10s)", 
    "🏭 Fleet & ROI Simulator", 
    "⚡ HVAC IoT Mart (Live 10s)",
    "🎛️ Live Drift & Bad Data Simulator",
    "🛡️ Audit & Quarantine Log",
    "🌐 Vendor Scraper (CR-A)",
    "⚙️ Baseline Entry"
])

# ----------------- Tab 1: Market View -----------------
with tabs[0]:
    with get_db() as con:
        market_df = con.execute("SELECT * FROM v_market_active").df()
        recent_bad = con.execute("""
            SELECT raw_payload, reason, created_at 
            FROM quarantine 
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL 30 SECOND 
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()

    # 若最近 30 秒內有抓到壞資料，在頂部顯示防禦告警橫幅
    if recent_bad:
        bad_payload, reason, ts = recent_bad
        st.warning(
            f"🛡️ **Data Contract Defense Activated**: External scraper captured corrupted payload at {ts}. "
            f"Blocked by rule: `{reason}`. **Showing Last-Known Good Norms below (Zero Downtime Maintained).**"
        )

    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.subheader("Market Intelligence & PUE vs. WUE Tradeoff")
    with col_t2:
        st.caption(f"🟢 **Live Streaming** (Cycle: #{count})")

    if not market_df.empty:
        fig = px.scatter(
            market_df,
            x="pue",
            y="wue",
            size="capacity_kw",
            color="price",
            text="name",
            hover_data=["load_kw", "price"],
            title="Liquid Cooling Efficiency Frontier (Strict Bounds: PUE [1.05, 1.80], WUE [0.0, 1.50])",
            labels={"pue": "PUE", "wue": "WUE", "price": "Price ($)"},
            color_continuous_scale="Viridis",
            size_max=35
        )
        fig.add_shape(
            type="rect",
            x0=1.05, y0=0.0, x1=1.20, y1=0.10,
            fillcolor="LightGreen", opacity=0.25,
            layer="below", line_width=1, line=dict(color="Green", dash="dash")
        )
        fig.update_traces(textposition='top center')
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(market_df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("---")
            st.write("#### 🚀 Simulate Scraped Unit (CR-B)")
            selected_unit_name = st.selectbox("Select Equipment", options=market_df["name"].tolist(), key="market_sim_sel")
            s_row = market_df[market_df["name"] == selected_unit_name].iloc[0]
            
            if st.button("Submit Simulation as Change Request B"):
                payload = {
                    "name": s_row["name"],
                    "pue": float(s_row["pue"]),
                    "wue": float(s_row["wue"]),
                    "load_kw": float(s_row["load_kw"]),
                    "capacity_kw": float(s_row["capacity_kw"]),
                    "price": float(s_row["price"])
                }
                cr_id, success, msg = submit_change_request("B", payload)
                if success:
                    st.session_state["last_sim_unit"] = payload
                    st.session_state["last_cr_b_id"] = cr_id
                    st.success(f"CR-B ({cr_id}) verified!")
                else:
                    st.error(f"Verification Failed: {msg}")

        with col2:
            st.markdown("---")
            st.write("#### 🗑️ Remove Unit from Market Roster")
            del_m_unit = st.selectbox("Select Unit to Remove", options=market_df["name"].tolist(), key="del_market_sel")
            if st.button("Delete from Market"):
                with get_db() as con:
                    del_id = market_df[market_df["name"] == del_m_unit].iloc[0]["equipment_id"]
                    con.execute("DELETE FROM vendor_equipment_raw WHERE equipment_id = ?", (del_id,))
                st.success(f"Removed {del_m_unit}!")
                time.sleep(0.5)
                st.rerun()

# ----------------- Tab 2: Fleet View + ROI -----------------
with tabs[1]:
    st.subheader("Active Fleet & Cost/Carbon ROI Impact Simulator")
    with get_db() as con:
        fleet_df = con.execute("SELECT * FROM v_fleet_active").df()
    st.dataframe(fleet_df, use_container_width=True)

    if not fleet_df.empty:
        total_load = fleet_df["load_kw"].sum()
        total_cap = fleet_df["capacity_kw"].sum()
        base_pue = (fleet_df["pue"] * fleet_df["load_kw"]).sum() / total_load if total_load > 0 else 0
        base_wue = (fleet_df["wue"] * fleet_df["load_kw"]).sum() / total_load if total_load > 0 else 0

        st.markdown("### Current Fleet Baseline")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Blended PUE", f"{base_pue:.3f}")
        m2.metric("Blended WUE", f"{base_wue:.3f}")
        m3.metric("Total Load", f"{total_load:,.1f} kW")
        m4.metric("Total Capacity", f"{total_cap:,.1f} kW")

        st.markdown("---")
        st.subheader("🌱 Projected Environmental & Financial ROI")
        
        sim_payload = st.session_state.get("last_sim_unit", None)
        if sim_payload is None and not market_df.empty:
            fm = market_df.iloc[0]
            sim_payload = {"name": fm["name"], "pue": float(fm["pue"]), "wue": float(fm["wue"]), "load_kw": float(fm["load_kw"]), "capacity_kw": float(fm["capacity_kw"]), "price": float(fm["price"])}

        if sim_payload:
            st.info(f"Simulating: **{sim_payload['name']}** (PUE: {sim_payload['pue']:.3f}, Load: {sim_payload['load_kw']} kW, Cap: {sim_payload['capacity_kw']} kW)")
            
            sim_load = sim_payload["load_kw"]
            sim_cap = sim_payload["capacity_kw"]
            sim_pue_val = sim_payload["pue"]
            sim_wue_val = sim_payload["wue"]

            new_total_load = total_load + sim_load
            new_total_cap = total_cap + sim_cap
            sim_blended_pue = ((fleet_df["pue"] * fleet_df["load_kw"]).sum() + (sim_pue_val * sim_load)) / new_total_load if new_total_load > 0 else 0
            sim_blended_wue = ((fleet_df["wue"] * fleet_df["load_kw"]).sum() + (sim_wue_val * sim_load)) / new_total_load if new_total_load > 0 else 0

            d1, d2, d3, d4 = st.columns(4)
            pue_diff = sim_blended_pue - base_pue
            d1.metric("Projected PUE", f"{sim_blended_pue:.3f}", delta=f"{pue_diff:.3f}", delta_color="inverse")
            d2.metric("Projected WUE", f"{sim_blended_wue:.3f}", delta=f"{sim_blended_wue - base_wue:.3f}", delta_color="inverse")
            d3.metric("Projected Load", f"{new_total_load:,.1f} kW", delta=f"+{sim_load:,.1f} kW")
            d4.metric("Projected Capacity", f"{new_total_cap:,.1f} kW", delta=f"+{sim_cap:,.1f} kW")

            annual_it_kwh = new_total_load * 8760
            baseline_annual_kwh = annual_it_kwh * base_pue
            projected_annual_kwh = annual_it_kwh * sim_blended_pue
            annual_saved_kwh = max(0.0, baseline_annual_kwh - projected_annual_kwh)
            annual_saved_cost = annual_saved_kwh * 0.18
            annual_co2_ton_saved = (annual_saved_kwh * 0.38) / 1000.0

            r1, r2, r3 = st.columns(3)
            r1.metric("⚡ Annual Energy Saved", f"{annual_saved_kwh:,.0f} kWh/yr")
            r2.metric("💰 Estimated OPEX Savings", f"${annual_saved_cost:,.0f} /yr")
            r3.metric("🌲 Carbon Reduction", f"{annual_co2_ton_saved:,.1f} tons CO2/yr")

            cr_b_id = st.session_state.get("last_cr_b_id", None)
            if cr_b_id:
                if st.button("✅ Approve CR-B & Add Permanently to Active Fleet"):
                    ok, msg = execute_approval(cr_b_id)
                    if ok:
                        st.success(f"Port Approval Action Triggered: {msg}")
                        time.sleep(1)
                        st.rerun()

# ----------------- Tab 3: HVAC IoT Mart -----------------
with tabs[2]:
    col_i_t1, col_i_t2 = st.columns([4, 1])
    with col_i_t1:
        st.subheader("HVAC IoT Energy Anomaly Analytics Mart")
    with col_i_t2:
        st.caption(f"⚡ **10s Grid Sync** (Cycle: #{count})")

    with get_db() as con:
        anom_df = con.execute("SELECT * FROM v_iot_anomalies").df()
        grid_df = con.execute("SELECT * FROM grid_energy_tariffs").df()

    g1, g2, g3 = st.columns(3)
    for idx, row in grid_df.iterrows():
        cols = [g1, g2, g3]
        cols[idx % 3].metric(
            f"🌐 {row['region_name']}",
            f"${row['current_tariff_per_kwh']:.3f} /kWh",
            delta=f"Live Tariff",
            delta_color="off"
        )

    st.markdown("---")
    st.write("#### 🚨 Low Power Factor (<0.85) Inefficiency Penalty")
    st.dataframe(anom_df, use_container_width=True)

    col_iot1, col_iot2 = st.columns(2)
    with col_iot1:
        st.write("#### 📡 Broadcast Sensor Reading")
        with st.form("iot_stream_form"):
            sim_chiller = st.selectbox("Chiller Sensor", ["chiller_alpha", "vertiv_coolchip_cdu", "submer_smartpodx"])
            sim_pf = st.slider("Power Factor", 0.60, 1.00, 0.78, 0.01)
            sim_pwr = st.number_input("Active Power (kW)", value=310.0)
            if st.form_submit_button("Broadcast Sensor Reading"):
                with get_db() as con:
                    new_id = f"rd-{int(time.time())}"
                    con.execute("""
                        INSERT INTO hvac_iot_telemetry VALUES (?, ?, ?, ?, 230.0, 33.0, CURRENT_TIMESTAMP)
                    """, (new_id, sim_chiller, sim_pf, sim_pwr))
                st.success(f"Broadcasted {new_id}!")
                time.sleep(0.5)
                st.rerun()

    with col_iot2:
        st.write("#### 🗑️ Manage Telemetry Broadcast Records")
        if not anom_df.empty:
            del_reading = st.selectbox("Select Reading ID to Delete", options=anom_df["reading_id"].tolist())
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("Delete Selected Reading"):
                with get_db() as con:
                    con.execute("DELETE FROM hvac_iot_telemetry WHERE reading_id = ?", (del_reading,))
                st.success(f"Deleted {del_reading}!")
                time.sleep(0.5)
                st.rerun()
            if col_b2.button("Clear All Broadcasts"):
                with get_db() as con:
                    con.execute("DELETE FROM hvac_iot_telemetry")
                st.success("Cleared all records!")
                time.sleep(0.5)
                st.rerun()

# ----------------- Tab 4: 變數與壞資料手動測試器 -----------------
with tabs[3]:
    st.subheader("🎛️ Live Drift & Bad Data Simulator")
    st.caption("Contract Bounds: PUE [1.05 - 1.80] | WUE [0.00 - 1.50] | Load [30 - 500kW] | Capacity [50 - 1000kW] | Price [$30,000 - $80,000]")

    col_sim_a, col_sim_b = st.columns(2)
    
    with col_sim_a:
        st.markdown("#### ⚡ Dynamic Electric Grid Pricing Drift")
        with st.form("drift_tariff_form"):
            ca_new = st.number_input("California CAISO ($/kWh)", min_value=0.05, max_value=1.00, value=0.285, step=0.01)
            va_new = st.number_input("Virginia PJM ($/kWh)", min_value=0.05, max_value=1.00, value=0.125, step=0.01)
            tx_new = st.number_input("Texas ERCOT ($/kWh)", min_value=0.05, max_value=1.00, value=0.160, step=0.01)
            if st.form_submit_button("⚡ Inject Grid Pricing Drift"):
                with get_db() as con:
                    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-west-ca'", (ca_new,))
                    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-east-va'", (va_new,))
                    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-central-tx'", (tx_new,))
                st.success("Grid pricing drift applied!")
                time.sleep(0.5)
                st.rerun()

    with col_sim_b:
        st.markdown("#### 🚨 Inject Bad / Malformed Vendor Data (Manual Test)")
        with st.form("bad_data_form"):
            bad_type = st.selectbox(
                "Select Bad Data Scenario (Violates Strict Bounds)",
                [
                    "PUE Outlier (PUE = 2.45 > 1.80)",
                    "Suspicious Low PUE (PUE = 1.01 < 1.05)",
                    "Excessive Price ($120,000 > $80,000 USD)",
                    "Capacity Mismatch (Cap 40kW < Load 400kW)",
                    "WUE Air Cooling Outlier (WUE = 2.20 > 1.50)"
                ]
            )
            if st.form_submit_button("💥 Inject Bad Data to Ingest Pipeline"):
                if "2.45" in bad_type:
                    payload = {"name": "Corrupted Chiller Alpha", "pue": 2.45, "wue": 0.10, "load_kw": 120.0, "capacity_kw": 800.0, "price": 45000.0}
                elif "1.01" in bad_type:
                    payload = {"name": "Fake Free Energy Tank", "pue": 1.01, "wue": 0.02, "load_kw": 80.0, "capacity_kw": 500.0, "price": 38000.0}
                elif "120,000" in bad_type:
                    payload = {"name": "Overpriced CDU Module", "pue": 1.15, "wue": 0.02, "load_kw": 60.0, "capacity_kw": 300.0, "price": 120000.0}
                elif "Capacity" in bad_type:
                    payload = {"name": "Undersized Radiator", "pue": 1.20, "wue": 0.02, "load_kw": 400.0, "capacity_kw": 40.0, "price": 35000.0}
                else:
                    payload = {"name": "Excessive Water Chiller", "pue": 1.35, "wue": 2.20, "load_kw": 200.0, "capacity_kw": 600.0, "price": 55000.0}
                
                cr_id, passed, msg = submit_change_request("A", payload)
                if not passed:
                    st.error(f"🛡️ Data Contract Gate Triggered: {msg}")
                    st.warning(f"Payload successfully blocked from Production and isolated into Quarantine table!")

# ----------------- Tab 5: Audit & Quarantine Log -----------------
with tabs[4]:
    st.subheader("Factory Audit Trail & Data Contract Quarantine")
    with get_db() as con:
        cr_history_df = con.execute("SELECT * FROM change_requests ORDER BY timestamp DESC").df()
        quarantine_df = con.execute("SELECT * FROM quarantine ORDER BY created_at DESC").df()

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.write("#### 📜 Change Request Ledger (CR-A & CR-B)")
        st.dataframe(cr_history_df, use_container_width=True)
    with col_h2:
        st.write("#### 🛡️ Quarantine Box (Malformed / Contract Dropped)")
        st.dataframe(quarantine_df, use_container_width=True)

# ----------------- Tab 6: Vendor Scraper (CR-A) -----------------
with tabs[5]:
    st.subheader("Automated Vendor Spec Scraper (Change Request A)")
    with st.form("vendor_scrape_form"):
        v_url = st.text_input("Vendor Spec URL", "https://www.refjet.ai/#/technology")
        v_name = st.text_input("Vendor Product Name", "RefJet Cooling Unit")
        submitted = st.form_submit_button("Fetch Specs with Bright Data & Submit CR-A")
        if submitted:
            with st.spinner("Scraping via Bright Data..."):
                time.sleep(1)
                extracted_payload = {"name": v_name, "url": v_url, "pue": 1.08, "wue": 0.01, "load_kw": 110.0, "capacity_kw": 920.0, "price": 49000.0}
                cr_id, success, msg = submit_change_request("A", extracted_payload)
                if success:
                    st.session_state["pending_cra_id"] = cr_id
                    st.session_state["pending_cra_payload"] = extracted_payload
                    st.success(f"CR-A ({cr_id}) verified!")
                else:
                    st.error(f"Verification Failed: {msg}")

    pending_id = st.session_state.get("pending_cra_id", None)
    pending_data = st.session_state.get("pending_cra_payload", None)
    if pending_id and pending_data:
        st.markdown("---")
        st.write("#### 🛡️ Port Human Approval Gate")
        st.json(pending_data)
        if st.button("✅ Approve & Add to Dashboard 1"):
            ok, msg = execute_approval(pending_id)
            if ok:
                st.success(f"Approved: {msg}")
                st.session_state["pending_cra_id"] = None
                st.session_state["pending_cra_payload"] = None
                time.sleep(1)
                st.rerun()

# ----------------- Tab 7: Baseline Entry -----------------
with tabs[6]:
    st.subheader("Enter Baseline Fleet Equipment")
    with st.form("baseline_form"):
        name = st.text_input("Baseline Unit Name", value="Chiller Alpha")
        b_pue = st.number_input("Baseline PUE", value=1.45, min_value=1.05, max_value=1.80)
        b_wue = st.number_input("Baseline WUE", value=0.85, min_value=0.00, max_value=1.50)
        b_load = st.number_input("Baseline Load (kW)", value=300.0, min_value=30.0, max_value=500.0)
        b_cap = st.number_input("Baseline Capacity (kW)", value=700.0, min_value=50.0, max_value=1000.0)
        b_price = st.number_input("Baseline Cost ($)", value=65000.0, min_value=30000.0, max_value=80000.0)
        if st.form_submit_button("Add Baseline Unit"):
            with get_db() as con:
                con.execute("INSERT OR REPLACE INTO baseline_equipment VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (name.lower().replace(" ", "_"), name, b_pue, b_wue, b_price, b_load, b_cap))
            st.success(f"Added {name}!")
