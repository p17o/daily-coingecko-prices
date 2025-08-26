
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict

import pandas as pd
import requests

# ----------------------------
# Configuration
# ----------------------------
API_KEY = os.environ.get("COINGECKO_API_KEY")
COIN_ID = os.environ.get("COIN_ID", "nym")
CURRENCIES = [c.strip().lower() for c in os.environ.get("CURRENCIES", "usd,eur,chf").split(",") if c.strip()]
START_BASELINE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # First-run baseline
DATA_DIR = os.environ.get("DATA_DIR", "data")
API_URL_TEMPLATE = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart/range"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


# ----------------------------
# Helpers
# ----------------------------
def _csv_path_for(currency: str, start_dt: datetime) -> str:
    """Build the CSV path using coin + currency + the *start* year."""
    year = start_dt.year
    stem = f"{COIN_ID}_{currency}_{year}_hourly_price_data_provided_by_coingecko"
    return os.path.join(DATA_DIR, f"{stem}.csv")


def _read_last_timestamp(csv_path: str) -> Optional[datetime]:
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path, usecols=["datetime"])
    except Exception:
        df = pd.read_csv(csv_path)
        if "datetime" not in df.columns:
            return None

    dt = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    if dt.isna().all():
        return None
    last_ts = dt.max()
    return last_ts.to_pydatetime()


def _decide_window(last_ts: Optional[datetime]) -> Tuple[datetime, datetime]:
    """Return (start, end) in UTC following the new logic:
    - If CSV doesn't exist (last_ts is None): start = 1 Jan 2025 00:00:00 UTC; end = start + 89 days.
    - If CSV exists: start = last_ts; end = start + 89 days.
    Note: we do NOT clamp to 'now'; CoinGecko will return up to the present if 'end' is in the future.
    """
    if last_ts is None:
        start = START_BASELINE
    else:
        start = last_ts.astimezone(timezone.utc)

    end = start + timedelta(days=89)
    return start, end


def _fetch_prices(coin_id: str, currency: str, start: datetime, end: datetime) -> List[Dict]:
    url = API_URL_TEMPLATE.format(coin=coin_id)
    params = {
        "vs_currency": currency,
        "from": int(start.timestamp()),
        "to": int(end.timestamp()),
    }
    headers = {}
    if API_KEY:
        headers["x-cg-demo-api-key"] = API_KEY

    r = requests.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    prices = data.get("prices", []) if isinstance(data, dict) else []
    rows: List[Dict] = []
    for ts_ms, price in prices:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        rows.append({"coin_symbol": coin_id, "datetime": dt_str, f"price_{currency}": float(price)})
    return rows


def _append_to_csv(csv_path: str, rows: List[Dict]) -> int:
    new_df = pd.DataFrame(rows)
    if new_df.empty:
        return 0

    if not os.path.exists(csv_path):
        new_df.to_csv(csv_path, index=False)
        return len(new_df)

    existing = pd.read_csv(csv_path)
    # If schemas differ (e.g., adding new currency column), outer-join via concat and de-dup on datetime
    combined = pd.concat([existing, new_df], ignore_index=True, sort=False)

    combined["datetime_parsed"] = pd.to_datetime(combined["datetime"], utc=True, errors="coerce")
    combined = combined.dropna(subset=["datetime_parsed"]).sort_values("datetime_parsed")
    combined = combined.drop_duplicates(subset=["datetime_parsed"], keep="last").drop(columns=["datetime_parsed"])

    # Reorder columns: datetime, coin_symbol, then others
    cols = list(combined.columns)
    ordered = [c for c in ["datetime", "coin_symbol"] if c in cols] + [c for c in cols if c not in ("datetime", "coin_symbol")]
    combined = combined[ordered]

    combined.to_csv(csv_path, index=False)
    return len(new_df)


def process_currency(currency: str) -> None:
    # Decide CSV path using the intended start year; must first determine start based on last_ts (which needs a path)
    # For first run when the file doesn't exist, we use baseline to name the file by 2025.
    tentative_path = _csv_path_for(currency, START_BASELINE)
    last_ts = _read_last_timestamp(tentative_path)

    # If the file existed, the 'start' year (for naming) should be last_ts.year; otherwise 2025.
    if last_ts is None:
        naming_start = START_BASELINE
        csv_path = tentative_path
    else:
        naming_start = last_ts
        csv_path = _csv_path_for(currency, naming_start)

    start, end = _decide_window(last_ts)

    # Log selection
    log = {
        "currency": currency,
        "csv_path": csv_path,
        "existing_last_timestamp_utc": last_ts.isoformat() if last_ts else None,
        "request_start_utc": start.isoformat(),
        "request_end_utc": end.isoformat(),
        "request_span_days": (end - start).total_seconds() / 86400.0,
    }
    print(json.dumps(log, indent=2))

    rows = _fetch_prices(COIN_ID, currency, start, end)
    appended = _append_to_csv(csv_path, rows)
    print(f"[{currency}] fetched {len(rows)} rows; appended {appended} rows -> {csv_path}")


def main():
    for currency in CURRENCIES:
        try:
            process_currency(currency)
        except Exception as e:
            print(f"Error processing {currency}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
