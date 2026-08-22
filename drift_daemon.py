import time
import random
import duckdb
import datetime
from engine import submit_change_request

def run_drift_cycle(cycle_count: int):
    con = duckdb.connect("datacenter.duckdb")

    # 1. 正常 10 秒電價與合法規格微幅跳動
    ca_tariff = round(0.245 + random.uniform(-0.025, 0.035), 3)
    va_tariff = round(0.118 + random.uniform(-0.010, 0.015), 3)
    tx_tariff = round(0.135 + random.uniform(-0.015, 0.030), 3)

    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-west-ca'", (ca_tariff,))
    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-east-va'", (va_tariff,))
    con.execute("UPDATE grid_energy_tariffs SET current_tariff_per_kwh = ?, last_updated = CURRENT_TIMESTAMP WHERE region_id = 'us-central-tx'", (tx_tariff,))

    con.execute("""
        UPDATE vendor_equipment_raw
        SET pue = CASE 
                    WHEN pue + ? > 1.80 THEN 1.80
                    WHEN pue + ? < 1.05 THEN 1.05
                    ELSE ROUND(pue + ?, 3)
                  END,
            price = CASE 
                    WHEN price + ? > 80000 THEN 80000
                    WHEN price + ? < 30000 THEN 30000
                    ELSE ROUND(price + ?, 0)
                  END,
            last_scraped = CURRENT_TIMESTAMP
        WHERE equipment_id = 'submer_smartpodx'
    """, (0.005, -0.005, random.choice([-0.005, 0.005, 0.000]), 500, -500, random.choice([-500, 500, 0])))

    con.close()
    now_str = datetime.datetime.now().strftime("%H:%M:%S")

    # 2. 每 3 輪 (30 秒) 自動模擬一次「外部爬到壞資料」
    if cycle_count % 3 == 0:
        bad_cases = [
            {"name": "Submer SmartPodX (Drifted)", "pue": 2.65, "wue": 0.01, "load_kw": 120.0, "capacity_kw": 900.0, "price": 52000.0}, # PUE 破表 > 1.80
            {"name": "Vertiv CoolChip CDU (Drifted)", "pue": 1.10, "wue": 2.40, "load_kw": 95.0, "capacity_kw": 800.0, "price": 38000.0},  # WUE 破表 > 1.50
            {"name": "RefJet Cooling Unit (Drifted)", "pue": 1.05, "wue": 0.01, "load_kw": 110.0, "capacity_kw": 920.0, "price": 140000.0}, # 價格破表 > 80k
            {"name": "Faulty Chiller Model-Z", "pue": 0.85, "wue": 0.02, "load_kw": 200.0, "capacity_kw": 500.0, "price": 45000.0}         # PUE < 1.05
        ]
        chosen = random.choice(bad_cases)
        cr_id, passed, msg = submit_change_request("A", chosen)
        print(f"\033[91m[{now_str}] ⚠️ [BAD DATA BLOCKED] '{chosen['name']}' -> Contract Gate: REJECTED ({msg}) | Last Known Good Preserved\033[0m")
    else:
        print(f"[{now_str}] 🟢 10s Drift Ingested -> CA: ${ca_tariff}/kWh | Valid Market Norms Live Updated")

if __name__ == "__main__":
    print("🚀 Background Live Drift & Auto-Quarantine Daemon Started (10s ticker, 30s bad data test)...")
    cycle = 1
    while True:
        try:
            run_drift_cycle(cycle)
            cycle += 1
            time.sleep(10)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            print(f"Ticker Error: {e}")
            time.sleep(5)
