# CommerceIQ — Decisions

This is a curated, organized explanation of **every meaningful choice** made
while building CommerceIQ, and *why* it was made that way. Each entry
follows the same shape: **Decision → Why → Alternatives considered →
Trade-off accepted.**

This file is the readable, grouped-by-topic version. The full raw,
chronological, timestamped build log (including the exact data-cleaning
reports with row counts) lives in
[`reports/decisions_log.md`](reports/decisions_log.md) — read that if you
want the blow-by-blow history. Read *this* file if you want to understand
the reasoning quickly, e.g. before an interview or a code review.

---

## 1. Data & scope decisions

### 1.1 Use fully synthetic data
**Decision:** Generate an entire fake-but-realistic e-commerce dataset with
a seeded Python script, rather than use a real dataset.

**Why:** No real dataset was available. Building a working, end-to-end
system (schema → cleaning → SQL → dashboard) requires *some* data to flow
through it, and a generator was the only path that didn't depend on
finding/licensing a suitable public dataset.

**Alternatives considered:** Using a public Kaggle e-commerce dataset.
Rejected because public datasets rarely match the exact schema/scenario
needed (Indian e-commerce context, specific KPI columns, deliberately
messy data for a cleaning step to fix) — shaping one dataset from scratch
was more controllable.

**Trade-off accepted:** Every "business insight" in this project is
illustrative of *how* the analysis is done, not a real discovered business
truth. This is stated plainly everywhere insights are shown, rather than
implied to be real findings.

---

### 1.2 Small data scale (~2,000 customers, ~5,000 orders)
**Decision:** Generate roughly 2,000 customers, 150 products, 5,000
orders, and 15,000 website sessions over 1 year — a small, fast-to-iterate
scale, not a "look how big this is" scale.

**Why:** At this size, every SQL query, notebook cell, and dashboard page
load runs in well under a second, which matters because the whole pipeline
gets re-run repeatedly during development, and the dashboard needs to feel
snappy in a portfolio demo.

**Alternatives considered:** A much larger dataset (~30,000 customers,
~80,000 orders) to look more "production-scale."

**Trade-off accepted:** The final numbers shown (revenue totals, etc.) look
smaller/less impressive than a big-company dashboard. This is purely
cosmetic — it doesn't change which skills the project demonstrates (SQL
joins/window functions, pandas segmentation logic, dashboard design all
work identically at any scale).

---

### 1.3 Deliberately inject messy data
**Decision:** `generate_data.py` intentionally creates duplicate rows,
inconsistent text casing, missing values, invalid dates, negative numbers,
and orphan foreign keys — then `clean_data.py` has to find and fix all of
them.

**Why:** Real e-commerce exports are never clean. A project that only ever
sees perfect data can't demonstrate real data-cleaning skill. Injecting
known, deliberate issues means the cleaning step can be verified against a
known-correct answer.

**Trade-off accepted:** None significant — this only adds value, since the
"messiness" is fully controlled and doesn't risk the pipeline breaking in
unpredictable ways.

---

## 2. Database & infrastructure decisions

### 2.1 PostgreSQL via Docker (not SQLite/DuckDB, not a native install)
**Decision:** Run Postgres 16 inside a Docker container via
`docker-compose.yml`.

**Why:** Postgres is what most real-world analytics/BI roles actually use
in production, and demonstrating comfort with a real client-server
relational database (not a local file-based DB) has more portfolio value.
Docker was chosen over a native Postgres install because it's disposable,
reproducible, and doesn't touch the host machine's global state.

**Alternatives considered:** SQLite or DuckDB — genuinely easier (zero
setup, no daemon to run), and were explicitly offered as options. Rejected
in favor of matching the target skill set exactly.

**Trade-off accepted:** Docker Desktop must be running before the pipeline
or dashboard can connect to the database — a real runtime dependency that
SQLite/DuckDB wouldn't have had.

---

### 2.2 One shared `db.py` connection helper
**Decision:** All database access — pipeline scripts and the dashboard —
goes through a single `get_engine()` / `get_database_url()` helper in
`src/db.py`.

**Why:** Connection logic (how to build the connection string, where
credentials come from) needs to differ between local development (`.env`
+ Docker) and cloud deployment (Streamlit `st.secrets` + hosted Postgres).
Centralizing it in one place means every script and every dashboard page
automatically works in both environments without being aware of the
difference.

**Trade-off accepted:** None — this is a straightforward DRY (don't repeat
yourself) win with no real downside at this project's size.

---

### 2.3 Schema recreated from scratch on every load (`DROP TABLE ... CASCADE`)
**Decision:** `00_schema.sql` starts by dropping every table (if it
exists) before recreating it, and `load_to_db.py` always runs the full
schema file before loading data.

**Why:** Makes the pipeline idempotent — running `run_all.py` twice in a
row produces the exact same database state both times, with no leftover
or duplicated rows to reason about.

