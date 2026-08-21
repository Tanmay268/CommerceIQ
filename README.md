# CommerceIQ — E-commerce Business Intelligence & Customer Analytics Platform

A synthetic-data portfolio project analyzing e-commerce sales, customers,
products, marketing, and profitability — SQL, Python, and an interactive
dashboard — built to answer not just "what happened" but "why, and what
should we do next."

Every architectural decision behind this project (data source, database,
dashboard delivery, scale, tooling) is recorded with reasoning and
trade-offs in **[`reports/decisions_log.md`](reports/decisions_log.md)** —
read that first for the *why*. This README is the *how to run it*.

## Stack

- **Data**: synthetic, seeded generator (Python/Faker/NumPy) — 7 tables, ~2,000 customers / ~5,000 orders / ~150 products / ~15,000 sessions, 1 year of history
- **Cleaning**: Pandas — see the auto-generated report in `reports/decisions_log.md`
- **Database**: PostgreSQL 16, via Docker
- **Analytics**: 31 SQL queries (joins, CTEs, window functions) + Python (EDA, RFM segmentation, rule-based churn risk, product profitability, forecasting)
- **Dashboard**: Streamlit + Plotly (working, tested) — plus a Power BI star-schema export + full DAX guide as a bonus deliverable

## Prerequisites

- Python 3.13+ (`python --version`)
- Docker Desktop, **running**, before step 4 below

## Setup

```powershell
# 1. Create and activate the virtual environment
python -m venv venv
venv\Scripts\Activate.ps1          # or: venv\Scripts\activate.bat (cmd)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the env template and adjust if you like (defaults work as-is for local dev)
copy .env.example .env

# 4. Start Postgres (Docker Desktop must be running)
docker compose up -d
```

## Run the full pipeline

```powershell
cd src
..\venv\Scripts\python.exe run_all.py
```

This runs, in order: generate synthetic data → clean it → load into
Postgres → RFM segmentation → churn/risk scoring → forecasting → Power BI
star-schema export → business insights generation.

Or run each stage individually (all from the `src/` directory, since the
modules import each other with relative imports):

```powershell
cd src
..\venv\Scripts\python.exe generate_data.py
..\venv\Scripts\python.exe clean_data.py
..\venv\Scripts\python.exe load_to_db.py
..\venv\Scripts\python.exe rfm.py
..\venv\Scripts\python.exe churn.py
..\venv\Scripts\python.exe forecasting.py
..\venv\Scripts\python.exe export_powerbi_star_schema.py
..\venv\Scripts\python.exe generate_insights.py
```

## Verify the SQL layer

```powershell
cd src
..\venv\Scripts\python.exe run_sql_files.py
```

Executes all 31 queries in `sql/*.sql` against the live database and
reports row/column counts per query — a quick way to confirm the schema
and data are in a good state.

## Run the notebooks

```powershell
cd notebooks
..\venv\Scripts\jupyter notebook
```

Or re-execute headless (outputs are already saved in the repo from the
last run, so this is only needed if you regenerate the data):

```powershell
..\venv\Scripts\jupyter nbconvert --to notebook --execute --inplace 01_eda.ipynb
```

(repeat for `02_rfm_analysis`, `03_product_profitability`, `04_marketing_funnel`, `05_forecasting`)

## Run the dashboard

```powershell
venv\Scripts\streamlit run dashboard\Home.py
```

Opens at `http://localhost:8501`. Four pages (sidebar navigation):
**Executive**, **Customer Analytics**, **Product Analytics**, **Marketing &
Funnel Analytics** — all sharing one filter panel (date range, state,
category, product, RFM segment, membership tier, channel, device).

## Power BI (optional, manual assembly)

Power BI Desktop wasn't available in the build environment and `.pbix` is
a closed binary format with no CLI, so this repo ships the next best thing:
a ready-to-import star schema (`powerbi/star_schema_export/*.csv`) and a
complete build guide with every DAX measure and a page-by-page walkthrough
(`powerbi/dax_measures.md`). Follow that guide in Power BI Desktop to
assemble the same 4 pages as the Streamlit dashboard.

## Project structure

```
CommerceIQ/
├── data/{raw,cleaned}/        synthetic CSVs
├── src/                       pipeline scripts (generation → cleaning → load → analytics)
├── sql/                       31 analysis queries across 5 domain files
├── notebooks/                 EDA, RFM, product profitability, marketing/funnel, forecasting
├── dashboard/                 Streamlit + Plotly app (4 pages)
├── powerbi/                   star schema export + DAX measure library/build guide
├── reports/
│   ├── decisions_log.md       every architectural decision + reasoning + trade-offs
│   ├── business_insights.md   findings/recommendations generated from real query results
│   └── figures/                saved charts (e.g. the forecast plot)
├── docker-compose.yml          Postgres service
└── requirements.txt
```

## Notes on the data

The dataset is entirely synthetic (seed=42, fully reproducible) — no real
business exists behind these numbers. It's deliberately generated messy
(inconsistent casing, missing values, a few duplicates/invalid rows, a
handful of orphan foreign keys) so `src/clean_data.py` has real problems to
solve, and the exact fixes applied are logged with before/after row counts
in `reports/decisions_log.md`.
