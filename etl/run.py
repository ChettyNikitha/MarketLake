"""CLI entrypoint: python -m etl.run [--dry-run]"""
import argparse
import json

from etl.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kalshi ETL pipeline.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and transform as usual, but skip writing to Postgres.",
    )
    args = parser.parse_args()

    summary = run_pipeline(dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
