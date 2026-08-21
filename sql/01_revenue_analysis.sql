-- ============================================================
-- 01_revenue_analysis.sql
-- Revenue trend, growth, and running-total analytics.
-- ============================================================

-- Q1. Monthly revenue
SELECT
    DATE_TRUNC('month', o.order_date)::date AS month,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY 1
ORDER BY 1;


-- Q2. Month-over-month revenue growth % (window function: LAG)
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
    ROUND(LAG(revenue) OVER (ORDER BY month)::numeric, 2) AS prev_month_revenue,
    ROUND((
        (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100
    )::numeric, 2) AS mom_growth_pct
FROM monthly
ORDER BY month;


-- Q3. Cumulative (running total) revenue across the year (window function: SUM() OVER)
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
    ROUND(SUM(revenue) OVER (ORDER BY month)::numeric, 2) AS running_total_revenue
FROM monthly
ORDER BY month;


-- Q4. Average Order Value (AOV) trend by month
SELECT
    DATE_TRUNC('month', o.order_date)::date AS month,
    ROUND((SUM(o.quantity * p.selling_price * (1 - o.discount)) / COUNT(DISTINCT o.order_id))::numeric, 2) AS aov
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY 1
ORDER BY 1;


-- Q5. Revenue by product category
SELECT
    p.category,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND((100.0 * SUM(o.quantity * p.selling_price * (1 - o.discount))
        / SUM(SUM(o.quantity * p.selling_price * (1 - o.discount))) OVER ())::numeric, 2) AS pct_of_total_revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.category
ORDER BY revenue DESC;


-- Q6. Top 10 states by revenue
SELECT
    c.state,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
    COUNT(DISTINCT o.customer_id) AS customers
FROM orders o
JOIN products p ON p.product_id = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status <> 'Cancelled'
GROUP BY c.state
ORDER BY revenue DESC
LIMIT 10;
