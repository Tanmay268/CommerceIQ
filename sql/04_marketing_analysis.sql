-- ============================================================
-- 04_marketing_analysis.sql
-- Marketing channel/campaign performance: CTR, conversion rate, CAC, ROAS.
--
-- Attribution note: orders carry no campaign_id/channel (matching the PDF's
-- own schema), so campaign "conversions" cannot be joined to actual order
-- revenue directly. ROAS below values each campaign conversion at the
-- dataset's overall Average Order Value as an explicit, documented proxy -
-- the same simplification used in src/generate_insights.py and the Power BI
-- DAX guide (powerbi/dax_measures.md).
-- ============================================================

-- Q20. Campaign-level CTR and conversion rate
SELECT
    campaign_id, campaign_name, channel, spend,
    impressions, clicks, conversions,
    ROUND((100.0 * clicks / NULLIF(impressions, 0))::numeric, 2) AS ctr_pct,
    ROUND((100.0 * conversions / NULLIF(clicks, 0))::numeric, 2) AS conversion_rate_pct
FROM marketing_campaigns
ORDER BY spend DESC;


-- Q21. Customer Acquisition Cost (CAC) by channel
SELECT
    channel,
    ROUND(SUM(spend)::numeric, 2) AS total_spend,
    SUM(conversions) AS total_conversions,
    ROUND((SUM(spend) / NULLIF(SUM(conversions), 0))::numeric, 2) AS cac
FROM marketing_campaigns
GROUP BY channel
ORDER BY cac ASC NULLS LAST;


-- Q22. ROAS by channel (proxy: conversions x overall AOV, see attribution note above)
WITH overall_aov AS (
    SELECT AVG(o.quantity * p.selling_price * (1 - o.discount)) AS aov
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
),
channel_totals AS (
    SELECT channel, SUM(spend) AS spend, SUM(conversions) AS conversions
    FROM marketing_campaigns
    GROUP BY channel
)
SELECT
    ct.channel,
    ROUND(ct.spend::numeric, 2) AS spend,
    ct.conversions,
    ROUND((ct.conversions * oa.aov)::numeric, 2) AS estimated_attributed_revenue,
    ROUND(((ct.conversions * oa.aov) / NULLIF(ct.spend, 0))::numeric, 2) AS roas
FROM channel_totals ct
CROSS JOIN overall_aov oa
ORDER BY roas DESC NULLS LAST;


-- Q23. Channel comparison: sessions, purchases, session-level conversion rate
SELECT
    channel,
    COUNT(*) AS sessions,
    SUM(CASE WHEN added_to_cart THEN 1 ELSE 0 END) AS add_to_cart,
    SUM(CASE WHEN purchased THEN 1 ELSE 0 END) AS purchases,
    ROUND((100.0 * SUM(CASE WHEN purchased THEN 1 ELSE 0 END) / COUNT(*))::numeric, 2) AS session_conversion_rate_pct
FROM website_sessions
GROUP BY channel
ORDER BY session_conversion_rate_pct DESC;


-- Q24. Email vs. paid channels: efficiency comparison
SELECT
    CASE WHEN channel = 'Email' THEN 'Email'
         WHEN channel = 'Organic' THEN 'Organic'
         ELSE 'Paid' END AS channel_group,
    COUNT(*) AS sessions,
    SUM(CASE WHEN purchased THEN 1 ELSE 0 END) AS purchases,
    ROUND((100.0 * SUM(CASE WHEN purchased THEN 1 ELSE 0 END) / COUNT(*))::numeric, 2) AS conversion_rate_pct
FROM website_sessions
GROUP BY channel_group
ORDER BY conversion_rate_pct DESC;


-- Q25. Device performance: sessions and conversion rate by device
SELECT
    device,
    COUNT(*) AS sessions,
    ROUND((100.0 * SUM(CASE WHEN purchased THEN 1 ELSE 0 END) / COUNT(*))::numeric, 2) AS conversion_rate_pct
FROM website_sessions
GROUP BY device
ORDER BY conversion_rate_pct DESC;
