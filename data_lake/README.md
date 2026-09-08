# Data Lake Layout

This directory is the local stand-in for an object-store-backed data lake
(e.g. S3 in production -- see ARCHITECTURE.md). Its contents (`raw/` and
`curated/`) are gitignored; only this README and the `.gitkeep` placeholders
are tracked.

## Partitioning

Both `raw/` and `curated/` are partitioned by ingestion date:

```
data_lake/
  raw/
    events/dt=YYYY-MM-DD/events_<run_id>_<page>.json
    markets/dt=YYYY-MM-DD/markets_<run_id>_<page>.json
  curated/
    events/dt=YYYY-MM-DD/events.parquet
    markets/dt=YYYY-MM-DD/markets.parquet
```

## Raw zone

- One JSON file per page returned by the Kalshi API, written verbatim
  (immutable, append-only -- never overwritten or mutated in place).
- `<run_id>` identifies the ETL run that produced the file; `<page>` is the
  0-indexed page number within that run.

## Curated zone

- One Parquet file per resource per run date, containing the cleaned/typed
  DataFrame that was also upserted into Postgres (see `etl/transform.py`
  and `etl/load.py`).
- Curated Parquet is meant to be read directly by analytics/BI tools or
  Spark jobs without needing the warehouse.
