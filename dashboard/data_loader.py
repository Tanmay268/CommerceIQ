"""
Shared, cached data access for the CommerceIQ Streamlit dashboard.

The dataset is small (a few thousand orders / a few thousand sessions), so
each loader pulls its whole table once per cache TTL and every page filters
the resulting in-memory DataFrame with widgets - no per-filter SQL
round-trips needed at this scale.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from db import get_engine  # noqa: E402

CACHE_TTL = 300


@st.cache_data(ttl=CACHE_TTL)
def load_fact_sales() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql(
        """
        SELECT
            o.order_id, o.order_date, o.quantity, o.discount, o.shipping_cost,
            o.payment_method, o.order_status,
            p.product_id, p.product_name, p.category, p.subcategory, p.brand,
            p.unit_cost, p.selling_price,
            c.customer_id, c.customer_name, c.gender, c.age, c.city, c.state,
            c.customer_segment AS membership_tier,
            COALESCE(r.rfm_segment, 'No Orders') AS rfm_segment,
            COALESCE(k.risk_tier, 'Never Purchased') AS risk_tier,
            (o.quantity * p.selling_price * (1 - o.discount)) AS revenue,
            (o.quantity * p.unit_cost) AS cost
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        JOIN customers c ON c.customer_id = o.customer_id
        LEFT JOIN customer_rfm r ON r.customer_id = c.customer_id
        LEFT JOIN customer_risk k ON k.customer_id = c.customer_id
        """,
        engine,
    )
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["profit"] = df["revenue"] - df["cost"]
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_returns() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql(
        """
        SELECT r.return_id, r.order_id, r.return_date, r.return_reason, r.refund_amount,
               o.product_id, o.customer_id
        FROM returns r
        JOIN orders o ON o.order_id = r.order_id
        """,
        engine,
    )
    df["return_date"] = pd.to_datetime(df["return_date"])
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_sessions() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM website_sessions", engine)
    df["session_date"] = pd.to_datetime(df["session_date"])
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_campaigns() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM marketing_campaigns", engine)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df


@st.cache_data(ttl=CACHE_TTL)
def load_customers() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql(
        """
        SELECT c.*, COALESCE(r.rfm_segment, 'No Orders') AS rfm_segment,
               COALESCE(k.risk_tier, 'Never Purchased') AS risk_tier
        FROM customers c
        LEFT JOIN customer_rfm r ON r.customer_id = c.customer_id
        LEFT JOIN customer_risk k ON k.customer_id = c.customer_id
        """,
        engine,
    )
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    return df


def render_sidebar_filters(sales: pd.DataFrame, sessions: pd.DataFrame) -> dict:
    """Renders the shared sidebar filter widgets and returns selected values."""
    st.sidebar.header("Filters")

    min_date, max_date = sales["order_date"].min().date(), sales["order_date"].max().date()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                        min_value=min_date, max_value=max_date)

    states = st.sidebar.multiselect("State", sorted(sales["state"].unique()))
    categories = st.sidebar.multiselect("Category", sorted(sales["category"].unique()))
    products = st.sidebar.multiselect("Product", sorted(sales["product_name"].unique()))
    rfm_segments = st.sidebar.multiselect("Customer Segment (RFM)", sorted(sales["rfm_segment"].unique()))
    membership_tiers = st.sidebar.multiselect("Membership Tier", sorted(sales["membership_tier"].unique()))
    channels = st.sidebar.multiselect("Marketing Channel", sorted(sessions["channel"].dropna().unique()))
    devices = st.sidebar.multiselect("Device", sorted(sessions["device"].dropna().unique()))

    return {
        "date_range": date_range,
        "states": states,
        "categories": categories,
        "products": products,
        "rfm_segments": rfm_segments,
        "membership_tiers": membership_tiers,
        "channels": channels,
        "devices": devices,
    }


def apply_sales_filters(sales: pd.DataFrame, filters: dict) -> pd.DataFrame:
    df = sales
    if len(filters["date_range"]) == 2:
        start, end = filters["date_range"]
        df = df[(df["order_date"].dt.date >= start) & (df["order_date"].dt.date <= end)]
    if filters["states"]:
        df = df[df["state"].isin(filters["states"])]
    if filters["categories"]:
        df = df[df["category"].isin(filters["categories"])]
    if filters["products"]:
        df = df[df["product_name"].isin(filters["products"])]
    if filters["rfm_segments"]:
        df = df[df["rfm_segment"].isin(filters["rfm_segments"])]
    if filters["membership_tiers"]:
        df = df[df["membership_tier"].isin(filters["membership_tiers"])]
    return df


def apply_session_filters(sessions: pd.DataFrame, filters: dict) -> pd.DataFrame:
    df = sessions
    if len(filters["date_range"]) == 2:
        start, end = filters["date_range"]
        df = df[(df["session_date"].dt.date >= start) & (df["session_date"].dt.date <= end)]
    if filters["channels"]:
        df = df[df["channel"].isin(filters["channels"])]
    if filters["devices"]:
        df = df[df["device"].isin(filters["devices"])]
    return df
