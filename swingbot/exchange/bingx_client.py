"""Minimal signed client for the BingX perpetual swap API."""
import hmac
import time
import urllib.parse
from hashlib import sha256

import pandas as pd
import requests

from swingbot.config import BINGX_API_KEY, BINGX_API_URL, BINGX_SECRET_KEY, CANDLES

TIMEOUT = 10


def get_sign(api_secret: str, payload: str) -> str:
    return hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"),
                    digestmod=sha256).hexdigest()


def parse_params(params: dict) -> tuple[str, str]:
    """Returns (string to sign, url query string), both with a timestamp."""
    keys = sorted(params)
    timestamp = str(int(time.time() * 1000))

    params_str = "&".join(f"{k}={params[k]}" for k in keys)
    params_str = f"{params_str}&timestamp={timestamp}" if params_str else f"timestamp={timestamp}"

    needs_encoding = "[" in params_str or "{" in params_str
    url_parts = [
        f"{k}={urllib.parse.quote(str(params[k]), safe='') if needs_encoding else params[k]}"
        for k in keys
    ]
    url_str = "&".join(url_parts)
    url_str = f"{url_str}&timestamp={timestamp}" if url_str else f"timestamp={timestamp}"

    return params_str, url_str


def send_request(method: str, path: str, params: dict | None = None) -> dict:
    params_str, url_str = parse_params(params or {})
    url = f"{BINGX_API_URL}{path}?{url_str}&signature={get_sign(BINGX_SECRET_KEY, params_str)}"

    response = requests.request(method, url, headers={"X-BX-APIKEY": BINGX_API_KEY},
                                data={}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


# --- market data ---------------------------------------------------------

def get_candles(symbol: str) -> pd.DataFrame | None:
    data = send_request("GET", "/openApi/swap/v3/quote/klines", {
        "symbol": symbol,
        "interval": CANDLES["interval"],
        "timezone": CANDLES["timezone"],
        "limit": CANDLES["limit"],
    })
    if data.get("code") != 0:
        print(f"[BINGX] klines error {symbol}: {data}")
        return None

    candles = [{
        "TimeStamp": pd.to_datetime(row["time"], unit="ms"),
        "Open": float(row["open"]),
        "Close": float(row["close"]),
        "High": float(row["high"]),
        "Low": float(row["low"]),
    } for row in data["data"]]
    return pd.DataFrame(candles)


def get_price(symbol: str) -> float:
    response = requests.get(f"{BINGX_API_URL}/openApi/swap/v2/quote/price",
                            params={"symbol": symbol}, timeout=TIMEOUT)
    return float(response.json()["data"]["price"])


# --- trading -------------------------------------------------------------

def place_market_order(symbol: str, side: str, position_side: str, quantity: float) -> dict:
    return send_request("POST", "/openApi/swap/v2/trade/order", {
        "symbol": symbol,
        "side": side,
        "positionSide": position_side,
        "type": "MARKET",
        "quantity": quantity,
    })


def has_position(symbol: str, position_side: str) -> bool:
    response = send_request("GET", "/openApi/swap/v2/user/positions", {"symbol": symbol})
    return any(
        p["symbol"] == symbol
        and p["positionSide"] == position_side
        and float(p["positionAmt"]) != 0
        for p in response["data"]
    )


def close_all_positions(symbol: str) -> bool:
    response = send_request("POST", "/openApi/swap/v2/trade/closeAllPositions", {"symbol": symbol})
    if response.get("code") == 0:
        print(f"[BINGX] CLOSED {symbol}")
        return True
    print(f"[BINGX] CLOSE ERROR: {response}")
    return False
