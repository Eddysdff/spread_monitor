#!/usr/bin/env python3
import os
import json
from curl_cffi import requests

# --- Configuration ---
COOKIE_PATH = os.path.join(os.path.dirname(__file__), "cookie.json")
QUOTE_SIMPLE_URL = "https://omni.variational.io/api/quotes/simple"

def load_json(path):
    try:
        if not os.path.exists(path): return {}
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}

def main():
    # 1. Load Cookies
    cookies = load_json(COOKIE_PATH)
    if not cookies:
        print(f"Warning: {COOKIE_PATH} not found or empty.")

    # 2. Initialize Session
    session = requests.Session(impersonate="chrome110")
    headers = {
        "content-type": "application/json",
        "origin": "https://omni.variational.io",
        "referer": "https://omni.variational.io/markets"
    }
    session.headers.update(headers)
    session.cookies.update(cookies)

    # 3. BTC Instrument Definition
    btc_instrument = {
        "underlying": "BTC",
        "instrument_type": "perpetual_future",
        "settlement_asset": "USDC",
        "funding_interval_s": 3600
    }

    # 4. Continuous Loop
    print(f"Monitoring BTC quotes (Press Ctrl+C to stop)...")
    try:
        while True:
            try:
                payload = {"instrument": btc_instrument, "qty": "0.001"}
                response = session.post(QUOTE_SIMPLE_URL, json=payload, timeout=10)
                
                if response.status_code != 200:
                    print(f"Error: API returned status code {response.status_code}")
                    time.sleep(5)
                    continue

                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                
                bid = float(data.get("bid", 0))
                ask = float(data.get("ask", 0))
                
                if bid == 0 or ask == 0:
                    print("Received invalid bid/ask from API.")
                    time.sleep(5)
                    continue

                mid = (bid + ask) / 2
                spread_abs = ask - bid
                spread_pct = (spread_abs / mid) * 100
                spread_bps = spread_pct * 100

                # 5. Output Results in one line for continuous monitoring
                print(f"Bid: {bid:.2f} | Ask: {ask:.2f} | Mid: {mid:.2f} | Spread: {spread_abs:.2f} | Bps: {spread_bps:.2f}")

            except Exception as e:
                print(f"An error occurred: {e}")
                import time
                time.sleep(5)
            
            import time
            time.sleep(1) # Poll every 1 seconds

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

if __name__ == "__main__":
    main()