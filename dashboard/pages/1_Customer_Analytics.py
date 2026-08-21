import sys
from pathlib import Path

import streamlit as st
import plotly.express as px

sys.path.append(str(Path(__file__).resolve().parent.parent))
from data_loader import (  # noqa: E402
    load_fact_sales, load_sessions, load_customers,
    render_sidebar_filters, apply_sales_filters,
)

st.set_page_config(page_title="CommerceIQ — Customer Analytics", layout="wide")
st.title("Customer Analytics")

sales_all = load_fact_sales()
sessions_all = load_sessions()
customers_all = load_customers()

filters = render_sidebar_filters(sales_all, sessions_all)
sales = apply_sales_filters(sales_all, filters)
sales_completed = sales[sales["order_status"] != "Cancelled"]

if sales_completed.empty:
    st.warning("No orders match the current filters.")
    st.stop()

filtered_customer_ids = set(sales_completed["customer_id"].unique())
customers = customers_all[customers_all["customer_id"].isin(filtered_customer_ids)]

# --- KPI tiles ---------------------------------------------------------
total_customers = len(customers)
order_counts = sales_completed.groupby("customer_id")["order_id"].nunique()
repeat_customers = (order_counts > 1).sum()
repeat_rate = repeat_customers / total_customers * 100 if total_customers else 0
clv = sales_completed.groupby("customer_id")["revenue"].sum().mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers (in view)", f"{total_customers:,}")
c2.metric("Repeat Customers", f"{repeat_customers:,}")
c3.metric("Repeat Purchase Rate", f"{repeat_rate:.1f}%")
c4.metric("Avg. Customer Lifetime Value", f"₹{clv:,.0f}")

st.divider()

col1, col2 = st.columns(2)

with col1:
    seg_counts = customers["rfm_segment"].value_counts().reset_index()
    seg_counts.columns = ["rfm_segment", "customers"]
    fig = px.pie(seg_counts, names="rfm_segment", values="customers", title="RFM Segmentation", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    risk_counts = customers["risk_tier"].value_counts().reset_index()
    risk_counts.columns = ["risk_tier", "customers"]
    fig = px.bar(risk_counts, x="risk_tier", y="customers", title="Customer Risk Tiers", color="risk_tier")
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    geo = customers.groupby("state", as_index=False).size().sort_values("size", ascending=False).head(10)
    fig = px.bar(geo, x="size", y="state", orientation="h", title="Top 10 States by Customer Count")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="customers")
    st.plotly_chart(fig, use_container_width=True)

with col4:
    tier_revenue = sales_completed.groupby("membership_tier", as_index=False)["revenue"].sum()
    fig = px.bar(tier_revenue, x="membership_tier", y="revenue", title="Revenue by Membership Tier")
    st.plotly_chart(fig, use_container_width=True)
