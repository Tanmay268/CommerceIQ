"""
Orchestrates the full CommerceIQ pipeline end to end, in dependency order.
Assumes Docker Desktop is running and `docker compose up -d` has already
started the Postgres container (this script doesn't manage Docker itself).

Usage:  venv\\Scripts\\python.exe src\\run_all.py
"""

import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent

STEPS = [
    "generate_data.py",
    "clean_data.py",
    "load_to_db.py",
    "rfm.py",
    "churn.py",
    "forecasting.py",
    "export_powerbi_star_schema.py",
    "generate_insights.py",
]


def main():
    python = sys.executable
    for step in STEPS:
        print(f"\n{'=' * 60}\n  Running {step}\n{'=' * 60}")
        result = subprocess.run([python, str(SRC_DIR / step)], cwd=SRC_DIR)
        if result.returncode != 0:
            print(f"\n{step} failed (exit code {result.returncode}). Stopping.")
            sys.exit(result.returncode)
    print("\nPipeline complete. Run the dashboard with:")
    print("  venv\\Scripts\\streamlit run dashboard\\Home.py")


if __name__ == "__main__":
    main()