**Alternatives considered:** Incremental migrations (only apply schema
changes since last run). Rejected as unnecessary complexity for a project
where the whole pipeline is meant to be re-runnable from zero at any time.

**Trade-off accepted:** This would be unacceptable in a real production
system with live, irreplaceable data — dropping tables is a destructive
operation. It's safe here only because the entire dataset is regenerable
synthetic data.

---

## 3. Analytics approach decisions

### 3.1 RFM segmentation done in Python/pandas, not pure SQL
**Decision:** `src/rfm.py` computes RFM scores and maps them to named
segments (Champions, At Risk, etc.) using pandas — even though the exact
same metric is also demonstrated in pure SQL (`sql/05_advanced_analysis.sql`,
using `NTILE()` window functions).

**Why:** The RFM *metrics* (recency/frequency/monetary, quintile scoring)
are naturally set-based and SQL does them well. But the *score-to-segment
mapping* (e.g. "r≥4 and f≥4 and m≥4 → Champions") is a chain of business
rules, which reads far more clearly as an `if/elif` chain in Python than
as nested `CASE WHEN` SQL. Using the right tool for each half of the
problem, rather than forcing one language to do both.

**Trade-off accepted:** The "real" segmentation the dashboard uses lives
in two places conceptually (SQL computes the same numbers separately, for
demonstration) — a minor duplication, clearly commented in the SQL file so
it's not mistaken for the dashboard's actual data source.

---

### 3.2 Rule-based churn/risk scoring, not machine learning
**Decision:** `src/churn.py` classifies every customer into a risk tier
using simple, explicit rules based on days-since-last-order and total
order count — no ML model.

**Why:** For a data-analytics-focused portfolio project, the priority is
demonstrating SQL/analytics/BI fluency, with ML explicitly framed as a
possible *future* extension rather than the foundation. A rule-based
system is also something you can explain to a business stakeholder in one
sentence and they'll trust it — a property real churn-prevention teams
value highly, since a black-box model they don't understand is hard to act
on.

**Alternatives considered:** A logistic regression or gradient-boosted
classifier trained on customer features. Considered but deliberately
deferred — it would add real value on a larger dataset with true churn
labels, but on this synthetic scale it would mostly be fitting noise.

**Trade-off accepted:** The risk tiers are less precise than a trained
model could be, and don't adapt automatically as customer behavior
patterns shift over time — someone would need to manually revisit the
thresholds (90 days, 180 days, 3+ orders) periodically.

---

### 3.3 Forecasting: Holt linear trend, kept as an optional, isolated module
**Decision:** `src/forecasting.py` forecasts monthly revenue using Holt's
linear-trend exponential smoothing (not a seasonal model like SARIMA or
Prophet), and is structured so nothing else in the pipeline depends on it.

**Why (method):** With only ~11-12 months of usable history, there isn't
enough data to reliably detect a seasonal pattern — fitting a seasonal
model on that little data would mean fitting noise, not signal.
Trend-only smoothing is the more honest choice at this data volume.

**Why (isolation):** Forecasting was explicitly framed as an optional,
advanced add-on to the core project. To respect that, `forecasting.py`
reads from the core pipeline's output and writes to its own table, but no
other module (RFM, churn, SQL, dashboard core pages) depends on it — if it
were removed or broke, everything else would keep working.

**Bug found and fixed during build:** The first forecast came out
oddly high (₹6.9-7.2M vs. a ₹5.5M moving-average baseline). Root cause:
the 1-year history window starts and ends mid-month, so the first and last
monthly buckets were *partial* months with artificially low revenue — the
trend model was reacting to two fake dips at the edges of the series.
**Fix:** exclude both partial-month buckets before fitting. Result: the
forecast (₹5.72-5.74M) landed close to the moving-average baseline
(₹5.85M) — the expected relationship for a low-trend series, confirming
the fix rather than just producing a different number.

**Trade-off accepted:** `ExponentialSmoothing` still raises a
`ConvergenceWarning` on this short series even after the fix — expected
behavior at this sample size (not enough points for the optimizer to
reliably confirm convergence within tolerance). The warning is caught and
suppressed locally in `forecast_holt()`, not silenced globally, so it
stays visible if it ever shows up somewhere it shouldn't.

---

