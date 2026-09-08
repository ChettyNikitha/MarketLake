# dbt project (optional stretch)

This is a minimal dbt project skeleton targeting the same Postgres curated
tables that `etl/load.py` writes to (`events`, `markets`). It is a design
artifact showing how transformation logic could move into dbt as the project
grows -- it is **not** run by CI and has no runtime dependency from the
FastAPI app or the ETL pipeline.

## Layout

- `models/staging/stg_markets.sql` -- light cleanup select over `markets`.
- `models/marts/top_markets_by_volume.sql` -- per-event volume ranking,
  mirroring `db/analytics_queries.sql` query (1).

## Would-be usage

```
pip install dbt-postgres
dbt run --profiles-dir . --project-dir dbt
```

You would need a `profiles.yml` (not included) pointing `profile: kalshi_markets`
at the same `DATABASE_URL` used by the app/ETL, and a `source` definition for
`kalshi.markets` in a `sources.yml`.
