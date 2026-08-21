-- ============================================================
-- 03_product_analysis.sql
-- Product performance: top sellers, profitability, rankings, returns, trends.
-- ============================================================

-- Q13. Top 10 products by units sold
SELECT
    p.product_id, p.product_name, p.category,
    SUM(o.quantity) AS units_sold
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY units_sold DESC
LIMIT 10;


-- Q14. Top 10 products by revenue
SELECT
    p.product_id, p.product_name, p.category,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;


-- Q15. Revenue, profit, and margin % by category
SELECT
    p.category,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
    ROUND(SUM(o.quantity * p.unit_cost)::numeric, 2) AS cost,
    ROUND((SUM(o.quantity * p.selling_price * (1 - o.discount)) - SUM(o.quantity * p.unit_cost))::numeric, 2) AS profit,
    ROUND((
        (SUM(o.quantity * p.selling_price * (1 - o.discount)) - SUM(o.quantity * p.unit_cost))
        / NULLIF(SUM(o.quantity * p.selling_price * (1 - o.discount)), 0) * 100
    )::numeric, 2) AS margin_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.category
ORDER BY profit DESC;


-- Q16. Product ranking within its own category by revenue (window function: RANK PARTITION BY)
WITH product_revenue AS (
    SELECT
        p.product_id, p.product_name, p.category,
        SUM(o.quantity * p.selling_price * (1 - o.discount)) AS revenue
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY p.product_id, p.product_name, p.category
)
SELECT
    product_id, product_name, category,
    ROUND(revenue::numeric, 2) AS revenue,
    RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;


-- Q17. Return rate by product (top 10 highest, min 5 orders to be meaningful)
WITH product_orders AS (
    SELECT product_id, COUNT(*) AS n_orders
    FROM orders
    GROUP BY product_id
),
product_returns AS (
    SELECT o.product_id, COUNT(*) AS n_returns
    FROM returns r
    JOIN orders o ON o.order_id = r.order_id
    GROUP BY o.product_id
)
SELECT
    p.product_id, p.product_name, p.category,
    po.n_orders,
    COALESCE(pr.n_returns, 0) AS n_returns,
    ROUND((100.0 * COALESCE(pr.n_returns, 0) / po.n_orders)::numeric, 2) AS return_rate_pct
FROM product_orders po
JOIN products p ON p.product_id = po.product_id
LEFT JOIN product_returns pr ON pr.product_id = po.product_id
WHERE po.n_orders >= 5
ORDER BY return_rate_pct DESC
LIMIT 10;


-- Q18. Products with declining month-over-month revenue (window function: LAG)
WITH product_month AS (
    SELECT
        p.product_id, p.product_name,
        DATE_TRUNC('month', o.order_date)::date AS month,
        SUM(o.quantity * p.selling_price * (1 - o.discount)) AS revenue
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY p.product_id, p.product_name, month
),
with_trend AS (
    SELECT
        product_id, product_name, month, revenue,
        LAG(revenue) OVER (PARTITION BY product_id ORDER BY month) AS prev_month_revenue
    FROM product_month
)
SELECT
    product_id, product_name, month,
    ROUND(revenue::numeric, 2) AS revenue,
    ROUND(prev_month_revenue::numeric, 2) AS prev_month_revenue,
    ROUND(((revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0) * 100)::numeric, 2) AS mom_change_pct
FROM with_trend
WHERE prev_month_revenue IS NOT NULL AND revenue < prev_month_revenue
ORDER BY mom_change_pct ASC
LIMIT 15;


-- Q19. Margin leaders vs. volume leaders (identifies the PDF's "Product A vs Product B" scenario)
SELECT
    p.product_id, p.product_name, p.category,
    SUM(o.quantity) AS units_sold,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue,
    ROUND((SUM(o.quantity * p.selling_price * (1 - o.discount)) - SUM(o.quantity * p.unit_cost))::numeric, 2) AS profit
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_status <> 'Cancelled'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC, profit DESC
LIMIT 15;
