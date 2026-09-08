"""OPTIONAL stretch: an Airflow DAG stub for running the Kalshi ETL pipeline
on a daily schedule.

This is a design artifact only -- it is NOT wired into docker-compose.yml or
CI, and Airflow is not a project dependency. It documents how the existing
etl.pipeline.run_pipeline() would be orchestrated under Airflow (or, in
production, MWAA -- see ARCHITECTURE.md).
"""
from __future__ import annotations

import datetime as dt

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    AIRFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency, not installed by default
    AIRFLOW_AVAILABLE = False


def _run_kalshi_pipeline() -> None:
    from etl.pipeline import run_pipeline

    run_pipeline()


if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="kalshi_pipeline",
        description="Daily extract-transform-load of Kalshi events/markets into Postgres.",
        schedule="@daily",
        start_date=dt.datetime(2026, 1, 1),
        catchup=False,
        tags=["kalshi", "etl"],
    ) as dag:
        run_etl = PythonOperator(
            task_id="run_kalshi_pipeline",
            python_callable=_run_kalshi_pipeline,
        )
