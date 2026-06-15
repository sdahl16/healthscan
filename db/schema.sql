CREATE TABLE IF NOT EXISTS hospitals (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT,
    address TEXT,
    state TEXT,
    zip TEXT,
    cms_hpt_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mrf_sources (
    id INTEGER PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id),
    source_url TEXT NOT NULL,
    content_type TEXT,
    content_length_bytes INTEGER,
    mrf_format TEXT,
    mrf_date TEXT,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TEXT,
    last_status TEXT,
    last_error TEXT,
    UNIQUE(hospital_id, source_url)
);

CREATE TABLE IF NOT EXISTS indexed_prices (
    id INTEGER PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id),
    mrf_source_id INTEGER NOT NULL REFERENCES mrf_sources(id),
    procedure_name TEXT NOT NULL,
    procedure_code TEXT NOT NULL,
    code_type TEXT NOT NULL,
    description TEXT,
    setting TEXT,
    price_type TEXT NOT NULL CHECK (
        price_type IN (
            'gross',
            'cash',
            'negotiated',
            'negotiated_min',
            'negotiated_max',
            'median_allowed',
            'allowed_p10',
            'allowed_p90'
        )
    ),
    amount NUMERIC NOT NULL,
    payer_name TEXT,
    plan_name TEXT,
    allowed_amount_count INTEGER,
    last_updated TEXT,
    source_url TEXT NOT NULL,
    data_quality_flag TEXT,
    parsed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parse_warnings TEXT
);

CREATE INDEX IF NOT EXISTS idx_indexed_prices_lookup
ON indexed_prices (code_type, procedure_code, hospital_id);

CREATE INDEX IF NOT EXISTS idx_indexed_prices_procedure
ON indexed_prices (procedure_name, hospital_id);

CREATE INDEX IF NOT EXISTS idx_indexed_prices_price_type
ON indexed_prices (price_type, procedure_code);
