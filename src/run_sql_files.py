"""
Verification utility: executes every statement in sql/*.sql against the
live database and prints row counts (+ a small preview) for each query.
Used to confirm every analysis query in the repo actually runs cleanly.
"""

import sys
from pathlib import Path

import pandas as pd

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = BASE_DIR / "sql"


def split_statements(sql_text: str) -> list[str]:
    # Simple split on ';' at top level - fine here since none of our
    # analysis queries contain semicolons inside string literals.
    statements = []
    current = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def main():
    files = sorted(SQL_DIR.glob("0[1-9]_*.sql"))
    engine = get_engine()
    total = 0
    for f in files:
        print(f"\n===== {f.name} =====")
        statements = split_statements(f.read_text(encoding="utf-8"))
        for i, stmt in enumerate(statements, start=1):
            total += 1
            try:
                df = pd.read_sql(stmt, engine)
                print(f"  Query {i}: OK -> {len(df)} rows, {len(df.columns)} columns")
                if "--print" in sys.argv:
                    print(df.head(3).to_string(index=False))
            except Exception as e:
                print(f"  Query {i}: FAILED -> {e}")
                raise
    print(f"\nAll {total} queries across {len(files)} files executed successfully.")


if __name__ == "__main__":
    main()
