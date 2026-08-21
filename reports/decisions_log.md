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
