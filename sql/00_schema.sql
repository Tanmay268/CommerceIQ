-- CommerceIQ database schema
-- 7 source tables (loaded from data/cleaned/*.csv) + 2 tables populated later
-- by Python analytics modules (customer_rfm, customer_risk) + 1 for the
-- optional forecasting module (monthly_revenue_forecast).

DROP TABLE IF EXISTS customer_risk CASCADE;
DROP TABLE IF EXISTS customer_rfm CASCADE;
DROP TABLE IF EXISTS monthly_revenue_forecast CASCADE;
DROP TABLE IF EXISTS returns CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS website_sessions CASCADE;
DROP TABLE IF EXISTS marketing_campaigns CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id      VARCHAR(10) PRIMARY KEY,
    customer_name    VARCHAR(120) NOT NULL,
    gender           VARCHAR(10),
    age              INTEGER,
    city             VARCHAR(60),
    state            VARCHAR(60),
    signup_date      DATE,
    customer_segment VARCHAR(20)   -- membership tier assigned at signup (Regular/Premium/VIP) -
                                   -- NOT the RFM behavioral segment, which lives in customer_rfm
);

CREATE TABLE products (
    product_id     VARCHAR(10) PRIMARY KEY,
    product_name   VARCHAR(150) NOT NULL,
    category       VARCHAR(40) NOT NULL,
    subcategory    VARCHAR(40),
    brand          VARCHAR(60),
    unit_cost      NUMERIC(10, 2) NOT NULL,
    selling_price  NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    order_id        VARCHAR(10) PRIMARY KEY,
    customer_id     VARCHAR(10) NOT NULL REFERENCES customers(customer_id),
    order_date      DATE NOT NULL,
    product_id      VARCHAR(10) NOT NULL REFERENCES products(product_id),
    quantity        INTEGER NOT NULL,
    discount        NUMERIC(4, 2) NOT NULL DEFAULT 0,
    shipping_cost   NUMERIC(8, 2) NOT NULL DEFAULT 0,
    payment_method  VARCHAR(30),
    order_status    VARCHAR(20) NOT NULL
);

CREATE TABLE payments (
    payment_id      VARCHAR(12) PRIMARY KEY,
    order_id        VARCHAR(10) NOT NULL REFERENCES orders(order_id),
    payment_date    DATE,
    payment_method  VARCHAR(30),
    amount          NUMERIC(10, 2) NOT NULL,
    payment_status  VARCHAR(20)
);

CREATE TABLE returns (
    return_id      VARCHAR(10) PRIMARY KEY,
    order_id       VARCHAR(10) NOT NULL REFERENCES orders(order_id),
    return_date    DATE,
    return_reason  VARCHAR(60),
    refund_amount  NUMERIC(10, 2)
);

CREATE TABLE marketing_campaigns (
    campaign_id    VARCHAR(10) PRIMARY KEY,
    campaign_name  VARCHAR(100) NOT NULL,
    channel        VARCHAR(30) NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE,
    spend          NUMERIC(12, 2) NOT NULL DEFAULT 0,
    impressions    BIGINT NOT NULL DEFAULT 0,
    clicks         BIGINT NOT NULL DEFAULT 0,
    conversions    BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE website_sessions (
    session_id        VARCHAR(12) PRIMARY KEY,
    customer_id       VARCHAR(10) REFERENCES customers(customer_id),  -- nullable: anonymous session
    session_date      DATE NOT NULL,
    channel           VARCHAR(30),
    device            VARCHAR(20),
    pages_viewed      INTEGER,
    session_duration  NUMERIC(8, 1),  -- seconds
    added_to_cart     BOOLEAN,
    purchased         BOOLEAN
);

-- Populated by src/rfm.py
CREATE TABLE customer_rfm (
    customer_id      VARCHAR(10) PRIMARY KEY REFERENCES customers(customer_id),
    recency_days     INTEGER NOT NULL,
    frequency        INTEGER NOT NULL,
    monetary         NUMERIC(12, 2) NOT NULL,
    r_score          INTEGER NOT NULL,
    f_score          INTEGER NOT NULL,
    m_score          INTEGER NOT NULL,
    rfm_segment      VARCHAR(30) NOT NULL,
    computed_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Populated by src/churn.py
CREATE TABLE customer_risk (
    customer_id            VARCHAR(10) PRIMARY KEY REFERENCES customers(customer_id),
    days_since_last_order  INTEGER,
    total_orders            INTEGER,
    risk_tier               VARCHAR(20) NOT NULL,
    computed_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Populated by src/forecasting.py (optional advanced module)
CREATE TABLE monthly_revenue_forecast (
    forecast_month  DATE PRIMARY KEY,
    method          VARCHAR(30) NOT NULL,
    forecast_revenue NUMERIC(14, 2) NOT NULL,
    is_actual        BOOLEAN NOT NULL DEFAULT FALSE,
    computed_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_product_id ON orders(product_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_returns_order_id ON returns(order_id);
CREATE INDEX idx_sessions_customer_id ON website_sessions(customer_id);
CREATE INDEX idx_sessions_session_date ON website_sessions(session_date);
CREATE INDEX idx_sessions_channel ON website_sessions(channel);
