"""
RFM (Recency / Frequency / Monetary) customer segmentation.

Reads orders + customers from Postgres, computes RFM metrics per customer,
scores each dimension into quintiles (1-5) via pd.qcut, maps the score
combination to a business segment (Champions, Loyal Customers, Potential
Loyalists, New Customers, At Risk, Can't Lose Them, Lost Customers), and
writes the result to the customer_rfm table.

This mirrors the PDF's "most important feature" (section 11) and is kept
in pandas (not raw SQL) so the score-to-segment mapping logic - which is
business-rule-heavy, not set-based - stays readable.
"""

from datetime import date

import pandas as pd
from sqlalchemy import text

from db import get_engine

ANALYSIS_DATE = date(2026, 8, 21)  # "today" for the synthetic dataset


def compute_rfm(engine) -> pd.DataFrame:
    orders = pd.read_sql(
        """
        SELECT customer_id, order_date, quantity, discount,
               quantity * (SELECT selling_price FROM products p WHERE p.product_id = o.product_id) * (1 - discount) AS revenue
        FROM orders o
        WHERE order_status <> 'Cancelled'
        """,
        engine,
    )
    orders["order_date"] = pd.to_datetime(orders["order_date"])

    grouped = orders.groupby("customer_id").agg(
        last_order_date=("order_date", "max"),
        frequency=("order_date", "count"),
        monetary=("revenue", "sum"),
    ).reset_index()

    grouped["recency_days"] = (pd.Timestamp(ANALYSIS_DATE) - grouped["last_order_date"]).dt.days

    # Quintile scores: recency is inverted (fewer days = better = score 5)
    grouped["r_score"] = pd.qcut(grouped["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    grouped["f_score"] = pd.qcut(grouped["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    grouped["m_score"] = pd.qcut(grouped["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    grouped["rfm_segment"] = grouped.apply(segment_customer, axis=1)

    return grouped[[
        "customer_id", "recency_days", "frequency", "monetary",
        "r_score", "f_score", "m_score", "rfm_segment",
    ]]


def segment_customer(row) -> str:
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 4:
        return "Loyal Customers"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r >= 3 and f >= 2 and m >= 3:
        return "Potential Loyalists"
    if r <= 2 and f >= 4 and m >= 4:
        return "Can't Lose Them"
    if r <= 2 and f >= 2:
        return "At Risk"
    return "Lost Customers"


def main():
    engine = get_engine()
    rfm = compute_rfm(engine)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM customer_rfm"))
    rfm.to_sql("customer_rfm", engine, if_exists="append", index=False)

    print(f"customer_rfm populated for {len(rfm)} customers.")
    print("\nSegment distribution:")
    print(rfm["rfm_segment"].value_counts())


if __name__ == "__main__":
    main()
