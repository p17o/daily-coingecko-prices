import requests
import csv
import os
import time
from datetime import datetime, timedelta

api_key = os.environ.get("COINGECKO_API_KEY")

coins = [
    "cardano", "algorand", "cosmos", "avalanche-2", "bitcoin-cash", "bitcoin", "polkadot",
    "ethereum", "ethereum-2", "ethereum-wormhole", "kava", "kusama", "chainlink", "litecoin",
    "terra-luna", "terra-luna-2", "matic-network", "pol", "nym", "oxt", "solana", "storj",
    "strike", "uniswap", "tether", "terrausd", "tezos"
]

def get_last_date_in_csv(filename):
    if not os.path.isfile(filename):
        return None
    with open(filename, "r", newline="") as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)
        if len(rows) < 2:
            return None
        last_row = rows[-1]
        try:
            return datetime.strptime(last_row[0], "%d-%m-%Y").date()
        except Exception:
            return None

def request_price(coin, date_str, api_key):
    headers = {"x-cg-demo-api-key": api_key}
    for attempt in range(10):
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin}/history"
            params = {"date": date_str, "localization": "false"}
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                prices = data.get("market_data", {}).get("current_price", {})
                usd = prices.get("usd", "")
                eur = prices.get("eur", "")
                chf = prices.get("chf", "")
                return [date_str, coin, usd, eur, chf]
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)
    print(f"Failed to fetch data for {coin} on {date_str}. Exiting.")
    return None

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
max_lookback = today - timedelta(days=360)
year = yesterday.year

for coin in coins:
    filename = f"{coin}_{year}_daily_price_data_provided_by_coingecko.csv"
    last_date = get_last_date_in_csv(filename)
    if last_date == yesterday:
        print(f"{coin}: Up-to-date. Skipping.")
        continue
    # Determine next day to fetch, respecting max_lookback
    if last_date:
        next_date = last_date + timedelta(days=1)
        if next_date < max_lookback:
            next_date = max_lookback
    else:
        next_date = max_lookback
    # Only fetch up to yesterday
    if next_date > yesterday:
        print(f"{coin}: No missing dates. Skipping.")
        continue
    date_str = next_date.strftime("%d-%m-%Y")
    row = request_price(coin, date_str, api_key)
    if row is None:
        print(f"{coin}: Aborting due to failure on {date_str}.")
        exit(1)
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["date", "coin", "usd", "eur", "chf"])
        writer.writerow(row)
    print(f"{coin}: Added data for {date_str}.")

print("Run complete for all coins.")
