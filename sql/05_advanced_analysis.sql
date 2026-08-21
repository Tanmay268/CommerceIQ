-- ============================================================
-- 05_advanced_analysis.sql
-- Advanced techniques: RFM in pure SQL (NTILE), funnel drop-off,
-- rule-based at-risk query, 3-month moving average, cohort heatmap.
--
-- Note: the RFM segmentation actually used by the dashboard/Power BI comes
-- from src/rfm.py (pandas), because the score->segment mapping is business-
-- rule-heavy and reads more clearly there. This query demonstrates the same
-- metric is fully reachable in pure SQL with NTILE() window functions.
-- ============================================================

-- Q26. RFM raw metrics + quintile scoring via NTILE(5)
WITH order_agg AS (
    SELECT
        o.customer_id,
        MAX(o.order_date) AS last_order_date,
        COUNT(*) AS frequency,
        SUM(o.quantity * p.selling_price * (1 - o.discount)) AS monetary
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY o.customer_id
),
rfm_raw AS (
    SELECT
        customer_id,
        (DATE '2026-08-21' - last_order_date) AS recency_days,
        frequency,
        monetary
    FROM order_agg
)
SELECT
    customer_id, recency_days, frequency, ROUND(monetary::numeric, 2) AS monetary,
    NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,   -- fewer days = higher score
    NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
    NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
FROM rfm_raw
ORDER BY customer_id
LIMIT 20;


-- Q27. RFM segment sizes (reads from the customer_rfm table populated by src/rfm.py)
SELECT
    rfm_segment,
    COUNT(*) AS customers,
    ROUND((100.0 * COUNT(*) / SUM(COUNT(*)) OVER ())::numeric, 2) AS pct_of_customers,
    ROUND(AVG(monetary)::numeric, 2) AS avg_monetary
FROM customer_rfm
GROUP BY rfm_segment
ORDER BY customers DESC;


-- Q28. Purchase funnel with stage-over-stage drop-off % (window function: LAG)
WITH funnel AS (
    SELECT
        COUNT(*) AS visitors,
        SUM(CASE WHEN pages_viewed > 1 THEN 1 ELSE 0 END) AS product_views,
        SUM(CASE WHEN added_to_cart THEN 1 ELSE 0 END) AS add_to_cart,
        SUM(CASE WHEN purchased THEN 1 ELSE 0 END) AS purchases
    FROM website_sessions
),
stages AS (
    SELECT 1 AS stage_order, 'Visitors' AS stage, visitors AS count FROM funnel
    UNION ALL
    SELECT 2, 'Product View', product_views FROM funnel
    UNION ALL
    SELECT 3, 'Add to Cart', add_to_cart FROM funnel
    UNION ALL
    SELECT 4, 'Purchase', purchases FROM funnel
)
SELECT
    stage, count,
    ROUND((100.0 * count / LAG(count) OVER (ORDER BY stage_order))::numeric, 2) AS pct_of_prev_stage,
    ROUND((100.0 * count / FIRST_VALUE(count) OVER (ORDER BY stage_order))::numeric, 2) AS pct_of_visitors
FROM stages
ORDER BY stage_order;


-- Q29. Rule-based at-risk customers, expressed directly in SQL
-- (mirrors src/churn.py: days_since_last_order > 90 AND total_orders >= 3 -> At Risk)
WITH customer_orders AS (
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date,
        COUNT(*) AS total_orders
    FROM orders
    WHERE order_status <> 'Cancelled'
    GROUP BY customer_id
)
SELECT
    c.customer_id, c.customer_name,
    co.total_orders,
    (DATE '2026-08-21' - co.last_order_date) AS days_since_last_order
FROM customer_orders co
JOIN customers c ON c.customer_id = co.customer_id
WHERE (DATE '2026-08-21' - co.last_order_date) > 90
  AND co.total_orders >= 3
ORDER BY days_since_last_order DESC;


-- Q30. 3-month moving average revenue (window function: AVG() OVER with frame)
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', o.order_date)::date AS month,
        SUM(o.quantity * p.selling_price * (1 - o.discount)) AS revenue
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY 1
)
SELECT
    month,
    ROUND(revenue::numeric, 2) AS revenue,
    ROUND(AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::numeric, 2) AS moving_avg_3mo
FROM monthly
ORDER BY month;


-- Q31. Cohort retention heatmap, first 6 month-offsets only (pivoted view of Q10)
WITH cohort AS (
    SELECT customer_id, DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers
),
orders_m AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', order_date)::date AS order_month
    FROM orders
    WHERE order_status <> 'Cancelled'
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers FROM cohort GROUP BY cohort_month
),
retention AS (
    SELECT
        c.cohort_month,
        cs.cohort_customers,
        ((DATE_PART('year', o.order_month) - DATE_PART('year', c.cohort_month)) * 12
            + (DATE_PART('month', o.order_month) - DATE_PART('month', c.cohort_month)))::int AS month_offset,
        COUNT(DISTINCT o.customer_id) AS active_customers
    FROM cohort c
    JOIN orders_m o ON o.customer_id = c.customer_id AND o.order_month >= c.cohort_month
    JOIN cohort_size cs ON cs.cohort_month = c.cohort_month
    GROUP BY c.cohort_month, cs.cohort_customers, month_offset
)
SELECT
    cohort_month, cohort_customers,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 0) / cohort_customers, 1) AS m0_pct,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 1) / cohort_customers, 1) AS m1_pct,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 2) / cohort_customers, 1) AS m2_pct,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 3) / cohort_customers, 1) AS m3_pct,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 4) / cohort_customers, 1) AS m4_pct,
    ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_offset = 5) / cohort_customers, 1) AS m5_pct
FROM retention
GROUP BY cohort_month, cohort_customers
ORDER BY cohort_month;
