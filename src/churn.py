"""
Rule-based customer churn/risk scoring (PDF section 12).

Deliberately NOT machine learning - the PDF is explicit that for a Data
Analytics role the primary focus should stay SQL + analytics + BI, with ML
only as a possible future extension. This keeps the rule simple, explicit,
and easy to justify to a business stakeholder:

    days_since_last_order > 90 AND total_orders >= 3  -> At Risk
    days_since_last_order > 180                        -> Lost
    days_since_last_order <= 30                          -> Active
    everything else                                       -> Watch
"""

from datetime import date

import pandas as pd
from sqlalchemy import text

from db import get_engine

ANALYSIS_DATE = date(2026, 8, 21)


def classify(row) -> str:
    days = row["days_since_last_order"]
    orders = row["total_orders"]
    if pd.isna(days):
        return "Never Purchased"
    if days > 180:
        return "Lost"
    if days > 90 and orders >= 3:
        return "At Risk"
    if days <= 30:
        return "Active"
    return "Watch"


def compute_risk(engine) -> pd.DataFrame:
    customers = pd.read_sql("SELECT customer_id FROM customers", engine)
    orders = pd.read_sql(
        "SELECT customer_id, order_date FROM orders WHERE order_status <> 'Cancelled'",
        engine,
    )
    orders["order_date"] = pd.to_datetime(orders["order_date"])

    agg = orders.groupby("customer_id").agg(
        last_order_date=("order_date", "max"),
        total_orders=("order_date", "count"),
    ).reset_index()

    df = customers.merge(agg, on="customer_id", how="left")
    df["days_since_last_order"] = (pd.Timestamp(ANALYSIS_DATE) - df["last_order_date"]).dt.days
    df["total_orders"] = df["total_orders"].fillna(0).astype(int)
    df["risk_tier"] = df.apply(classify, axis=1)

    return df[["customer_id", "days_since_last_order", "total_orders", "risk_tier"]]


def main():
    engine = get_engine()
    risk = compute_risk(engine)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM customer_risk"))
    risk.to_sql("customer_risk", engine, if_exists="append", index=False)

    print(f"customer_risk populated for {len(risk)} customers.")
    print("\nRisk tier distribution:")
    print(risk["risk_tier"].value_counts())


if __name__ == "__main__":
    main()
