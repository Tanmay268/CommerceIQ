-- ============================================================
-- 02_customer_analysis.sql
-- Customer behavior: repeat rate, CLV, cohorts, new vs returning.
-- ============================================================

-- Q7. Total customers, repeat customer rate
WITH order_counts AS (
    SELECT customer_id, COUNT(*) AS n_orders
    FROM orders
    WHERE order_status <> 'Cancelled'
    GROUP BY customer_id
)
SELECT
    (SELECT COUNT(*) FROM customers) AS total_customers,
    COUNT(*) AS customers_with_orders,
    COUNT(*) FILTER (WHERE n_orders > 1) AS repeat_customers,
    ROUND((100.0 * COUNT(*) FILTER (WHERE n_orders > 1) / COUNT(*))::numeric, 2) AS repeat_customer_rate_pct
FROM order_counts;


-- Q8. Customer Lifetime Value (CLV) - top 10 customers by total revenue (window function: RANK)
WITH clv AS (
    SELECT
        o.customer_id,
        SUM(o.quantity * p.selling_price * (1 - o.discount)) AS lifetime_revenue,
        COUNT(*) AS orders
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY o.customer_id
)
SELECT
    c.customer_id, cu.customer_name, c.orders,
    ROUND(c.lifetime_revenue::numeric, 2) AS lifetime_revenue,
    RANK() OVER (ORDER BY c.lifetime_revenue DESC) AS revenue_rank
FROM clv c
JOIN customers cu ON cu.customer_id = c.customer_id
ORDER BY revenue_rank
LIMIT 10;


-- Q9. New vs returning customers by month
-- "New" = this is the customer's first-ever order month; "Returning" = they'd ordered before.
WITH first_order AS (
    SELECT customer_id, MIN(DATE_TRUNC('month', order_date))::date AS first_order_month
    FROM orders
    WHERE order_status <> 'Cancelled'
    GROUP BY customer_id
),
monthly_orders AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', order_date)::date AS order_month
    FROM orders
    WHERE order_status <> 'Cancelled'
)
SELECT
    mo.order_month,
    COUNT(*) FILTER (WHERE mo.order_month = fo.first_order_month) AS new_customers,
    COUNT(*) FILTER (WHERE mo.order_month <> fo.first_order_month) AS returning_customers
FROM monthly_orders mo
JOIN first_order fo ON fo.customer_id = mo.customer_id
GROUP BY mo.order_month
ORDER BY mo.order_month;


-- Q10. Signup-month cohort retention (CTE + self-join)
-- For each signup cohort, what % of that cohort placed an order in each
-- subsequent month-offset (0 = signup month, 1 = one month later, etc).
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
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM cohort
    GROUP BY cohort_month
)
SELECT
    c.cohort_month,
    cs.cohort_customers,
    (DATE_PART('year', o.order_month) - DATE_PART('year', c.cohort_month)) * 12
        + (DATE_PART('month', o.order_month) - DATE_PART('month', c.cohort_month)) AS month_offset,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    ROUND((100.0 * COUNT(DISTINCT o.customer_id) / cs.cohort_customers)::numeric, 2) AS retention_pct
FROM cohort c
JOIN orders_m o ON o.customer_id = c.customer_id AND o.order_month >= c.cohort_month
JOIN cohort_size cs ON cs.cohort_month = c.cohort_month
GROUP BY c.cohort_month, cs.cohort_customers, month_offset
ORDER BY c.cohort_month, month_offset;


-- Q11. Average orders per customer, by membership tier
SELECT
    c.customer_segment AS membership_tier,
    COUNT(DISTINCT c.customer_id) AS customers,
    COUNT(o.order_id) AS total_orders,
    ROUND((COUNT(o.order_id)::numeric / COUNT(DISTINCT c.customer_id)), 2) AS avg_orders_per_customer
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.order_status <> 'Cancelled'
GROUP BY c.customer_segment
ORDER BY avg_orders_per_customer DESC;


-- Q12. Revenue contribution by membership tier
SELECT
    c.customer_segment AS membership_tier,
    ROUND(SUM(o.quantity * p.selling_price * (1 - o.discount))::numeric, 2) AS revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status <> 'Cancelled'
GROUP BY c.customer_segment
ORDER BY revenue DESC;
