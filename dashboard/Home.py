import streamlit as st
import plotly.express as px

from data_loader import (
    load_fact_sales, load_returns, load_sessions,
    render_sidebar_filters, apply_sales_filters,
)

st.set_page_config(page_title="CommerceIQ — Executive Dashboard", layout="wide")

st.title("CommerceIQ — Executive Dashboard")
st.caption("E-commerce Business Intelligence & Customer Analytics Platform")

sales_all = load_fact_sales()
returns_all = load_returns()
sessions_all = load_sessions()

filters = render_sidebar_filters(sales_all, sessions_all)
sales = apply_sales_filters(sales_all, filters)
sales_completed = sales[sales["order_status"] != "Cancelled"]

if sales_completed.empty:
    st.warning("No orders match the current filters.")
    st.stop()

# --- KPI tiles -------------------------------------------------------------
revenue = sales_completed["revenue"].sum()
profit = sales_completed["profit"].sum()
orders = sales_completed["order_id"].nunique()
customers = sales_completed["customer_id"].nunique()
aov = revenue / orders if orders else 0
returned_orders = returns_all[returns_all["order_id"].isin(sales_completed["order_id"])].shape[0]
return_rate = returned_orders / orders * 100 if orders else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Revenue", f"₹{revenue/1e5:,.1f}L")
c2.metric("Orders", f"{orders:,}")
c3.metric("Customers", f"{customers:,}")
c4.metric("AOV", f"₹{aov:,.0f}")
c5.metric("Profit", f"₹{profit/1e5:,.1f}L")
c6.metric("Return Rate", f"{return_rate:.1f}%")

st.divider()

col1, col2 = st.columns(2)

with col1:
    monthly = (
        sales_completed.assign(month=sales_completed["order_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)["revenue"].sum()
    )
    fig = px.line(monthly, x="month", y="revenue", markers=True, title="Revenue Trend")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    by_category = sales_completed.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
    fig = px.bar(by_category, x="revenue", y="category", orientation="h", title="Revenue by Category")
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    top_products = (
        sales_completed.groupby("product_name", as_index=False)["revenue"].sum()
        .sort_values("revenue", ascending=False).head(10)
    )
    fig = px.bar(top_products, x="revenue", y="product_name", orientation="h", title="Top 10 Products")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with col4:
    by_state = (
        sales_completed.groupby("state", as_index=False)["revenue"].sum()
        .sort_values("revenue", ascending=False).head(10)
    )
    fig = px.bar(by_state, x="revenue", y="state", orientation="h", title="Regional Performance (Top 10 States)")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Use the sidebar to filter by date, state, category, product, customer segment, "
    "marketing channel, and device — every chart on every page updates together."
)
