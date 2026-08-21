"""
Runs real queries against the loaded database and writes
reports/business_insights.md in the PDF's Finding/Recommendation format.

Every number below comes from the actual (synthetic) dataset via SQL/pandas
- nothing is hand-written. Run this last, after every other module.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_FILE = BASE_DIR / "reports" / "business_insights.md"


def finding_category_margin(engine) -> str:
    df = pd.read_sql(
        """
        SELECT p.category,
               SUM(o.quantity * p.selling_price * (1 - o.discount)) AS revenue,
               SUM(o.quantity * p.unit_cost) AS cost
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        WHERE o.order_status <> 'Cancelled'
        GROUP BY p.category
        ORDER BY revenue DESC
        """,
        engine,
    )
    df["margin_pct"] = (df["revenue"] - df["cost"]) / df["revenue"] * 100
    top = df.iloc[0]
    lowest_margin = df.sort_values("margin_pct").iloc[0]
    return (
        f"## Finding 1 — Category revenue vs. margin\n\n"
        f"**{top['category']}** generates the highest revenue (₹{top['revenue']:,.0f}), "
        f"but **{lowest_margin['category']}** has the lowest margin among top categories "
        f"({lowest_margin['margin_pct']:.1f}% vs. category average "
        f"{df['margin_pct'].mean():.1f}%).\n\n"
        f"**Recommendation:** Review discounting depth and supplier cost for "
        f"{lowest_margin['category']} before scaling its marketing spend further.\n"
    )


def finding_at_risk_customers(engine) -> str:
    df = pd.read_sql(
        "SELECT risk_tier, COUNT(*) AS n FROM customer_risk GROUP BY risk_tier", engine
    )
    total = df["n"].sum()
    at_risk = df.loc[df["risk_tier"] == "At Risk", "n"].sum()
    pct = at_risk / total * 100 if total else 0
    return (
        f"## Finding 2 — Retention risk\n\n"
        f"**{pct:.1f}%** of customers ({at_risk:,} of {total:,}) are classified **At Risk** "
        f"(90+ days since last order, 3+ historical orders) — high-value customers going quiet.\n\n"
        f"**Recommendation:** Launch a targeted win-back campaign (e.g. discount code + "
        f"personalized email) aimed specifically at the At Risk segment before they lapse to Lost.\n"
    )


def finding_channel_conversion(engine) -> str:
    df = pd.read_sql(
        """
        SELECT channel,
               COUNT(*) AS sessions,
               SUM(CASE WHEN purchased THEN 1 ELSE 0 END) AS purchases
        FROM website_sessions
        GROUP BY channel
        """,
        engine,
    )
    df["conversion_rate_pct"] = df["purchases"] / df["sessions"] * 100

    # Budget can only be reallocated across channels that actually carry spend -
    # exclude Organic (free/unpaid traffic) from the "shift budget" comparison,
    # even though it's shown below for context.
    paid = df[df["channel"] != "Organic"]
    best_paid = paid.sort_values("conversion_rate_pct", ascending=False).iloc[0]
    highest_traffic = df.sort_values("sessions", ascending=False).iloc[0]
    organic = df[df["channel"] == "Organic"].iloc[0]

    return (
        f"## Finding 3 — Channel efficiency vs. volume\n\n"
        f"Among paid/owned channels, **{best_paid['channel']}** has the highest conversion rate "
        f"({best_paid['conversion_rate_pct']:.2f}%) with {best_paid['sessions']:,} sessions, while "
        f"**{highest_traffic['channel']}** drives the most traffic overall ({highest_traffic['sessions']:,} "
        f"sessions) at a {highest_traffic['conversion_rate_pct']:.2f}% conversion rate. For context, "
        f"**Organic** (unpaid) converts at {organic['conversion_rate_pct']:.2f}%.\n\n"
        f"**Recommendation:** Shift incremental paid budget toward {best_paid['channel']} — it is "
        f"converting more efficiently per session than the highest-traffic paid channel.\n"
    )


def finding_device_checkout(engine) -> str:
    # Excludes device = 'Unknown': that's the ~1% of sessions where the raw
    # device value was missing and filled by the cleaning pipeline (see
    # clean_data.py) - it's a data-quality placeholder, not a real device
    # segment, and shouldn't be reported as if it were one.
    df = pd.read_sql(
        """
        SELECT device,
               SUM(CASE WHEN added_to_cart THEN 1 ELSE 0 END) AS carts,
               SUM(CASE WHEN purchased THEN 1 ELSE 0 END) AS purchases
        FROM website_sessions
        WHERE added_to_cart AND device <> 'Unknown'
        GROUP BY device
        """,
        engine,
    )
    df["checkout_completion_pct"] = df["purchases"] / df["carts"] * 100
    worst = df.sort_values("checkout_completion_pct").iloc[0]
    best = df.sort_values("checkout_completion_pct", ascending=False).iloc[0]
    return (
        f"## Finding 4 — Checkout completion by device\n\n"
        f"**{worst['device']}** has the lowest cart-to-purchase completion rate "
        f"({worst['checkout_completion_pct']:.1f}%) vs. **{best['device']}** at "
        f"{best['checkout_completion_pct']:.1f}%.\n\n"
        f"**Recommendation:** Investigate the {worst['device']} checkout experience "
        f"(form length, payment options, page load) for friction points.\n"
    )


def main():
    engine = get_engine()
    findings = [
        finding_category_margin(engine),
        finding_at_risk_customers(engine),
        finding_channel_conversion(engine),
        finding_device_checkout(engine),
    ]

    header = (
        "# CommerceIQ — Business Insights & Recommendations\n\n"
        f"_Generated {datetime.now():%Y-%m-%d} by `src/generate_insights.py` directly from the "
        "loaded database — every figure below is computed from the actual dataset, not written "
        "by hand._\n\n---\n\n"
    )

    OUT_FILE.write_text(header + "\n---\n\n".join(findings), encoding="utf-8")
    print(f"Business insights written to {OUT_FILE}")


if __name__ == "__main__":
    main()
