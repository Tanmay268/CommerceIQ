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

## 2026-08-21 — `reports/business_insights.md`: two corrections made during generation

`src/generate_insights.py` runs real queries and writes Finding/Recommendation pairs — no numbers are
hand-written — but the first draft output surfaced two things worth catching before calling it done:

1. **Channel recommendation nonsensical for unpaid traffic.** The first version picked whichever channel
   had the single highest session-conversion rate and recommended "shift budget toward it" — which broke
   when that channel was **Organic** (zero marketing spend; there's no budget to shift *toward* free
   traffic). Fixed by splitting the comparison: the budget-shift recommendation now only considers
   paid/owned channels, with Organic shown separately for context.
2. **Data-cleaning artifact leaking into a "finding."** The device-checkout-completion finding was
   initially won by `device = 'Unknown'` — the placeholder `clean_data.py` fills in for the ~1% of
   sessions where the raw device value was missing (see the cleaning report below). Reporting a data-
   quality placeholder as if it were a real device segment would be misleading, so that finding now
   explicitly excludes `Unknown` and compares only real device values.

Also worth being honest about: the corrected device finding ended up with a very small gap (32.0% vs.
32.4%) — the synthetic generator has no deliberate device-driven checkout effect built in, so this
particular finding is closer to noise than signal. It's left in because the pipeline is meant to
demonstrate the *mechanism* (real query → real number → written finding) on a portfolio-scale synthetic
dataset, not to claim a discovered business truth — that caveat applies to every finding in this file,
consistent with the trade-off accepted in the very first decision above.

---

## 2026-08-21 — Project complete: end-to-end verification summary

All 10 build-sequence milestones from the plan are done, each as its own git commit. Final verification
status:

- **Data generation**: 7 CSVs, seeded/reproducible (seed=42), deliberately messy.
- **Cleaning**: every injected issue fixed and logged above with before/after row counts.
- **Database**: Postgres 16 in Docker, schema applied, all 7 tables loaded with row counts verified equal
  to the cleaned CSVs (`load_to_db.py`'s built-in assertion).
- **SQL**: all 31 queries across 5 files execute successfully against the live DB (`run_sql_files.py`).
- **Python analytics**: RFM (1,800 customers scored, 7 segments), rule-based churn/risk (2,000 customers,
  5 tiers), product profitability, forecasting (Holt linear trend, partial-month bug found and fixed
  mid-build — see the forecasting entry above) — all 5 notebooks executed headless with zero exceptions.
- **Dashboard**: Streamlit + Plotly, 4 pages, verified via HTTP smoke test (200 OK on all page routes plus
  `/_stcore/health`, clean server log) — not a visual browser check, since no browser tool was available in
  this environment; the user should still open it and look before considering it fully verified end-to-end.
- **Power BI**: star schema exported + full DAX/build guide written, but **not** independently verified —
  Power BI Desktop isn't installed and `.pbix` can't be produced or tested by Claude Code at all. This is
  the one deliverable in the repo that hasn't been run, only authored against the documented schema.
- **Business insights**: generated from real query results, two issues caught and fixed during generation
  (see above).

**Known limitations, stated plainly:**
- All data is synthetic; findings are illustrative of the *mechanism*, not real business discoveries.
- Marketing ROAS/CAC use a documented proxy attribution model (conversions × overall AOV), because orders
  carry no channel/campaign_id in this schema.
- The Power BI deliverable is guide + data only, not a verified `.pbix`.
- Running the project requires Docker Desktop to be running (Postgres dependency, chosen deliberately over
  zero-setup alternatives to match the source spec exactly).

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

---

## 2026-09-29 — Data cleaning (automated report from `src/clean_data.py`)
Cleaning CommerceIQ raw data...

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

---

## 2026-09-29 — Data cleaning (automated report from `src/clean_data.py`)
Cleaning CommerceIQ raw data...

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

---

## 2026-09-30 — Data cleaning (automated report from `src/clean_data.py`)
Cleaning CommerceIQ raw data...

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

---

## 2026-09-30 — Data cleaning (automated report from `src/clean_data.py`)
Cleaning CommerceIQ raw data...

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
