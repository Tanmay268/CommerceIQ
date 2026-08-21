# CommerceIQ — Decisions Log

Living record of every architectural decision made while building this project, the reasoning behind it, and the trade-offs considered. Entries are appended chronologically as the build progresses.

---

## 2026-08-21 — Project kickoff & scoping

**Source of truth**: a spec PDF ("E-commerce Business Intelligence & Customer Analytics Platform") describing a portfolio project analyzing e-commerce sales/customers/products/marketing via SQL + Python + Power BI, with an emphasis on *why* metrics moved, not just charting *what* happened.

Before writing any code, the environment was audited and 8 scoping questions were put to the user rather than assumed. Findings and decisions:

### Environment audit
- Python 3.13.7 + pip 25.2 present.
- PostgreSQL not installed: no `psql` on PATH, no Postgres Windows service running.
- Docker CLI 28.3.2 present but the daemon was not running (Docker Desktop installed but stopped).
- Power BI Desktop **not installed**. It is also a closed, binary/proprietary GUI format with no CLI or API — meaning even if installed, Claude Code cannot author or test a `.pbix` file programmatically. This is a hard capability limit, not a preference.
- git 2.55.0 present; working directory was empty and not yet a repo.

### Decision: Data source — fully synthetic
**Choice**: Generate a synthetic dataset from scratch with a seeded Python generator.
**Why**: No real dataset was provided or exists. The PDF's own examples (₹ currency, Chennai/Tamil Nadu, specific KPI numbers) are templates, not real data, so a generator is the only path to an end-to-end working system.
**Trade-off accepted**: Insights and "business recommendations" are illustrative, not real business findings — but they are still computed from the actual generated numbers (via SQL/Python queries), not hand-written, so the *mechanism* is real even though the underlying facts are synthetic.

### Decision: Database — PostgreSQL via Docker
**Choice**: Run Postgres 16 in a Docker container (`docker-compose.yml`), rather than SQLite/DuckDB or a native Postgres install.
**Why**: The user explicitly chose this to match the PDF's spec exactly, over the zero-setup alternatives (SQLite, DuckDB) that were offered as easier options given Postgres wasn't already installed.
**Trade-off accepted**: This introduces a runtime dependency — Docker Desktop must be running for the database layer to work. Docker Desktop was launched in the background immediately after this decision so it has time to boot before it's needed in the pipeline (step 4 of the build).

### Decision: Dashboard — both a working web app and a Power BI asset bundle
**Choice**: Build a fully working, self-tested Streamlit + Plotly dashboard as the primary deliverable, **and** export a Power BI–ready star schema plus a complete DAX measure library and build guide as a bonus.
**Why**: Power BI Desktop isn't installed and its file format can't be produced or verified by Claude Code at all — building *only* a Power BI deliverable would mean shipping something never actually run or tested. The web app is real, working, and independently verifiable (I can start it and check it serves data). The Power BI assets still deliver full portfolio/resume value (`.pbix` is standard for BI analyst roles) — the user assembles it visually using the provided guide.
**Trade-off accepted**: The user has to do the final Power BI assembly step by hand; I cannot verify the finished `.pbix` looks correct.

### Decision: Data scale — small demo
**Choice**: ~2,000 customers, ~5,000 orders, ~150 products, ~15,000 website sessions, 1 year of history — rather than the PDF's example scale (~80,000 orders, ~30,000 customers, 2 years).
**Why**: User chose the faster-to-generate/query/iterate option. At this scale every SQL query, notebook, and dashboard load runs quickly, which matters because the entire pipeline gets re-run multiple times during development and verification.
**Trade-off accepted**: Numbers shown in the final dashboard will be smaller/less "impressive" than the PDF's mockup figures — this is cosmetic and doesn't affect what skills are demonstrated.

### Decision: Git strategy — milestone commits
**Choice**: `git init` now, with a commit at the end of each major build stage (schema, cleaning, SQL, RFM/churn, forecasting, dashboard, Power BI export, insights/docs).
**Why**: Produces a reviewable, portfolio-style commit history showing the build progression, which the user can point to as evidence of process, not just a final-state dump.

### Decision: Decisions documentation format — Markdown only
**Choice**: This file (`reports/decisions_log.md`), plain Markdown, no binary PDF export.
**Why**: The user explicitly chose Markdown-only over generating an actual `.pdf` file. Markdown is git-diffable (each append shows as a clean diff) and requires no extra library (e.g. fpdf2/reportlab) to maintain live throughout the build.

