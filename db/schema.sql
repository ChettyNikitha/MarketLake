-- Schema for the Kalshi markets curated warehouse.

CREATE TABLE IF NOT EXISTS events (
    event_ticker  TEXT PRIMARY KEY,
    series_ticker TEXT,
    category      TEXT,
    title         TEXT,
    status        TEXT,
    strike_date   TIMESTAMPTZ,
    loaded_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS markets (
    ticker         TEXT PRIMARY KEY,
    event_ticker   TEXT REFERENCES events(event_ticker),
    title          TEXT,
    status         TEXT,
    -- Kalshi's real API returns prices/volume as decimal strings
    -- (e.g. yes_bid_dollars="0.5500", volume_fp="1730.18"), not integers.
    yes_bid        NUMERIC(12, 4),
    yes_ask        NUMERIC(12, 4),
    no_bid         NUMERIC(12, 4),
    no_ask         NUMERIC(12, 4),
    last_price     NUMERIC(12, 4),
    volume         NUMERIC(18, 4),
    open_interest  NUMERIC(18, 4),
    loaded_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_markets_event_ticker ON markets(event_ticker);
CREATE INDEX IF NOT EXISTS idx_markets_status ON markets(status);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);

-- One row per ETL pipeline invocation, so the operator dashboard can show
-- "when did this last run, and how much data did it move" without scraping
-- log files.
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id             TEXT PRIMARY KEY,
    started_at         TIMESTAMPTZ NOT NULL,
    finished_at        TIMESTAMPTZ,
    duration_seconds   NUMERIC(10, 3),
    status             TEXT NOT NULL DEFAULT 'running',
    events_extracted   INTEGER,
    markets_extracted  INTEGER,
    events_loaded      INTEGER,
    markets_loaded     INTEGER,
    error_message      TEXT
);

CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON etl_runs(started_at DESC);
