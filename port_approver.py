import duckdb
import json
from engine import tracer

def approve_change_request(cr_id: str, approver_name: str = "Operator"):
    con = duckdb.connect("datacenter.duckdb")
    with tracer.start_as_current_span("port_approval_action"):
        row = con.execute("SELECT type, payload, status FROM change_requests WHERE id = ?", (cr_id,)).fetchone()
        if not row:
            print("Change Request not found.")
            con.close()
            return
        
        cr_type, payload_str, status = row
        if status != "pending_approval":
            print(f"Cannot approve request with status: {status}")
            con.close()
            return

        payload = json.loads(payload_str)
        eq_id = payload["name"].lower().replace(" ", "_")

        if cr_type == "A":
            # Expand vendor raw specs and refresh view
            con.execute("""
                INSERT OR REPLACE INTO vendor_equipment_raw 
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (eq_id, payload["name"], payload["pue"], payload["wue"], payload["price"], payload["load_kw"], payload["capacity_kw"]))
            print(f"Approved CR-A: Vendor equipment '{payload['name']}' published to Market View.")

        elif cr_type == "B":
            # Add to baseline fleet and refresh view
            con.execute("""
                INSERT OR REPLACE INTO baseline_equipment 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (eq_id, payload["name"], payload["pue"], payload["wue"], payload["price"], payload["load_kw"], payload["capacity_kw"]))
            print(f"Approved CR-B: Equipment '{payload['name']}' added to Fleet View.")

        # Update CR status
        con.execute(
            "UPDATE change_requests SET status = 'approved', reviewed_by = ? WHERE id = ?",
            (approver_name, cr_id)
        )
    con.close()

if __name__ == "__main__":
    con = duckdb.connect("datacenter.duckdb")
    pending = con.execute("SELECT id, type, payload FROM change_requests WHERE status = 'pending_approval'").fetchall()
    con.close()
    for item in pending:
        approve_change_request(item[0])