### Decision: Forecasting — included as an opt-in module
**Choice**: Build `src/forecasting.py` + a forecasting notebook (moving average + exponential smoothing on monthly revenue).
**Why**: The PDF explicitly frames forecasting as optional/advanced and *not* the foundation of the project — it recommends adding it only once the core system works. The user opted in anyway. To honor the PDF's own caution, forecasting is kept as an isolated module that depends on the core pipeline's output but that the core pipeline does not depend on — if forecasting were skipped or broken, everything else still stands alone.

### Decision: Python environment — venv + requirements.txt
**Choice**: Standard library `venv` and a pinned `requirements.txt`, over Poetry.
**Why**: `venv` ships with the already-installed Python 3.13; Poetry would be an extra tool to install first for no benefit at this project's size.

### Decision: Repository structure
**Choice**: A flat, purpose-named top-level layout (`data/`, `src/`, `sql/`, `notebooks/`, `dashboard/`, `powerbi/`, `reports/`) rather than nesting everything under a single `ecommerce-business-analytics/` folder as the PDF's example tree shows.
**Why**: The working directory (`CommerceIQ`) already *is* the project root, so an extra nested folder would be redundant. Naming otherwise follows the PDF's suggested structure closely (SQL files numbered by analysis domain, notebooks numbered by pipeline stage, etc.).

---

*(Further entries are appended below as each build stage completes, in particular: exact row counts and every data-quality issue found/fixed during cleaning, why each SQL technique was chosen where it was, model choices in forecasting, and any deviations from this initial plan.)*

---

## 2026-08-21 — Data cleaning (automated report from `src/clean_data.py`)
Cleaning CommerceIQ raw data...

## 2026-08-21 — Forecasting module: excluding partial months

While building `src/forecasting.py` (optional module, RFM/churn/SQL do not depend on it), the first Holt
linear-trend forecast came out oddly high (₹6.9-7.2M vs. a ₹5.5M moving-average baseline). Root cause: the
1-year history window (`TODAY - 365 days` to `TODAY`) starts and ends mid-month, so both the first bucketed
month (2025-08, ~11 days of data) and the last (2026-08, ~21 days of data) are partial months with
artificially low revenue — the trend model was reacting to two fake dips at each end of the series.

**Fix**: `get_monthly_revenue()` now drops both the first and last monthly bucket when they correspond to
the known partial-month boundaries, before fitting. Re-run result: forecast (₹5.72-5.74M) now sits close to
the moving-average baseline (₹5.85M), which is the expected sanity-check relationship for a low-trend series
— confirms the fix, not just a difference.

**Also observed**: `ExponentialSmoothing` raised a `ConvergenceWarning` on this ~11-point series even after
the fix — expected at this sample size (the optimizer's tolerance isn't reliably reachable with so few
points) and the resulting parameters were still stable/sane, so the warning is caught and suppressed locally
in `forecast_holt()` rather than treated as an error or silenced globally.

---

### customers
- Raw row count: 2015
- Removed 15 exact duplicate rows
- Normalized inconsistent state casing/spelling (e.g. 'TAMILNADU' -> 'Tamil Nadu')
- Filled 20 missing city values with 'Unknown'
- Treated 6 impossible age values as missing; imputed all 46 missing ages (incl. those outliers) with the median age (33)
- Cleaned row count: 2000

### products
- Raw row count: 150
- Removed 0 exact duplicate rows
- Standardized category text: 15 distinct raw spellings -> 6 canonical categories
- Filled 4 missing brand values with 'Unknown'
- Cleaned row count: 150

### orders
- Raw row count: 5020
- Removed 20 exact duplicate rows
- Fixed 8 negative quantity values (took absolute value)
- Dropped 5 rows with invalid/unparseable order_date
- Dropped 4 rows with an order customer_id not present in customers
- Dropped 4 rows with an order product_id not present in products
- Cleaned row count: 4987

### payments
- Raw row count: 5020
- Dropped 13 rows referencing an order_id no longer present after order cleaning
- Recomputed 50 missing amount values from order price x qty x (1-discount); dropped 0 rows that still couldn't be recomputed
- Cleaned row count: 5007

### returns
- Raw row count: 298
- Dropped 1 rows referencing an order_id no longer present after order cleaning
- Fixed 3 negative refund_amount values (took absolute value)
- Cleaned row count: 297

### marketing_campaigns
- Raw row count: 24
- No injected issues; parsed dates and passed through unchanged
- Cleaned row count: 24

### website_sessions
- Raw row count: 15000
- Filled 150 missing device values with 'Unknown'
- Dropped 0 rows with a non-null customer_id not present in customers (null customer_id = anonymous session, kept as valid)
- Cleaned row count: 15000

All cleaned tables written to data/cleaned/.
