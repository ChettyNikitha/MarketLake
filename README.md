# Kalshi-MarketLake

A data-engineering demo project built around Kalshi's public demo trading
API. It started as a small FastAPI app that live-proxied Kalshi's cricket
markets endpoint; it has since been rebuilt around a proper batch ETL
pipeline, a Postgres warehouse, and a FastAPI app that only ever reads from
that warehouse.

## Architecture

```
                        +-------------------+
                        |   Kalshi API      |
                        | /trade-api/v2/...|
                        +---------+---------+
                                  |
                                  v  (etl/kalshi_client.py: RSA-signed, retrying HTTP)
                        +-------------------+
                        |  Extract          |  etl/extract.py
                        |  raw JSON pages   |
                        +---------+---------+
                                  v
                data_lake/raw/{events,markets}/dt=YYYY-MM-DD/*.json
                                  |
                                  v  (etl/transform.py: pandas flatten/typecast)
                        +-------------------+
                        |  Transform        |
                        +---------+---------+
                                  v
                  +---------------+----------------+
                  v                                 v
   data_lake/curated/.../*.parquet        Postgres (db/schema.sql)
   (etl/load.py: to_parquet)              (etl/load.py: INSERT ... ON CONFLICT
                                            DO UPDATE upsert, idempotent)
                                                     |
                                                     v
                                          +-------------------+
                                          |   FastAPI app     |  app/main.py
                                          |  (reads Postgres  |  app/routers/*.py
                                          |   only, never     |  app/web.py
                                          |   calls Kalshi)   |
                                          +-------------------+
```

`etl/pipeline.py` orchestrates extract -> transform -> load and is run via
`python -m etl.run` (see `etl/run.py`). The FastAPI app (`app/`) never talks
to Kalshi directly; it only reads curated data back out of Postgres, both for
its JSON API (`/api/events`, `/api/markets`, `/api/analytics/...`) and its
HTML UI (`/ui/events`, `/ui/events/{event_ticker}`).

## Skills demonstrated

| Skill                          | Where                                                              |
|---------------------------------|---------------------------------------------------------------------|
| Python ETL pipeline design      | `etl/extract.py`, `etl/transform.py`, `etl/load.py`, `etl/pipeline.py` |
| Data lake / Parquet             | `etl/load.py` (`to_parquet`), `data_lake/README.md`                |
| PostgreSQL / advanced SQL       | `db/schema.sql`, `db/analytics_queries.sql` (CTE + window function) |
| SQLAlchemy (ORM + Core)         | `app/models.py`, `app/db.py`, `etl/load.py` (Core upsert SQL)      |
| FastAPI (API + server-rendered UI) | `app/main.py`, `app/routers/*.py`, `app/web.py`                 |
| API integration robustness      | `etl/kalshi_client.py` (RSA signing, retries/backoff, timeouts, cursor pagination) |
| PyTest (unit + integration)     | `tests/unit/*`, `tests/integration/*`, `tests/conftest.py`        |
| Docker / Docker Compose         | `Dockerfile`, `docker-compose.yml`                                 |
| GitHub Actions CI               | `.github/workflows/ci.yml`                                         |

## Project structure

```
app/            FastAPI application (API routers, HTML UI, DB models/config)
etl/            Extract / transform / load pipeline + Kalshi client
db/             SQL schema and example analytics queries
data_lake/      Local raw/curated data lake (gitignored contents)
tests/          Unit and integration tests + fixtures
airflow/        Optional Airflow DAG stub (not wired into CI/compose)
dbt/            Optional dbt project skeleton (not run by CI)
```

## Setup

1. Copy `.env.example` to `.env` and fill in real values (or leave the demo
   defaults if you don't have Kalshi credentials -- the FastAPI app itself
   never needs them, only the ETL pipeline does).

2. Start Postgres (and, if desired, the API) with Docker Compose:

   ```
   docker compose up -d postgres
   docker compose up api
   ```

   Postgres auto-applies `db/schema.sql` on first startup via
   `docker-entrypoint-initdb.d`.

3. Run the ETL pipeline to populate the warehouse (requires real or demo
   Kalshi credentials in `.env`):

   ```
   docker compose run --rm etl
   ```

   or locally without Docker:

   ```
   pip install -r requirements.txt
   python -m etl.run            # or: python -m etl.run --dry-run
   ```

4. Browse the app at `http://localhost:8000/` (`/ui/events` for the event
   list, `/docs` for the interactive API docs).

## Running tests

```
pip install -r requirements-dev.txt
pytest tests/unit            # no network, no database required
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg2://kalshi:kalshi@localhost:5433/kalshi pytest tests/integration
```

Integration tests are skipped automatically if `DATABASE_URL` isn't
reachable. CI (`.github/workflows/ci.yml`) runs the full suite against a
Postgres service container.

## Roadmap 

- **Airflow DAG stub** (`airflow/dags/kalshi_pipeline_dag.py`) -- a daily
  `PythonOperator` task wrapping `etl.pipeline.run_pipeline`. Guarded
  `airflow` import; not installed or run by this repo's CI/compose.
- **dbt models** (`dbt/`) -- a minimal staging + marts skeleton over the same
  Postgres tables, showing how transformation logic could move out of
  `etl/transform.py` and into dbt as the project grows.
- **PySpark transform** (`etl/spark_transform.py`) -- re-implements the
  events/markets flattening in Spark DataFrames instead of pandas, for a
  bigger-data version of the same pipeline. See `requirements-optional.txt`.
- **AWS mapping** -- see `ARCHITECTURE.md` for how each piece would map onto
  managed AWS services (S3, RDS/Aurora, ECS Fargate, MWAA, CloudWatch).

See `ARCHITECTURE.md` for further architectural notes.
