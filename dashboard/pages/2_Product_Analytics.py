import sys
from pathlib import Path

import streamlit as st
import plotly.express as px

sys.path.append(str(Path(__file__).resolve().parent.parent))
from data_loader import (  # noqa: E402
    load_fact_sales, load_returns, load_sessions,
    render_sidebar_filters, apply_sales_filters,
)

st.set_page_config(page_title="CommerceIQ — Product Analytics", layout="wide")
st.title("Product Analytics")

sales_all = load_fact_sales()
returns_all = load_returns()
sessions_all = load_sessions()

filters = render_sidebar_filters(sales_all, sessions_all)
sales = apply_sales_filters(sales_all, filters)
sales_completed = sales[sales["order_status"] != "Cancelled"]

if sales_completed.empty:
    st.warning("No orders match the current filters.")
    st.stop()

product_stats = sales_completed.groupby(
    ["product_id", "product_name", "category"], as_index=False
).agg(units_sold=("quantity", "sum"), revenue=("revenue", "sum"), profit=("profit", "sum"))
product_stats["margin_pct"] = (product_stats["profit"] / product_stats["revenue"] * 100).round(1)

order_counts = sales_completed.groupby("product_id")["order_id"].nunique()
return_counts = (
    returns_all[returns_all["order_id"].isin(sales_completed["order_id"])]
    .groupby("product_id")["return_id"].count()
)
product_stats["return_rate_pct"] = (
    product_stats["product_id"].map(return_counts).fillna(0)
    / product_stats["product_id"].map(order_counts) * 100
).round(1)

# --- KPI tiles -----------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"₹{product_stats['revenue'].sum()/1e5:,.1f}L")
c2.metric("Total Profit", f"₹{product_stats['profit'].sum()/1e5:,.1f}L")
c3.metric("Blended Margin", f"{product_stats['profit'].sum() / product_stats['revenue'].sum() * 100:.1f}%")
c4.metric("Units Sold", f"{product_stats['units_sold'].sum():,}")

st.divider()

st.subheader("High/Low Sales × High/Low Profit Quadrant")
sales_median = product_stats["units_sold"].median()
profit_median = product_stats["profit"].median()
fig = px.scatter(
    product_stats, x="units_sold", y="profit", color="category",
    hover_data=["product_name", "margin_pct"],
    title="Product Quadrant (median-split lines mark high vs. low)",
)
fig.add_vline(x=sales_median, line_dash="dash", line_color="gray")
fig.add_hline(y=profit_median, line_dash="dash", line_color="gray")
st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Revenue / Profit / Margin by Category")
    cat = sales_completed.groupby("category", as_index=False).agg(
        revenue=("revenue", "sum"), profit=("profit", "sum")
    )
    cat["margin_pct"] = (cat["profit"] / cat["revenue"] * 100).round(1)
    st.dataframe(cat.sort_values("profit", ascending=False), use_container_width=True, hide_index=True)

with col2:
    st.subheader("Highest Return-Rate Products (min. 5 orders)")
    eligible = product_stats[product_stats["product_id"].map(order_counts).fillna(0) >= 5]
    st.dataframe(
        eligible.sort_values("return_rate_pct", ascending=False)
        [["product_name", "category", "return_rate_pct"]].head(10),
        use_container_width=True, hide_index=True,
    )

st.subheader("Full Product Table")
st.dataframe(
    product_stats.sort_values("revenue", ascending=False),
    use_container_width=True, hide_index=True,
)
