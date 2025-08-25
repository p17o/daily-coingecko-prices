# Daily CoinGecko Prices

This repository uses GitHub Actions to fetch daily prices for selected cryptocurrencies from [CoinGecko v3.0.1 API](https://docs.coingecko.com/v3.0.1/reference/introduction), and saves them as separate CSV files per coin and per year.

## How it works

- **Workflow** runs every hour at the 55th minute (UTC).
- **Python script** (`fetch_coingecko.py`) queries the next missing day's prices for each coin, catching up from 360 days ago until the present.
- **Output files:**  
  Each coin's prices for a given year are stored in  
  `{coin}_{year}_daily_price_data_provided_by_coingecko.csv`  
  Example: `bitcoin_2025_daily_price_data_provided_by_coingecko.csv`

- **CSV columns:** `date, coin, usd, eur, chf`

## API Key Setup

This workflow requires a CoinGecko API key.  
1. Go to your repository’s **Settings > Secrets and variables > Actions**.
2. Add a new repository secret named `COINGECKO_API_KEY`.
3. Paste your CoinGecko API key as the value.

The workflow will automatically use this key for authenticated requests.

## Setup

No setup required when using GitHub Actions. For local runs:

1. Install Python 3 and `requests` library:
   ```sh
   pip install requests
   ```
2. Set the API key environment variable:
   ```sh
   export COINGECKO_API_KEY=your_key_here
   ```
3. Run:
   ```sh
   python fetch_coingecko.py
   ```

## Notes on API Limits

- CoinGecko limits: **10,000 requests/month**, **30 requests/minute**.
- The script fetches one missing day per coin per run, so it will catch up safely within the allowed quota.
- Once caught up, it will fetch only yesterday's prices for each coin.

## License

MIT
