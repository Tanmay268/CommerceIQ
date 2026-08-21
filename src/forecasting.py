"""
Optional advanced module: monthly revenue forecasting.

Per the PDF (section 22), forecasting is explicitly an add-on, not the
foundation - so this module reads from Postgres and writes to its own
table (monthly_revenue_forecast) without any other module depending on it.

Method: Holt's linear trend exponential smoothing (statsmodels), compared
against a 3-month moving-average baseline. With only 12 months of history
there isn't enough data for reliable seasonal decomposition, so a seasonal
model (e.g. Prophet/SARIMA) would be overfitting - trend-only smoothing is
the honest choice at this data volume.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent.parent
FIG_DIR = BASE_DIR / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

FORECAST_MONTHS = 3
ANALYSIS_DATE = pd.Timestamp("2026-08-21")  # "today" for the synthetic dataset


def get_monthly_revenue(engine) -> pd.Series:
    df = pd.read_sql(
        """
        SELECT DATE_TRUNC('month', o.order_date)::date AS month,
               SUM(o.quantity * p.selling_price * (1 - o.discount)) AS revenue
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        WHERE o.order_status <> 'Cancelled'
        GROUP BY 1
        ORDER BY 1
        """,
        engine,
    )
    df["month"] = pd.to_datetime(df["month"])
    series = df.set_index("month")["revenue"]
    series.index = series.index.to_period("M").to_timestamp()

    # Drop the current, still-in-progress month: the dataset only has orders
    # up to ANALYSIS_DATE, so the latest month is a partial month and would
    # look like an artificial revenue dip to the trend model if left in.
    current_month = ANALYSIS_DATE.to_period("M").to_timestamp()
    if series.index[-1] == current_month:
        series = series.iloc[:-1]

    # Symmetrically, the dataset's history starts on ANALYSIS_DATE minus 365
    # days (not the 1st of a month), so the very first monthly bucket is
    # also partial - drop it for the same reason.
    history_start_month = (ANALYSIS_DATE - pd.Timedelta(days=365)).to_period("M").to_timestamp()
    if series.index[0] == history_start_month:
        series = series.iloc[1:]

    return series


def moving_average_baseline(series: pd.Series, window: int = 3) -> float:
    return series.tail(window).mean()


def forecast_holt(series: pd.Series, periods: int) -> pd.Series:
    # With only ~11 data points the optimizer sometimes reports non-
    # convergence (ConvergenceWarning) even though it still returns a
    # sane, stable set of smoothing parameters - expected at this sample
    # size and not a correctness issue; suppressed here rather than
    # silenced globally so it stays visible if it starts happening
    # elsewhere.
    import warnings
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model = ExponentialSmoothing(series, trend="add", seasonal=None, initialization_method="estimated")
        fit = model.fit()
    forecast = fit.forecast(periods)
    return forecast


def plot(series: pd.Series, forecast: pd.Series):
    plt.figure(figsize=(10, 5))
    plt.plot(series.index, series.values, marker="o", label="Actual monthly revenue")
    plt.plot(forecast.index, forecast.values, marker="o", linestyle="--", color="orange",
              label="Forecast (Holt linear trend)")
    plt.title("CommerceIQ — Monthly Revenue & 3-Month Forecast")
    plt.xlabel("Month")
    plt.ylabel("Revenue (INR)")
    plt.legend()
    plt.tight_layout()
    out_path = FIG_DIR / "revenue_forecast.png"
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"Forecast chart saved to {out_path}")


def main():
    engine = get_engine()
    series = get_monthly_revenue(engine)
    print(f"Loaded {len(series)} months of actual revenue.")

    baseline = moving_average_baseline(series)
    print(f"3-month moving-average baseline (naive next-month estimate): INR {baseline:,.0f}")

    forecast = forecast_holt(series, FORECAST_MONTHS)
    print("\nHolt linear-trend forecast, next {} months:".format(FORECAST_MONTHS))
    print(forecast)

    plot(series, forecast)

    actual_rows = pd.DataFrame({
        "forecast_month": series.index.date,
        "method": "actual",
        "forecast_revenue": series.values,
        "is_actual": True,
    })
    forecast_rows = pd.DataFrame({
        "forecast_month": forecast.index.date,
        "method": "holt_linear_trend",
        "forecast_revenue": forecast.values,
        "is_actual": False,
    })

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM monthly_revenue_forecast"))
    pd.concat([actual_rows, forecast_rows], ignore_index=True).to_sql(
        "monthly_revenue_forecast", engine, if_exists="append", index=False
    )
    print("\nmonthly_revenue_forecast table populated (actuals + forecast).")


if __name__ == "__main__":
    main()
