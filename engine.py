import duckdb
import uuid
import json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "cooling-pue-factory"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("cooling-pue-factory")

def get_db():
    return duckdb.connect("datacenter.duckdb")

def verify_change_request(payload: dict) -> tuple[bool, str]:
    """
    資料合約驗證閘門 (Strict Contract):
    - PUE: 1.05 - 1.80
    - WUE: 0.00 - 1.50
    - Load: 30 - 500 kW
    - Capacity: 50 - 1000 kW (且 capacity >= load)
    - Price: 30,000 - 80,000 USD
    """
    with tracer.start_as_current_span("verify_change_request") as span:
        span.set_attribute("payload.name", payload.get("name", "unknown"))
        
        try:
            pue = float(payload.get("pue", 0))
            wue = float(payload.get("wue", -1))
            load_kw = float(payload.get("load_kw", 0))
            capacity_kw = float(payload.get("capacity_kw", 0))
            price = float(payload.get("price", 0))
        except (ValueError, TypeError) as e:
            span.set_attribute("verification.result", "failed_type_error")
            return False, f"Contract Type Violation: Numeric conversion error ({e})"

        # 1. PUE 範圍檢查 (1.05 - 1.80)
        if not (1.05 <= pue <= 1.80):
            span.set_attribute("verification.result", "failed_pue_range")
            return False, f"PUE Contract Violation: {pue} is out of bounds [1.05, 1.80]"

        # 2. WUE 範圍檢查 (0.00 - 1.50)
        if not (0.00 <= wue <= 1.50):
            span.set_attribute("verification.result", "failed_wue_range")
            return False, f"WUE Contract Violation: {wue} is out of bounds [0.00, 1.50]"

        # 3. Load 範圍檢查 (30 - 500 kW)
        if not (30.0 <= load_kw <= 500.0):
            span.set_attribute("verification.result", "failed_load_range")
            return False, f"Load Contract Violation: {load_kw} kW is out of bounds [30.0, 500.0] kW"

        # 4. Capacity 範圍檢查 (50 - 1000 kW)
        if not (50.0 <= capacity_kw <= 1000.0):
            span.set_attribute("verification.result", "failed_capacity_range")
            return False, f"Capacity Contract Violation: {capacity_kw} kW is out of bounds [50.0, 1000.0] kW"

        # 5. 物理合理性：容量必須大於自身負載
        if capacity_kw < load_kw:
            span.set_attribute("verification.result", "failed_capacity_load_ratio")
            return False, f"Physical Plausibility Error: Cooling capacity ({capacity_kw} kW) cannot be less than load ({load_kw} kW)"

        # 6. 價格範圍檢查 (30,000 - 80,000 USD)
        if not (30000.0 <= price <= 80000.0):
            span.set_attribute("verification.result", "failed_price_range")
            return False, f"Price Contract Violation: ${price:,.0f} is out of bounds [$30,000, $80,000] USD"

        span.set_attribute("verification.result", "passed")
        return True, "Data Contract Verified: All parameters strictly within bounds."

def submit_change_request(cr_type: str, payload: dict) -> tuple[str, bool, str]:
    """送出 Change Request，未通過合約則寫入 quarantine (raw_payload, reason, created_at)"""
    cr_id = str(uuid.uuid4())
    passed, msg = verify_change_request(payload)
    
    with get_db() as con:
        if not passed:
            con.execute("""
                INSERT INTO quarantine (raw_payload, reason, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (json.dumps(payload), msg))
            return cr_id, False, msg
        
        con.execute("""
            INSERT INTO change_requests (id, type, payload, status, reviewed_by, timestamp)
            VALUES (?, ?, ?, 'pending_approval', NULL, CURRENT_TIMESTAMP)
        """, (cr_id, cr_type, json.dumps(payload)))
        
        return cr_id, True, "Queued for approval"
