"""Paper trading on closed candles; state is kept in a JSON file, closed trades go to `trading_paper`."""
import json
import os

import pandas as pd

from swingbot.config import PAPER_FEE_PCT, PAPER_MAX_POSITIONS, PAPER_MAX_SIGNAL_AGE, PAPER_STATE_FILE
from swingbot.database import insert_paper_trade


def load_state() -> dict:
    if os.path.exists(PAPER_STATE_FILE):
        with open(PAPER_STATE_FILE) as f:
            return json.load(f)
    return {"positions": {}, "last_signal": {}}


def save_state(state: dict) -> None:
    os.makedirs(PAPER_STATE_FILE.parent, exist_ok=True)
    with open(PAPER_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def calc_pnl(direction: str, entry_price: float, exit_price: float) -> float:
    if direction == "LONG":
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return pnl - 2 * PAPER_FEE_PCT


def track_structure_break(candles_df, transitions, symbol):
    candles = candles_df.sort_values("TimeStamp").reset_index(drop=True)
    if len(candles) < 3 or not transitions:
        return

    closed = candles.iloc[:-1]  # the last candle is still forming
    last = closed.iloc[-1]
    price, now = float(last["Close"]), pd.Timestamp(last["TimeStamp"])

    forming_ts = candles["TimeStamp"].iloc[-1]
    signals = transitions[:-1] if transitions[-1][0] >= forming_ts else transitions
    if not signals:
        return
    bos_time, trend, _level = signals[-1]

    state = load_state()
    pos = state["positions"].get(symbol)

    if pos and pos["direction"] != trend:
        entry_price = pos["entry_price"]
        entry_time = pd.Timestamp(pos["entry_time"])
        pnl = calc_pnl(pos["direction"], entry_price, price)

        try:
            insert_paper_trade(symbol, pos["direction"], entry_time, now, entry_price, price,
                               pnl, (now - entry_time).total_seconds() / 3600)
        except Exception as e:
            print(f"[PAPER] DB error {symbol}: {e}")
            return

        print(f'[PAPER] CLOSE {pos["direction"]} {symbol} PnL {pnl:+.2f}%')
        del state["positions"][symbol]
        pos = None

    age = len(closed) - 1 - closed["TimeStamp"].searchsorted(bos_time)
    if (not pos
            and state["last_signal"].get(symbol) != str(bos_time)
            and age <= PAPER_MAX_SIGNAL_AGE
            and len(state["positions"]) < PAPER_MAX_POSITIONS):
        state["positions"][symbol] = {
            "direction": trend,
            "entry_time": str(now),
            "entry_price": price,
        }
        state["last_signal"][symbol] = str(bos_time)
        print(f"[PAPER] OPEN {trend} {symbol} @ {price}")

    save_state(state)
