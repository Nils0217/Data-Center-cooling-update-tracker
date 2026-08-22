import duckdb

con = duckdb.connect("datacenter.duckdb")

con.execute("""
CREATE TABLE IF NOT EXISTS baseline_equipment (
    equipment_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    pue DOUBLE,
    wue DOUBLE,
    price DOUBLE,
    load_kw DOUBLE,
    capacity_kw DOUBLE
);

CREATE TABLE IF NOT EXISTS vendor_equipment_raw (
    equipment_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    pue DOUBLE,
    wue DOUBLE,
    price DOUBLE,
    load_kw DOUBLE,
    capacity_kw DOUBLE,
    last_scraped TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quarantine (
    raw_payload TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_requests (
    id VARCHAR PRIMARY KEY,
    type VARCHAR,
    payload TEXT,
    verification_result VARCHAR,
    status VARCHAR,
    reviewed_by VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW v_market_active AS SELECT * FROM vendor_equipment_raw;
CREATE OR REPLACE VIEW v_fleet_active AS SELECT * FROM baseline_equipment;
""")
con.close()
print("Database and views initialized successfully.")
