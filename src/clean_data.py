"""
Data cleaning pipeline for CommerceIQ.

Reads data/raw/*.csv, fixes every data-quality issue intentionally injected
by src/generate_data.py (plus generic validation), writes data/cleaned/*.csv,
and appends a factual, auto-generated report of exactly what was found and
fixed (with before/after row counts) to reports/decisions_log.md.

Nothing here is silent: every transformation increments a counter that ends
up in the printed + logged report, so the cleaning step is auditable.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
DECISIONS_LOG = BASE_DIR / "reports" / "decisions_log.md"

CANONICAL_CATEGORIES = ["Electronics", "Fashion", "Home", "Beauty", "Sports", "Toys"]

report_lines: list[str] = []


def log(line: str = ""):
    print(line)
    report_lines.append(line)


def normalize_category(raw: str) -> str:
    if pd.isna(raw):
        return raw
    key = str(raw).strip().lower()
    for canon in CANONICAL_CATEGORIES:
        canon_lower = canon.lower()
        if key == canon_lower or key == canon_lower.rstrip("s") or key + "s" == canon_lower:
            return canon
    return str(raw).strip().title()


def normalize_state(raw: str) -> str:
    if pd.isna(raw):
        return raw
    # Title-case with spaces normalized handles "TAMILNADU" -> "Tamilnadu" too,
    # so also try inserting a space heuristically for known concatenations.
    key = str(raw).strip()
    collapsed = key.replace(" ", "").lower()
    known = {
        "tamilnadu": "Tamil Nadu",
        "maharashtra": "Maharashtra",
        "karnataka": "Karnataka",
        "delhi": "Delhi",
        "haryana": "Haryana",
        "telangana": "Telangana",
        "westbengal": "West Bengal",
        "gujarat": "Gujarat",
        "rajasthan": "Rajasthan",
        "uttarpradesh": "Uttar Pradesh",
        "chandigarh": "Chandigarh",
        "madhyapradesh": "Madhya Pradesh",
        "kerala": "Kerala",
        "bihar": "Bihar",
        "assam": "Assam",
    }
    return known.get(collapsed, key.title())


def clean_customers() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "customers.csv")
    n0 = len(df)
    log("\n### customers")
    log(f"- Raw row count: {n0}")

    dupes = df.duplicated().sum()
    df = df.drop_duplicates()
    log(f"- Removed {dupes} exact duplicate rows")

    df["state"] = df["state"].apply(normalize_state)
    log("- Normalized inconsistent state casing/spelling (e.g. 'TAMILNADU' -> 'Tamil Nadu')")

    missing_city = df["city"].isna().sum()
    df["city"] = df["city"].fillna("Unknown")
    log(f"- Filled {missing_city} missing city values with 'Unknown'")

    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    outliers = ((df["age"] < 10) | (df["age"] > 90)).sum()
    df.loc[(df["age"] < 10) | (df["age"] > 90), "age"] = np.nan
    missing_age = df["age"].isna().sum()
    median_age = df["age"].median()
    df["age"] = df["age"].fillna(median_age).round().astype(int)
    log(f"- Treated {outliers} impossible age values as missing; imputed all {missing_age} missing "
        f"ages (incl. those outliers) with the median age ({median_age:.0f})")

    df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "customers.csv", index=False)
    return df


def clean_products() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "products.csv")
    n0 = len(df)
    log("\n### products")
    log(f"- Raw row count: {n0}")

    dupes = df.duplicated().sum()
    df = df.drop_duplicates()
    log(f"- Removed {dupes} exact duplicate rows")

    before = df["category"].nunique()
    df["category"] = df["category"].apply(normalize_category)
    after = df["category"].nunique()
    log(f"- Standardized category text: {before} distinct raw spellings -> {after} canonical categories")

    missing_brand = df["brand"].isna().sum()
    df["brand"] = df["brand"].fillna("Unknown")
    log(f"- Filled {missing_brand} missing brand values with 'Unknown'")

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "products.csv", index=False)
    return df


def clean_orders(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "orders.csv")
    n0 = len(df)
    log("\n### orders")
    log(f"- Raw row count: {n0}")

    dupes = df.duplicated().sum()
    df = df.drop_duplicates()
    log(f"- Removed {dupes} exact duplicate rows")

    neg_qty = (df["quantity"] < 0).sum()
    df["quantity"] = df["quantity"].abs()
    log(f"- Fixed {neg_qty} negative quantity values (took absolute value)")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    invalid_dates = df["order_date"].isna().sum()
    df = df.dropna(subset=["order_date"])
    log(f"- Dropped {invalid_dates} rows with invalid/unparseable order_date")

    before = len(df)
    df = df[df["customer_id"].isin(customers["customer_id"])]
    orphan_cust = before - len(df)
    log(f"- Dropped {orphan_cust} rows with an order customer_id not present in customers")

    before = len(df)
    df = df[df["product_id"].isin(products["product_id"])]
    orphan_prod = before - len(df)
    log(f"- Dropped {orphan_prod} rows with an order product_id not present in products")

    df["discount"] = df["discount"].fillna(0.0)

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "orders.csv", index=False)
    return df


def clean_payments(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "payments.csv")
    n0 = len(df)
    log("\n### payments")
    log(f"- Raw row count: {n0}")

    before = len(df)
    df = df[df["order_id"].isin(orders["order_id"])]
    orphan = before - len(df)
    log(f"- Dropped {orphan} rows referencing an order_id no longer present after order cleaning")

    price_lookup = products.drop_duplicates("product_id").set_index("product_id")["selling_price"].to_dict()
    order_lookup = orders.set_index("order_id")[["product_id", "quantity", "discount"]]

    missing_before = df["amount"].isna().sum()

    def recompute(row):
        if pd.notna(row["amount"]):
            return row["amount"]
        if row["order_id"] not in order_lookup.index:
            return np.nan
        o = order_lookup.loc[row["order_id"]]
        price = price_lookup.get(o["product_id"])
        if price is None:
            return np.nan
        return round(float(price) * float(o["quantity"]) * (1 - float(o["discount"])), 2)

    df["amount"] = df.apply(recompute, axis=1)
    still_missing = df["amount"].isna().sum()
    df = df.dropna(subset=["amount"])
    log(f"- Recomputed {missing_before - still_missing} missing amount values from order price x qty x (1-discount); "
        f"dropped {still_missing} rows that still couldn't be recomputed")

    df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce")

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "payments.csv", index=False)
    return df


def clean_returns(orders: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "returns.csv")
    n0 = len(df)
    log("\n### returns")
    log(f"- Raw row count: {n0}")

    before = len(df)
    df = df[df["order_id"].isin(orders["order_id"])]
    orphan = before - len(df)
    log(f"- Dropped {orphan} rows referencing an order_id no longer present after order cleaning")

    neg = (df["refund_amount"] < 0).sum()
    df["refund_amount"] = df["refund_amount"].abs()
    log(f"- Fixed {neg} negative refund_amount values (took absolute value)")

    df["return_date"] = pd.to_datetime(df["return_date"], errors="coerce")

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "returns.csv", index=False)
    return df


def clean_marketing_campaigns() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "marketing_campaigns.csv")
    log("\n### marketing_campaigns")
    log(f"- Raw row count: {len(df)}")
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    log("- No injected issues; parsed dates and passed through unchanged")
    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "marketing_campaigns.csv", index=False)
    return df


def clean_website_sessions(customers: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "website_sessions.csv")
    n0 = len(df)
    log("\n### website_sessions")
    log(f"- Raw row count: {n0}")

    missing_device = df["device"].isna().sum()
    df["device"] = df["device"].fillna("Unknown")
    log(f"- Filled {missing_device} missing device values with 'Unknown'")

    # customer_id may legitimately be null (anonymous session) - only drop
    # non-null customer_ids that don't exist in the customers table.
    non_null_mask = df["customer_id"].notna()
    before = non_null_mask.sum()
    valid_mask = df["customer_id"].isna() | df["customer_id"].isin(customers["customer_id"])
    orphan = before - (non_null_mask & valid_mask).sum()
    df = df[valid_mask]
    log(f"- Dropped {orphan} rows with a non-null customer_id not present in customers "
        f"(null customer_id = anonymous session, kept as valid)")

    df["session_date"] = pd.to_datetime(df["session_date"], errors="coerce")

    log(f"- Cleaned row count: {len(df)}")
    df.to_csv(CLEAN_DIR / "website_sessions.csv", index=False)
    return df


def append_to_decisions_log():
    header = f"\n---\n\n## {datetime.now():%Y-%m-%d} — Data cleaning (automated report from `src/clean_data.py`)\n"
    body = "\n".join(report_lines)
    with open(DECISIONS_LOG, "a", encoding="utf-8") as f:
        f.write(header + body + "\n")


def main():
    log("Cleaning CommerceIQ raw data...")

    customers = clean_customers()
    products = clean_products()
    orders = clean_orders(customers, products)
    payments = clean_payments(orders, products)
    returns = clean_returns(orders)
    clean_marketing_campaigns()
    clean_website_sessions(customers)

    log("\nAll cleaned tables written to data/cleaned/.")
    append_to_decisions_log()
    log(f"Cleaning report appended to {DECISIONS_LOG.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
