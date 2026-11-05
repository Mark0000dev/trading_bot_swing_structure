"""Main loop: fetch candles for every token, run the strategy, save candles. Run: python -m scripts.run_bot"""
import os
import time
import traceback

from swingbot.config import CANDLES_DIR, POLL_INTERVAL_SEC, TOKENS
from swingbot.exchange.bingx_client import get_candles
from swingbot.pipeline import process_symbol


def run_once():
    os.makedirs(CANDLES_DIR, exist_ok=True)
    for token in TOKENS:
        try:
            candles_df = get_candles(token)
            if candles_df is None or candles_df.empty:
                continue

            process_symbol(candles_df, token)
            candles_df.sort_values("TimeStamp").to_csv(
                CANDLES_DIR / f"candles_df_{token}.csv", encoding="utf-8", index=False
            )
        except Exception:
            print(f"[BOT] error while processing {token}")
            traceback.print_exc()


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(POLL_INTERVAL_SEC)
