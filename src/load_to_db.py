"""Applies sql/00_schema.sql then bulk-loads data/cleaned/*.csv into Postgres."""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = BASE_DIR / "data" / "cleaned"
SCHEMA_FILE = BASE_DIR / "sql" / "00_schema.sql"

# Load order matters: parents before children (FK dependencies).
LOAD_ORDER = [
    "customers",
    "products",
    "orders",
    "payments",
    "returns",
    "marketing_campaigns",
    "website_sessions",
]

DATE_COLUMNS = {
    "customers": ["signup_date"],
    "orders": ["order_date"],
    "payments": ["payment_date"],
    "returns": ["return_date"],
    "marketing_campaigns": ["start_date", "end_date"],
    "website_sessions": ["session_date"],
}


def apply_schema(engine):
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    print("Schema applied.")


def load_tables(engine):
    for table in LOAD_ORDER:
        df = pd.read_csv(CLEAN_DIR / f"{table}.csv", parse_dates=DATE_COLUMNS.get(table, []))
        df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=1000)
        print(f"  {table:22s} -> {len(df):6d} rows loaded")


def verify(engine):
    print("\nVerification (DB row counts vs cleaned CSV row counts):")
    with engine.connect() as conn:
        for table in LOAD_ORDER:
            csv_count = len(pd.read_csv(CLEAN_DIR / f"{table}.csv"))
            db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            status = "OK" if csv_count == db_count else "MISMATCH"
            print(f"  {table:22s} CSV={csv_count:6d}  DB={db_count:6d}  [{status}]")
            assert csv_count == db_count, f"Row count mismatch for {table}"


def main():
    engine = get_engine()
    apply_schema(engine)
    load_tables(engine)
    verify(engine)
    print("\nAll tables loaded and verified.")


if __name__ == "__main__":
    main()
