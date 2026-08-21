"""
Exports a proper star schema from the loaded Postgres database as CSVs under
powerbi/star_schema_export/, ready for Power BI's Get Data > Folder/CSV.

Run this LAST, after load_to_db.py, rfm.py, and churn.py have all populated
their tables - the dimension tables enrich customers with RFM segment and
risk tier, which only exist once those modules have run.

Attribution note (documented in powerbi/dax_measures.md too): orders do not
carry a marketing channel or campaign_id (matching the PDF's own schema),
so FactSales and FactMarketing/FactSessions cannot be joined on a shared key
without an attribution model. This export keeps them as separate facts
sharing DimDate and DimChannel, and the DAX guide is explicit that
channel-level ROAS/CAC are approximations (conversions x overall AOV), not
order-level attributed revenue - the same limitation the PDF's schema has.
"""

from datetime import timedelta
from pathlib import Path

import pandas as pd

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "powerbi" / "star_schema_export"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_dim_customer(engine) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT c.customer_id, c.customer_name, c.gender, c.age, c.city, c.state,
               c.signup_date, c.customer_segment AS membership_tier,
               COALESCE(r.rfm_segment, 'No Orders') AS rfm_segment,
               COALESCE(k.risk_tier, 'Never Purchased') AS risk_tier
        FROM customers c
        LEFT JOIN customer_rfm r ON r.customer_id = c.customer_id
        LEFT JOIN customer_risk k ON k.customer_id = c.customer_id
        """,
        engine,
    )
    df["age_band"] = pd.cut(
        df["age"], bins=[0, 24, 34, 44, 54, 120],
        labels=["18-24", "25-34", "35-44", "45-54", "55+"]
    )
    return df


def build_dim_product(engine) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM products", engine)
    df["margin_pct"] = ((df["selling_price"] - df["unit_cost"]) / df["selling_price"] * 100).round(2)
    return df


def build_dim_date(engine) -> pd.DataFrame:
    min_max = pd.read_sql(
        """
        SELECT LEAST(MIN(order_date), MIN(session_date)) AS min_d,
               GREATEST(MAX(order_date), MAX(session_date)) AS max_d
        FROM orders, website_sessions
        """,
        engine,
    )
    start, end = min_max.loc[0, "min_d"], min_max.loc[0, "max_d"]
    dates = pd.date_range(start, end + timedelta(days=31), freq="D")
    df = pd.DataFrame({"date": dates})
    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year
    df["day_of_week"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    return df


def build_dim_channel(engine) -> pd.DataFrame:
    channels = pd.read_sql(
        "SELECT DISTINCT channel FROM website_sessions WHERE channel IS NOT NULL", engine
    )
    channel_type = {
        "Google Ads": "Paid", "Instagram": "Paid", "Facebook": "Paid",
        "Affiliate": "Paid", "Email": "Owned", "Organic": "Organic",
    }
    channels["channel_type"] = channels["channel"].map(channel_type).fillna("Other")
    return channels


def build_fact_sales(engine) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT o.order_id, o.customer_id, o.product_id, o.order_date,
               o.quantity, o.discount, o.shipping_cost, o.payment_method, o.order_status,
               p.selling_price, p.unit_cost,
               ROUND((o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
               ROUND((o.quantity * p.unit_cost)::numeric, 2) AS cost
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        """,
        engine,
    )
    df["profit"] = (df["revenue"] - df["cost"]).round(2)
    return df


def build_fact_sessions(engine) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM website_sessions", engine)


def build_fact_marketing(engine) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM marketing_campaigns", engine)
    df["ctr_pct"] = (df["clicks"] / df["impressions"] * 100).round(2)
    df["conversion_rate_pct"] = (df["conversions"] / df["clicks"] * 100).round(2)
    df["cac"] = (df["spend"] / df["conversions"].replace(0, pd.NA)).round(2)
    return df


def main():
    engine = get_engine()

    exports = {
        "DimCustomer.csv": build_dim_customer(engine),
        "DimProduct.csv": build_dim_product(engine),
        "DimDate.csv": build_dim_date(engine),
        "DimChannel.csv": build_dim_channel(engine),
        "FactSales.csv": build_fact_sales(engine),
        "FactSessions.csv": build_fact_sessions(engine),
        "FactMarketing.csv": build_fact_marketing(engine),
    }

    for filename, df in exports.items():
        path = OUT_DIR / filename
        df.to_csv(path, index=False)
        print(f"  {filename:20s} -> {len(df):6d} rows -> {path}")

    print("\nPower BI star schema export complete.")


if __name__ == "__main__":
    main()
