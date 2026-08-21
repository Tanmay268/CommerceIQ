import sys
from pathlib import Path

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(str(Path(__file__).resolve().parent.parent))
from data_loader import (  # noqa: E402
    load_fact_sales, load_sessions, load_campaigns,
    render_sidebar_filters, apply_sales_filters, apply_session_filters,
)

st.set_page_config(page_title="CommerceIQ — Marketing & Funnel", layout="wide")
st.title("Marketing & Funnel Analytics")

sales_all = load_fact_sales()
sessions_all = load_sessions()
campaigns_all = load_campaigns()

filters = render_sidebar_filters(sales_all, sessions_all)
sales = apply_sales_filters(sales_all, filters)
sales_completed = sales[sales["order_status"] != "Cancelled"]
sessions = apply_session_filters(sessions_all, filters)

campaigns = campaigns_all
if len(filters["date_range"]) == 2:
    start, end = filters["date_range"]
    campaigns = campaigns[(campaigns["start_date"].dt.date <= end) & (campaigns["end_date"].dt.date >= start)]
if filters["channels"]:
    campaigns = campaigns[campaigns["channel"].isin(filters["channels"])]

if sessions.empty:
    st.warning("No sessions match the current filters.")
    st.stop()

aov = sales_completed["revenue"].mean() if not sales_completed.empty else 0

st.caption(
    "Attribution note: orders don't carry a marketing channel/campaign_id, so ROAS below values each "
    "campaign conversion at the current filtered Average Order Value — an explicit, documented proxy, "
    "not order-level attributed revenue (see reports/decisions_log.md and powerbi/dax_measures.md)."
)

# --- KPI tiles -------------------------------------------------------------
total_spend = campaigns["spend"].sum()
total_conversions = campaigns["conversions"].sum()
cac = total_spend / total_conversions if total_conversions else 0
roas = (total_conversions * aov) / total_spend if total_spend else 0
total_clicks = campaigns["clicks"].sum()
total_impressions = campaigns["impressions"].sum()
ctr = total_clicks / total_impressions * 100 if total_impressions else 0
session_conv_rate = sessions["purchased"].sum() / len(sessions) * 100

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Marketing Spend", f"₹{total_spend/1e5:,.1f}L")
c2.metric("CAC", f"₹{cac:,.0f}")
c3.metric("ROAS", f"{roas:.2f}x")
c4.metric("CTR", f"{ctr:.2f}%")
c5.metric("Session Conversion Rate", f"{session_conv_rate:.2f}%")

st.divider()

col1, col2 = st.columns(2)
with col1:
    channel_stats = campaigns.groupby("channel", as_index=False).agg(spend=("spend", "sum"), conversions=("conversions", "sum"))
    channel_stats["cac"] = (channel_stats["spend"] / channel_stats["conversions"]).round(2)
    fig = px.bar(channel_stats.sort_values("cac"), x="cac", y="channel", orientation="h", title="CAC by Channel (lower is better)")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    channel_stats["roas"] = ((channel_stats["conversions"] * aov) / channel_stats["spend"]).round(2)
    fig = px.bar(channel_stats.sort_values("roas", ascending=False), x="roas", y="channel", orientation="h", title="ROAS by Channel (higher is better)")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Purchase Funnel")
stages = {
    "Visitors": len(sessions),
    "Product View": int((sessions["pages_viewed"] > 1).sum()),
    "Add to Cart": int(sessions["added_to_cart"].sum()),
    "Purchase": int(sessions["purchased"].sum()),
}
fig = go.Figure(go.Funnel(y=list(stages.keys()), x=list(stages.values())))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Channel Performance")
session_channel = sessions.groupby("channel", as_index=False).agg(
    sessions=("session_id", "count"),
    purchases=("purchased", "sum"),
)
session_channel["conversion_rate_pct"] = (session_channel["purchases"] / session_channel["sessions"] * 100).round(2)
st.dataframe(session_channel.sort_values("sessions", ascending=False), use_container_width=True, hide_index=True)
