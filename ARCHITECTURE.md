# Architecture Notes

## Current (local / Docker Compose)

See the diagram in `README.md`. In short: `etl/` extracts from Kalshi into a
local raw JSON data lake, transforms with pandas, and loads curated Parquet
plus idempotent Postgres upserts. `app/` is a read-only FastAPI layer over
that same Postgres database, serving both a JSON API and a small
server-rendered HTML UI.

## Mapping onto AWS (roadmap)

| Local component                         | AWS equivalent                                                        |
|------------------------------------------|-------------------------------------------------------------------------|
| `data_lake/raw/`, `data_lake/curated/`   | Amazon S3 (raw and curated buckets/prefixes, same `dt=YYYY-MM-DD` partitioning) |
| Postgres (Docker Compose service)        | Amazon RDS for PostgreSQL or Aurora PostgreSQL                          |
| FastAPI `api` service                    | Amazon ECS Fargate service (behind an ALB), or App Runner              |
| `etl` one-off container / cron           | Amazon ECS Fargate scheduled task, or an Airflow DAG run on MWAA        |
| `airflow/dags/kalshi_pipeline_dag.py`    | Amazon MWAA (Managed Workflows for Apache Airflow)                      |
| Python `logging` structured lines        | Amazon CloudWatch Logs (+ CloudWatch Alarms on error-rate/duration metrics) |
| GitHub Actions CI                        | Unchanged -- GitHub Actions can deploy directly to ECS/S3/RDS via OIDC  |

This mapping is intentionally not implemented -- the project runs entirely
locally via Docker Compose -- but it demonstrates how the same code would be
deployed at scale.