### 3.4 Marketing attribution: documented proxy model, not fabricated precision
**Decision:** Because `orders` has no `campaign_id` or `channel` column
(matching the source spec's own schema), channel-level ROAS and CAC are
computed as a **proxy**: `conversions × overall average order value`, not
true order-level attributed revenue.

**Why:** Building a fake join key just to make the numbers look more
precise would be actively misleading — it would imply a level of tracking
precision the underlying data doesn't have. Being explicit about the
limitation (in code comments, the Power BI DAX guide, and the business
insights report) is more valuable than hiding it, both technically (it's
the honest analysis) and as an interview talking point (it shows awareness
of a real, common BI limitation).

**Trade-off accepted:** Channel comparisons in the dashboard/Power BI are
directional, not exact — acceptable for a portfolio project, but would
need real attribution data (UTM tracking, order-level campaign IDs) in a
production system.

---

## 4. Dashboard & delivery decisions

### 4.1 Build a real, working Streamlit dashboard *and* a Power BI export
**Decision:** Ship two deliverables — a fully working, self-tested
Streamlit + Plotly web app (the primary deliverable) and a Power BI–ready
star schema + complete DAX measure guide (a bonus deliverable that
requires manual assembly).

**Why:** Power BI Desktop wasn't available in the build environment, and
`.pbix` is a closed binary format with no CLI or API — it's a hard
capability limit, not a preference. Building *only* a Power BI deliverable
would mean shipping something that was never actually run or verified. The
Streamlit app is real, working, and independently testable (it can be
started and checked to actually serve data). The Power BI assets still
carry full portfolio value for BI-analyst-track roles, where `.pbix` is
the expected format — the user does the final visual assembly using the
provided guide.

**Trade-off accepted:** The Power BI deliverable requires a manual step
from the user, and the finished `.pbix` can't be independently verified —
this is stated plainly as a known limitation rather than glossed over.

---

### 4.2 One shared `data_loader.py`, filters applied client-side in pandas
**Decision:** All four dashboard pages call the same cached loader
functions and the same filter-application functions from
`dashboard/data_loader.py`, rather than each page running its own queries.

**Why:** This guarantees filter consistency — a filter chosen on one page
behaves identically when the user switches to another page — and avoids
duplicating query logic four times. At this data volume (a few thousand
rows), pulling each full table once (cached 5 minutes) and filtering
in-memory with pandas is simpler and fast enough, versus re-querying
Postgres on every filter change.

**Trade-off accepted:** This wouldn't scale to a much larger dataset —
at real production volume, filtering should be pushed down into SQL
`WHERE` clauses instead of pulled into memory. This is a deliberate,
scale-appropriate choice, not an oversight (see `decisions.md §6.2` below
for how this would change).

---

## 5. Process & tooling decisions

### 5.1 `venv` + pinned `requirements.txt`, not Poetry
**Decision:** Use the Python standard library's `venv` module and a
version-pinned `requirements.txt`.

**Why:** `venv` ships with the already-installed Python — no extra tool to
install first. Poetry adds dependency-resolution and packaging features
this project doesn't need at its size (it's not published as a package).

---

### 5.2 Git strategy: one commit per build milestone
**Decision:** Commit at the end of each major build stage (schema,
cleaning, SQL, RFM/churn, forecasting, dashboard, Power BI export,
insights/docs) rather than one large final commit.

**Why:** Produces a reviewable, portfolio-style commit history that shows
the build progression as evidence of process — useful both for a
technical reviewer and as a way to point to "here's how I built this
piece by piece" in an interview.

---

### 5.3 Decisions log kept as plain Markdown, auto-appended
**Decision:** `reports/decisions_log.md` is plain Markdown, git-diffable,
and `clean_data.py` programmatically appends its cleaning report to it on
every run (rather than, say, generating a PDF).

**Why:** Markdown requires no extra library to write to, and every append
shows up as a clean, reviewable diff in git history — the cleaning report
becomes part of the auditable build history automatically, not a
separately-maintained document that can drift out of sync with the code.

---

### 5.4 Flat top-level repo structure
**Decision:** Top-level folders are purpose-named directly
(`data/`, `src/`, `sql/`, `notebooks/`, `dashboard/`, `powerbi/`,
`reports/`) rather than nested one level deeper under a project-name
folder.

**Why:** The repository root already *is* the project — an extra nesting
level would be redundant. Folder and file naming otherwise follows
domain-based conventions closely (SQL files numbered by analysis domain,
notebooks numbered by pipeline stage).

---

## 6. What would change at real production scale

Worth stating explicitly, since a few decisions above were deliberately
scale-appropriate rather than "the most scalable possible choice":

1. **Dashboard filtering** would move from in-memory pandas filtering to
   SQL `WHERE` clauses with server-side pagination once row counts get
   into the millions.
2. **Churn scoring** would likely move from fixed rule thresholds to a
   trained model once there's enough real historical churn data to train
   and validate one.
3. **Marketing attribution** would need real order-level campaign/UTM
   tracking to replace the proxy ROAS/CAC calculation with true attributed
   revenue.
4. **The database** would move off Docker-on-one-machine to a managed,
   backed-up, access-controlled Postgres instance with read replicas for
   the dashboard's read-heavy query pattern.
5. **Re-running the full pipeline from empty** (via `DROP TABLE`) would no
   longer be acceptable — real production data isn't regenerable, so
   migrations would need to become incremental and additive.
