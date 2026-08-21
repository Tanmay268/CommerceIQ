"""
Synthetic data generator for CommerceIQ.

Produces 7 raw CSVs under data/raw/ that mimic a real e-commerce export:
customers, products, orders, payments, returns, marketing_campaigns,
website_sessions.

The data is INTENTIONALLY messy in small, controlled ways (inconsistent
category casing, missing values, a few duplicate rows, a few invalid
dates/negative quantities, a couple of orphan foreign keys, a few age
outliers) so that src/clean_data.py has real problems to fix, matching
the PDF spec's emphasis on data cleaning being a first-class step.

Deterministic: everything is seeded (SEED = 42), so re-running this
script reproduces the exact same dataset.
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)
rng = np.random.default_rng(SEED)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TODAY = date(2026, 8, 21)
HISTORY_START = TODAY - timedelta(days=365)

N_CUSTOMERS = 2000
N_PRODUCTS = 150
N_ORDERS = 5000
N_CAMPAIGNS = 24
N_SESSIONS = 15000

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

CITY_STATE = {
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu",
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nagpur": "Maharashtra",
    "Bangalore": "Karnataka", "Mysuru": "Karnataka",
    "Delhi": "Delhi",
    "Gurugram": "Haryana", "Faridabad": "Haryana",
    "Hyderabad": "Telangana",
    "Kolkata": "West Bengal",
    "Ahmedabad": "Gujarat", "Surat": "Gujarat",
    "Jaipur": "Rajasthan",
    "Lucknow": "Uttar Pradesh", "Kanpur": "Uttar Pradesh",
    "Chandigarh": "Chandigarh",
    "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh",
    "Kochi": "Kerala", "Thiruvananthapuram": "Kerala",
    "Patna": "Bihar",
    "Guwahati": "Assam",
}
CITIES = list(CITY_STATE.keys())

CATEGORY_TREE = {
    "Electronics": {
        "subcategories": ["Audio", "Mobiles", "Laptops", "Accessories"],
        "brands": ["Sony", "JBL", "boAt", "Samsung", "Xiaomi", "Apple", "Dell", "HP", "Lenovo", "Anker", "Portronics"],
        "price_range": (500, 60000),
    },
    "Fashion": {
        "subcategories": ["Men's Wear", "Women's Wear", "Footwear"],
        "brands": ["Levis", "Peter England", "Allen Solly", "Biba", "W", "Fabindia", "Bata", "Woodland", "Puma"],
        "price_range": (300, 5000),
    },
    "Home": {
        "subcategories": ["Kitchen", "Furniture", "Decor"],
        "brands": ["Prestige", "Pigeon", "Milton", "Nilkamal", "Godrej Interio", "Wakefit"],
        "price_range": (200, 8000),
    },
    "Beauty": {
        "subcategories": ["Skincare", "Haircare", "Makeup"],
        "brands": ["Nivea", "Lakme", "Mamaearth", "Dove", "Tresemme", "Maybelline"],
        "price_range": (100, 2000),
    },
    "Sports": {
        "subcategories": ["Fitness", "Outdoor"],
        "brands": ["Decathlon", "Cosco", "Wildcraft", "Quechua"],
        "price_range": (300, 6000),
    },
    "Toys": {
        "subcategories": ["Educational", "Outdoor Toys"],
        "brands": ["Funskool", "LEGO", "Hot Wheels"],
        "price_range": (150, 3000),
    },
}
CATEGORIES = list(CATEGORY_TREE.keys())

CHANNELS = ["Google Ads", "Instagram", "Facebook", "Email", "Affiliate", "Organic"]
DEVICES = ["Mobile", "Desktop", "Tablet"]
PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "COD", "Net Banking"]
ORDER_STATUSES = ["Delivered", "Shipped", "Cancelled", "Returned", "Pending"]
ORDER_STATUS_WEIGHTS = [0.72, 0.10, 0.06, 0.06, 0.06]
RETURN_REASONS = ["Defective", "Wrong Item", "Size Issue", "Not as Described", "Changed Mind", "Late Delivery"]
MEMBERSHIP_TIERS = ["Regular", "Premium", "VIP"]
MEMBERSHIP_WEIGHTS = [0.70, 0.24, 0.06]


def random_date(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=int(rng.integers(0, delta_days + 1)))


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------

def generate_customers() -> pd.DataFrame:
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        customer_id = f"C{10000 + i}"
        gender = random.choice(["Male", "Female"])
        name = fake.name_male() if gender == "Male" else fake.name_female()
        age = int(rng.normal(34, 10))
        age = max(18, min(65, age))
        city = random.choice(CITIES)
        state = CITY_STATE[city]
        signup_date = random_date(HISTORY_START - timedelta(days=200), TODAY)
        segment = random.choices(MEMBERSHIP_TIERS, weights=MEMBERSHIP_WEIGHTS, k=1)[0]
        rows.append([customer_id, name, gender, age, city, state, signup_date, segment])

    df = pd.DataFrame(rows, columns=[
        "customer_id", "customer_name", "gender", "age", "city", "state",
        "signup_date", "customer_segment",
    ])

    # --- inject messiness -------------------------------------------------
    # 1) ~2% missing age
    mask = df.sample(frac=0.02, random_state=SEED).index
    df.loc[mask, "age"] = np.nan

    # 2) a handful of impossible age outliers
    outlier_idx = df.sample(n=6, random_state=SEED + 1).index
    df.loc[outlier_idx, "age"] = random.choice([150, -5, 0, 200])

    # 3) inconsistent state casing/spelling for a slice of rows
    messy_idx = df.sample(frac=0.05, random_state=SEED + 2).index
    def mess_state(s):
        return random.choice([s.upper(), s.lower(), s.replace(" ", "")])
    df.loc[messy_idx, "state"] = df.loc[messy_idx, "state"].apply(mess_state)

    # 4) ~1% missing city
    mask = df.sample(frac=0.01, random_state=SEED + 3).index
    df.loc[mask, "city"] = np.nan

    # 5) duplicate a few customer rows outright (simulates export duplication)
    dupes = df.sample(n=15, random_state=SEED + 4)
    df = pd.concat([df, dupes], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------

def generate_products() -> pd.DataFrame:
    rows = []
    per_category = N_PRODUCTS // len(CATEGORIES)
    pid = 1
    for category, meta in CATEGORY_TREE.items():
        for _ in range(per_category):
            product_id = f"P{1000 + pid}"
            subcategory = random.choice(meta["subcategories"])
            brand = random.choice(meta["brands"])
            low, high = meta["price_range"]
            unit_cost = round(rng.uniform(low, high * 0.7), 2)
            markup = rng.uniform(1.2, 1.8)
            selling_price = round(unit_cost * markup, 2)
            product_name = f"{brand} {subcategory} {fake.word().capitalize()}"
            rows.append([product_id, product_name, category, subcategory, brand, unit_cost, selling_price])
            pid += 1

    df = pd.DataFrame(rows, columns=[
        "product_id", "product_name", "category", "subcategory", "brand",
        "unit_cost", "selling_price",
    ])

    # --- inject messiness -------------------------------------------------
    # inconsistent category casing on a slice of rows
    messy_idx = df.sample(frac=0.08, random_state=SEED).index
    def mess_category(c):
        return random.choice([c.upper(), c.lower(), c[:-1] if c.endswith("s") else c])
    df.loc[messy_idx, "category"] = df.loc[messy_idx, "category"].apply(mess_category)

    # missing brand for a few rows
    mask = df.sample(frac=0.03, random_state=SEED + 1).index
    df.loc[mask, "brand"] = np.nan

    return df


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------

def generate_orders(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    valid_customer_ids = customers["customer_id"].unique().tolist()
    valid_product_ids = products["product_id"].unique().tolist()
    price_lookup = products.drop_duplicates("product_id").set_index("product_id")["selling_price"].to_dict()

    rows = []
    for i in range(1, N_ORDERS + 1):
        order_id = f"O{100000 + i}"
        customer_id = random.choice(valid_customer_ids)
        product_id = random.choice(valid_product_ids)
        order_date = random_date(HISTORY_START, TODAY)
        quantity = int(rng.choice([1, 1, 1, 2, 2, 3, 4], size=1)[0])
        discount = round(float(rng.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2])), 2)
        shipping_cost = round(rng.uniform(0, 150), 2)
        payment_method = random.choice(PAYMENT_METHODS)
        order_status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1)[0]
        rows.append([order_id, customer_id, order_date, product_id, quantity,
                      discount, shipping_cost, payment_method, order_status])

    df = pd.DataFrame(rows, columns=[
        "order_id", "customer_id", "order_date", "product_id", "quantity",
        "discount", "shipping_cost", "payment_method", "order_status",
    ])

    # --- inject messiness -------------------------------------------------
    # a few negative quantities (data entry errors)
    neg_idx = df.sample(n=8, random_state=SEED).index
    df.loc[neg_idx, "quantity"] = -df.loc[neg_idx, "quantity"]

    # a few invalid/malformed order dates
    bad_date_idx = df.sample(n=5, random_state=SEED + 1).index
    df.loc[bad_date_idx, "order_date"] = random.choice(["0000-00-00", "31/02/2026", "not_a_date", ""])

    # a few orphan foreign keys (references a customer/product that doesn't exist)
    orphan_cust_idx = df.sample(n=4, random_state=SEED + 2).index
    df.loc[orphan_cust_idx, "customer_id"] = "C99999"
    orphan_prod_idx = df.sample(n=4, random_state=SEED + 3).index
    df.loc[orphan_prod_idx, "product_id"] = "P9999"

    # duplicate a handful of orders outright
    dupes = df.sample(n=20, random_state=SEED + 4)
    df = pd.concat([df, dupes], ignore_index=True)

    return df, price_lookup


# ---------------------------------------------------------------------------
# payments
# ---------------------------------------------------------------------------

def generate_payments(orders: pd.DataFrame, price_lookup: dict) -> pd.DataFrame:
    rows = []
    for i, order in enumerate(orders.itertuples(index=False), start=1):
        payment_id = f"PAY{100000 + i}"
        unit_price = price_lookup.get(order.product_id, np.nan)
        qty = order.quantity if pd.notna(order.quantity) else 1
        amount = round(float(unit_price) * abs(qty) * (1 - order.discount), 2) if pd.notna(unit_price) else np.nan
        try:
            pay_date = pd.to_datetime(order.order_date) + timedelta(days=int(rng.integers(0, 2)))
        except Exception:
            pay_date = pd.NaT
        status = "Success" if order.order_status != "Cancelled" else random.choice(["Failed", "Refunded"])
        rows.append([payment_id, order.order_id, pay_date, order.payment_method, amount, status])

    df = pd.DataFrame(rows, columns=[
        "payment_id", "order_id", "payment_date", "payment_method", "amount", "payment_status",
    ])

    # a few missing amounts
    mask = df.sample(frac=0.01, random_state=SEED).index
    df.loc[mask, "amount"] = np.nan

    return df


# ---------------------------------------------------------------------------
# returns
# ---------------------------------------------------------------------------

def generate_returns(orders: pd.DataFrame, price_lookup: dict) -> pd.DataFrame:
    returnable = orders[orders["order_status"] == "Returned"].drop_duplicates("order_id")
    rows = []
    for i, order in enumerate(returnable.itertuples(index=False), start=1):
        return_id = f"RET{1000 + i}"
        try:
            order_dt = pd.to_datetime(order.order_date)
            return_date = order_dt + timedelta(days=int(rng.integers(2, 15)))
        except Exception:
            return_date = pd.NaT
        unit_price = price_lookup.get(order.product_id, np.nan)
        qty = abs(order.quantity) if pd.notna(order.quantity) else 1
        refund_amount = round(float(unit_price) * qty * (1 - order.discount), 2) if pd.notna(unit_price) else np.nan
        reason = random.choice(RETURN_REASONS)
        rows.append([return_id, order.order_id, return_date, reason, refund_amount])

    df = pd.DataFrame(rows, columns=[
        "return_id", "order_id", "return_date", "return_reason", "refund_amount",
    ])

    # a couple of negative refund amounts (entry errors)
    if len(df) > 3:
        neg_idx = df.sample(n=3, random_state=SEED).index
        df.loc[neg_idx, "refund_amount"] = -df.loc[neg_idx, "refund_amount"]

    return df


# ---------------------------------------------------------------------------
# marketing_campaigns
# ---------------------------------------------------------------------------

def generate_marketing_campaigns() -> pd.DataFrame:
    rows = []
    for i in range(1, N_CAMPAIGNS + 1):
        campaign_id = f"CMP{i:03d}"
        channel = CHANNELS[(i - 1) % len(CHANNELS)]
        start_date = random_date(HISTORY_START, TODAY - timedelta(days=20))
        end_date = start_date + timedelta(days=int(rng.integers(10, 45)))
        if channel == "Organic":
            spend = 0.0
        elif channel == "Email":
            spend = round(rng.uniform(2000, 15000), 2)
        else:
            spend = round(rng.uniform(20000, 250000), 2)
        impressions = int(rng.integers(5000, 500000))
        clicks = int(impressions * rng.uniform(0.01, 0.08))
        conversions = int(clicks * rng.uniform(0.02, 0.12))
        campaign_name = f"{channel} {start_date.strftime('%b %Y')} Push"
        rows.append([campaign_id, campaign_name, channel, start_date, end_date,
                      spend, impressions, clicks, conversions])

    return pd.DataFrame(rows, columns=[
        "campaign_id", "campaign_name", "channel", "start_date", "end_date",
        "spend", "impressions", "clicks", "conversions",
    ])


# ---------------------------------------------------------------------------
# website_sessions
# ---------------------------------------------------------------------------

def generate_website_sessions(customers: pd.DataFrame) -> pd.DataFrame:
    valid_customer_ids = customers["customer_id"].unique().tolist()
    rows = []
    for i in range(1, N_SESSIONS + 1):
        session_id = f"S{1000000 + i}"
        # ~20% of sessions are anonymous (no logged-in customer yet)
        customer_id = random.choice(valid_customer_ids) if rng.random() > 0.2 else None
        session_date = random_date(HISTORY_START, TODAY)
        channel = random.choices(CHANNELS, weights=[0.22, 0.18, 0.15, 0.15, 0.12, 0.18], k=1)[0]
        device = random.choices(DEVICES, weights=[0.62, 0.30, 0.08], k=1)[0]
        pages_viewed = int(rng.poisson(4)) + 1
        session_duration = round(float(rng.gamma(2, 90)), 1)  # seconds
        added_to_cart = rng.random() < (0.30 if pages_viewed > 3 else 0.10)
        purchased = added_to_cart and (rng.random() < 0.32)
        rows.append([session_id, customer_id, session_date, channel, device,
                      pages_viewed, session_duration, added_to_cart, purchased])

    df = pd.DataFrame(rows, columns=[
        "session_id", "customer_id", "session_date", "channel", "device",
        "pages_viewed", "session_duration", "added_to_cart", "purchased",
    ])

    # a few missing device values
    mask = df.sample(frac=0.01, random_state=SEED).index
    df.loc[mask, "device"] = np.nan

    return df


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print(f"Generating synthetic data (seed={SEED})...")

    customers = generate_customers()
    products = generate_products()
    orders, price_lookup = generate_orders(customers, products)
    payments = generate_payments(orders, price_lookup)
    returns = generate_returns(orders, price_lookup)
    campaigns = generate_marketing_campaigns()
    sessions = generate_website_sessions(customers)

    tables = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "payments": payments,
        "returns": returns,
        "marketing_campaigns": campaigns,
        "website_sessions": sessions,
    }

    for name, df in tables.items():
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {name:22s} -> {len(df):6d} rows -> {path}")

    print("\nIntentional data-quality issues injected (for the cleaning step to fix):")
    print("  customers: missing age (~2%), age outliers (6 rows), inconsistent state casing (~5%),")
    print("             missing city (~1%), 15 exact duplicate rows")
    print("  products:  inconsistent category casing (~8%), missing brand (~3%)")
    print("  orders:    8 negative quantities, 5 invalid order_date values, 4 orphan customer_id,")
    print("             4 orphan product_id, 20 exact duplicate rows")
    print("  payments:  ~1% missing amount")
    print("  returns:   3 negative refund_amount values")
    print("  website_sessions: ~1% missing device")
    print("\nDone.")


if __name__ == "__main__":
    main()
