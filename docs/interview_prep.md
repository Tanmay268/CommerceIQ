# CommerceIQ — Interview Prep

A practice sheet for talking about this project in an interview: a ready
elevator pitch, a longer walkthrough, and anticipated questions with
simple, honest answers. See [`architecture.md`](architecture.md) for
diagrams and [`decisions.md`](decisions.md) for the full reasoning behind
each choice — this file is written to be *said out loud*, not read.

---

## 1. The 30-second elevator pitch

> "CommerceIQ is an end-to-end e-commerce analytics platform I built
> solo — synthetic data generation, data cleaning, a PostgreSQL database,
> 31 SQL analysis queries using joins and window functions, Python-based
> customer segmentation and churn scoring, a revenue forecast, and a
> 4-page interactive Streamlit dashboard, plus a Power BI star schema as a
> bonus deliverable. Every decision I made — why Postgres over SQLite, why
> rule-based churn scoring instead of ML, how I handled a bug in my
> forecasting model — is documented with reasoning, not just the final
> code. It's meant to demonstrate the full analytics pipeline a Data
> Analyst or BI role actually touches, not just a polished dashboard
> screenshot."

---

## 2. The 2-minute walkthrough (STAR-style)

**Situation:** I wanted a portfolio project that proved I could work
across the whole analytics stack — not just write SQL queries in
isolation, but actually own data from raw generation through to a
stakeholder-facing dashboard.

**Task:** Build something that mirrors a real e-commerce BI platform:
sales, customers, products, marketing, and profitability — answering not
just "what happened" but "why, and what should we do about it."

**Action:**
1. I generated a realistic, seeded synthetic dataset — 7 tables, about
   2,000 customers and 5,000 orders — deliberately injecting messy data
   (duplicates, bad dates, missing values) so I'd have a real cleaning
   problem to solve, not a toy one.
2. I cleaned it with pandas, logging every single fix with before/after
   row counts, so the cleaning step is fully auditable.
3. I loaded it into PostgreSQL running in Docker, with a schema built
   around clear primary/foreign key relationships.
4. I wrote 31 SQL queries across 5 business domains, deliberately using
   CTEs, window functions (`LAG`, `RANK`, `NTILE`, running totals), and
   `FILTER` clauses to demonstrate real SQL fluency, not just `SELECT *`.
5. I built customer segmentation (RFM) and a rule-based churn risk score
   in Python, plus a revenue forecast using Holt linear trend smoothing.
6. I built a 4-page Streamlit dashboard with shared, synchronized filters
   across every page, and separately exported a Power BI star schema with
   a full DAX measure library.
7. I deployed the dashboard live, against a hosted Postgres database.

**Result:** A working, end-to-end system I can demo live, where every
number in the dashboard traces back to a real query against real
(synthetic) data — and a documented decision trail explaining every
architectural choice along the way, including a couple of bugs I found
and fixed mid-build.

---

## 3. Quick facts cheat-sheet

| Fact | Value |
|---|---|
| Tables | 10 (7 source + `customer_rfm` + `customer_risk` + `monthly_revenue_forecast`) |
| Customers | ~2,000 |
| Orders | ~5,000 |
| Products | 150, across 6 categories |
| Website sessions | ~15,000 |
| History window | 1 year |
| SQL queries | 31, across 5 domain files |
| RFM segments | 7 (Champions, Loyal Customers, Potential Loyalists, New Customers, At Risk, Can't Lose Them, Lost Customers) |
| Churn/risk tiers | 5 (Active, Watch, At Risk, Lost, Never Purchased) |
| Dashboard pages | 4 (Executive, Customer Analytics, Product Analytics, Marketing & Funnel) |
| Forecast method | Holt linear trend exponential smoothing (statsmodels) |
| Database | PostgreSQL 16, via Docker locally / hosted Postgres (Neon/Supabase) in production |
| Dashboard stack | Streamlit + Plotly |
| Seed | 42 (fully reproducible generation) |

---

## 4. Technical Q&A

### General / project-level

**Q: Why did you build this project?**
> To demonstrate the full analytics lifecycle end-to-end, not just isolated
> SQL puzzles — from messy raw data to a stakeholder-ready dashboard,
> including the judgment calls in between (what to clean, how to segment
> customers, how to be honest about a proxy metric's limitations).

**Q: Why synthetic data instead of a real dataset?**
> No real dataset was available or appropriate for the scope I wanted.
> A seeded generator let me control the schema exactly and deliberately
> inject data-quality problems, so the cleaning step had something real to
> solve rather than starting from already-clean data. I'm upfront that the
> "insights" are illustrative of the *method*, not real discovered
> business facts — the mechanism (real query → real number → written
> finding) is real, even though the underlying data is synthetic.

**Q: What was the hardest part?**
> Getting the revenue forecast right. My first Holt linear-trend forecast
> came out ₹6.9-7.2M against a ₹5.5M moving-average baseline — clearly
> wrong. I traced it to my history window starting and ending mid-month,
> so the first and last monthly revenue buckets were partial months that
> looked like fake dips to the trend model. Once I excluded both partial
> buckets before fitting, the forecast landed at ₹5.72-5.74M, right next
> to the ₹5.85M baseline — which is the sanity-check relationship you'd
> expect for a low-trend series, so I could tell the fix actually worked
> rather than just producing a different wrong number.

**Q: What would you do differently / improve next?**
> Three things: (1) move dashboard filtering from in-memory pandas to SQL
> `WHERE` clauses if the data volume grew significantly; (2) replace the
> rule-based churn score with a trained model once there's enough real
> historical churn outcomes to validate one against; (3) get real
> order-level campaign attribution (UTM tracking / campaign IDs on orders)
> instead of the proxy ROAS/CAC calculation I had to use.

---

### SQL

**Q: What SQL techniques did you use, and why?**
> CTEs to break complex queries into readable steps, window functions for
> anything that needs to compare a row to other rows (`LAG` for
> month-over-month revenue growth, `RANK` for top customers by revenue,
> `NTILE(5)` for RFM quintile scoring, `SUM() OVER` for a running revenue
> total, `AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` for a
> 3-month moving average), and `FILTER (WHERE ...)` for building a cohort
> retention heatmap without repeating the same `CASE WHEN` five times.

**Q: Walk me through one non-trivial query.**
> The cohort retention query: I first build a `cohort` CTE that assigns
> each customer to their signup month, then an `orders_m` CTE with the
> distinct months each customer actually ordered in, then I compute a
> `month_offset` — how many months after signup each order happened — and
> finally pivot that into a wide table with one column per offset using
> `MAX(...) FILTER (WHERE month_offset = N)`. It answers "of customers who
> signed up in month X, what % were still ordering N months later" —
> classic cohort retention, done in pure SQL.

**Q: Why do the same RFM metrics appear in both SQL and Python?**
> The metrics themselves (recency/frequency/monetary quintiles) are
> naturally set-based, so I show them in SQL using `NTILE(5)` to prove I
> can do it that way. But the actual segment used by the dashboard is
> computed in pandas, because mapping score combinations to named segments
> (e.g. "recency≥4 AND frequency≥4 AND monetary≥4 → Champions") is a
> readable `if/elif` chain in Python, and would be an unreadable mess of
> nested `CASE WHEN` in SQL. Using the right tool for each half of the
> problem.

**Q: How would you optimize these queries at scale?**
> I already added indexes on the foreign key and filter columns that get
> hit most (`orders.customer_id`, `orders.product_id`, `orders.order_date`,
> `website_sessions.channel`, etc. — see `sql/00_schema.sql`). At real
> scale I'd also look at materializing the RFM/churn aggregate tables on a
> schedule (they already are, as `customer_rfm`/`customer_risk`, rather
> than computed live) and possibly partitioning `orders` by month.

---

### Python / pandas / analytics

**Q: Explain your RFM segmentation logic.**
> For each customer: Recency = days since their last order, Frequency =
> total order count, Monetary = total revenue. Each metric gets scored
> 1-5 using quintiles (`pd.qcut`) — recency is inverted, since *fewer*
> days since last order is *better*, so it gets score 5. Then I map score
> combinations to 7 named segments using explicit business rules — e.g.
> high scores on all three dimensions is "Champions"; high recency and
> frequency but low monetary is different from high everything, etc.

**Q: Why rule-based churn scoring instead of a machine learning model?**
> Two reasons. First, the brief was explicit that for a data-analytics
> role, SQL/analytics/BI should be the core focus, with ML as a possible
> future extension, not the foundation — so I kept it in scope. Second,
> and more practically: a rule I can explain to a business stakeholder in
> one sentence ("90+ days since last order and at least 3 past orders
> means At Risk") is something they can act on and trust immediately. A
> black-box model would need way more historical churn-outcome data than
> a synthetic one-year dataset actually has to be trained and validated
> properly — on this data volume, an ML model would mostly be fitting
> noise, not signal.

**Q: Why Holt linear trend instead of a seasonal model like Prophet or
SARIMA?**
> With only about 11-12 months of usable history, there isn't enough data
> to reliably detect a seasonal pattern — a seasonal model would overfit.
> Trend-only exponential smoothing is the more honest choice at this data
> volume; I'd revisit that decision if I had 2+ years of history to work
> with.

**Q: What data quality issues did you handle, and how?**
> Duplicate rows (dropped exact duplicates), inconsistent text casing
> (e.g. "TAMILNADU" vs "Tamil Nadu" — normalized via a lookup table),
> missing values (filled sensibly — median age for missing ages, "Unknown"
> for missing city/brand/device), invalid data (negative quantities → took
> absolute value; unparseable dates → dropped, since a fabricated date
> would be worse than no row), and orphan foreign keys (an order
> referencing a customer or product ID that doesn't exist → dropped, since
> there's nothing legitimate to attach it to). Every fix is counted and
> logged, nothing is silent.

**Q: How do you know your cleaning was correct?**
> Because I injected the issues myself with known counts, I could verify
> the cleaner found exactly what I expected — e.g. I injected exactly 15
> duplicate customer rows and 6 impossible age outliers, and the cleaning
> report confirms exactly those counts were caught and fixed.

---

### Database / schema design

**Q: Why PostgreSQL instead of MySQL or SQLite?**
> Postgres is what most real analytics/BI teams actually run in
> production, so it's the more relevant skill to demonstrate. I ran it in
> Docker rather than installing it natively, so the whole database layer
> is disposable and reproducible — anyone cloning the repo gets the exact
> same environment with `docker compose up -d`.

**Q: Walk me through your schema design.**
> Seven source tables mirror what a real e-commerce platform exports:
> customers, products, orders (the fact table everything else hangs off
> of), payments, returns, marketing_campaigns, and website_sessions. Three
> more tables — `customer_rfm`, `customer_risk`, and
> `monthly_revenue_forecast` — get populated later by the Python analytics
> modules, not by the raw data load. I added indexes on every foreign key
> and every column that shows up in a `WHERE`/`GROUP BY` in my 31 queries.

**Q: Why isn't `orders` linked to `marketing_campaigns` or
`website_sessions`?**
> Because there's no `campaign_id` or `channel` column on `orders` in this
> schema — which mirrors a very real limitation many e-commerce platforms
> actually have: you often can't cleanly attribute a specific order to a
> specific ad click. Rather than fabricate a join key that doesn't really
> exist, I built channel-level ROAS/CAC as an explicitly-labeled proxy
> metric (conversions × average order value) and said so everywhere it
> shows up — in code comments, the DAX guide, and the insights report.
> I'd rather show I understand the limitation than hide it behind a fake
> precise number.

---

### Dashboard / BI

**Q: Why Streamlit instead of Power BI or Tableau as the primary
deliverable?**
> Power BI Desktop wasn't available in my build environment, and `.pbix`
> is a closed binary format I can't produce or test programmatically at
> all — a hard limitation, not a preference. Streamlit let me build
> something I could actually run, test, and verify end-to-end (I checked
> every page returns 200 OK and renders real data), so it became the
> primary, verified deliverable. I still built the Power BI star schema
> and a full DAX measure guide as a bonus deliverable, since `.pbix` is
> the expected format for a lot of BI-analyst roles — I just can't verify
> the final assembled file myself.

**Q: How does filtering work across your 4 dashboard pages?**
> All four pages import the same `render_sidebar_filters()` and
> `apply_sales_filters()` functions from one shared `data_loader.py`
> module, so a filter selected on one page behaves identically if you
> switch to another page — there's exactly one filtering implementation,
> not four slightly-different copies.

**Q: How does your dashboard perform, and how would that change at
scale?**
> Each page's queries are cached for 5 minutes with `st.cache_data`, so I
> pull each full table from Postgres once and filter it in memory with
> pandas rather than re-querying on every filter change. That's fine at a
> few thousand rows. At real production scale I'd push filtering down into
> SQL `WHERE` clauses and add pagination instead of loading full tables
> into memory.

**Q: How did you deploy it?**
> Streamlit Community Cloud, pointed at a hosted Postgres instance (Neon
> or Supabase), since there's no Docker on Community Cloud. My `db.py`
> helper reads `st.secrets` when running under Streamlit and falls back to
> `.env` locally, so the exact same code runs unmodified in both places —
> only where the connection string comes from changes.

---

### Business / soft-skill angle

**Q: What's one specific business insight you generated?**
> My insights generator found that one product category had the highest
> raw revenue but the lowest profit margin among the top categories — the
> recommendation was to review discounting depth and supplier cost there
> before scaling its marketing spend further, since growing an
> already-low-margin category makes the problem bigger, not smaller. Every
> number in that finding comes from a live SQL query against the loaded
> database, not from me typing plausible-sounding numbers.

**Q: Tell me about a mistake you caught in your own analysis.**
> My first version of the "best marketing channel" recommendation picked
> whichever channel had the highest session-conversion rate and
> recommended shifting budget toward it — which broke completely when that
> channel turned out to be Organic (free, unpaid traffic). You can't shift
> *budget* toward a channel that has no budget. I fixed it by splitting
> the comparison: the budget-shift recommendation now only considers
> paid/owned channels, with Organic shown separately for context. It's a
> small thing, but it's the kind of logic error that's easy to ship if you
> don't sanity-check what a recommendation is actually asking a
> stakeholder to do.

**Q: How do you make sure your dashboard doesn't mislead people?**
> A concrete example: about 1% of website sessions had a missing `device`
> value, which my cleaning step fills in as `"Unknown"` so the row isn't
> lost. My first draft of a "checkout completion by device" finding was
> initially won by `device = 'Unknown'` — which would have reported a
> data-cleaning placeholder as if it were a real device segment. I caught
> it and excluded `Unknown` from that specific comparison. The lesson I'd
> generalize: know which of your columns are real signal versus a cleanup
> artifact, and don't let cleanup artifacts win a "finding."

---

## 5. Questions to ask the interviewer (optional, if it fits the flow)

- "What does your team's data quality/cleaning process look like today —
  is it as explicit/logged as what I did here, or more ad hoc?"
- "How does your team currently handle marketing attribution — do you have
  order-level campaign tracking, or is it also a proxy/estimate?"
- "Is your BI delivery primarily Power BI, or is there appetite for
  lighter-weight tools like Streamlit for faster internal iteration?"

---

## 6. Things to say plainly if asked directly (don't oversell)

- The dataset is synthetic — be upfront immediately if asked, don't wait
  to be caught.
- The Power BI `.pbix` file itself was never opened/verified by me — only
  the exported CSVs and the DAX guide were built and checked against the
  documented schema.
- Marketing ROAS/CAC are a proxy, not true attributed revenue, because the
  schema has no order-level campaign ID.
- The churn/risk model is rule-based by design, not because ML wasn't
  considered.
