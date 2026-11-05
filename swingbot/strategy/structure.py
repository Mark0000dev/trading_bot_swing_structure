"""Market structure: cleaned swings, break-of-structure transitions and trend ranges."""
import os
from datetime import datetime

import pandas as pd

from swingbot.config import STRUCTURES_FILE


def clean_inputs(candles_df: pd.DataFrame, swings_df: pd.DataFrame):
    candles_df = candles_df.copy()
    swings_df = swings_df.copy()

    candles_df["TimeStamp"] = pd.to_datetime(candles_df["TimeStamp"])
    swings_df["time"] = pd.to_datetime(swings_df["time"])
    candles_df["Close"] = pd.to_numeric(candles_df["Close"], errors="coerce")
    swings_df["price"] = pd.to_numeric(swings_df["price"], errors="coerce")

    candles_df = (
        candles_df.dropna(subset=["TimeStamp", "Close"])
        .sort_values("TimeStamp")
        .drop_duplicates("TimeStamp", keep="last")
        .reset_index(drop=True)
    )
    swings_df = (
        swings_df.dropna(subset=["time", "price"])
        .sort_values("time")
        .drop_duplicates(["time", "type"], keep="last")
        .reset_index(drop=True)
    )
    return candles_df, swings_df


def alternate_swings(swings_df: pd.DataFrame) -> pd.DataFrame:
    """Keeps HIGH/LOW strictly alternating, choosing the more extreme of repeated types."""
    clean = []
    for swing in swings_df.to_dict("records"):
        if swing["type"] not in ("HIGH", "LOW"):
            continue
        if not clean:
            clean.append(swing)
            continue

        previous = clean[-1]
        if swing["type"] == previous["type"]:
            more_extreme = (
                (swing["type"] == "HIGH" and swing["price"] >= previous["price"])
                or (swing["type"] == "LOW" and swing["price"] <= previous["price"])
            )
            if more_extreme:
                clean[-1] = swing
        else:
            clean.append(swing)

    return pd.DataFrame(clean)


def significant_levels(candles_df: pd.DataFrame, swings_df: pd.DataFrame):
    """Swing highs/lows that price has not traded through yet."""
    last_price = candles_df["Close"].iloc[-1]
    highs, lows = [], []

    for swing in swings_df.to_dict("records"):
        future = candles_df[candles_df["TimeStamp"] > swing["time"]]["Close"]

        if swing["type"] == "HIGH":
            if not (future > swing["price"]).any() and last_price < swing["price"]:
                highs.append([swing["time"], swing["price"], "HIGH"])
        elif not (future < swing["price"]).any() and last_price > swing["price"]:
            lows.append([swing["time"], swing["price"], "LOW"])

    return highs, lows


def find_transitions(candles_df: pd.DataFrame, swings_df: pd.DataFrame):
    """Break-of-structure events where the trend flips: [bos_time, 'LONG'|'SHORT', level]."""
    bos_events = []

    for i in range(3, len(swings_df)):
        current_time = swings_df.iloc[i]["time"]
        seen = swings_df.iloc[:i + 1]
        highs = seen[seen["type"] == "HIGH"]
        lows = seen[seen["type"] == "LOW"]

        if len(highs) < 2 or len(lows) < 2:
            continue

        h1, h2 = highs["price"].iloc[-2:]
        l1, l2 = lows["price"].iloc[-2:]

        if h2 > h1 and l2 > l1:
            new_trend, level = "LONG", h2
        elif h2 < h1 and l2 < l1:
            new_trend, level = "SHORT", l2
        else:
            continue

        future = candles_df[candles_df["TimeStamp"] > current_time]
        broken = (future[future["Close"] > level] if new_trend == "LONG"
                  else future[future["Close"] < level])
        if broken.empty:
            continue

        bos_events.append([broken.iloc[0]["TimeStamp"], new_trend, level])

    bos_events.sort(key=lambda x: x[0])

    transitions = []
    current_trend = None
    for bos_time, new_trend, level in bos_events:
        if new_trend != current_trend:
            transitions.append([bos_time, new_trend, level])
            current_trend = new_trend

    return transitions


def trend_ranges(candles_df: pd.DataFrame, transitions):
    """[start, end, trend] for every trend leg; the last one runs to the latest candle."""
    ranges = []
    for i, (start, trend, _level) in enumerate(transitions):
        if i + 1 < len(transitions):
            previous_candles = candles_df[candles_df["TimeStamp"] < transitions[i + 1][0]]
            if previous_candles.empty:
                continue
            end = previous_candles.iloc[-1]["TimeStamp"]
        else:
            end = candles_df["TimeStamp"].iloc[-1]

        if start <= end:
            ranges.append([start, end, trend])
    return ranges


# --- structure history (CSV log) -----------------------------------------

STRUCTURE_COLUMNS = ["Дата", "Symbol", "Структура", "Свинг"]


def log_structure_status(swings_df: pd.DataFrame, symbol: str):
    """Appends the current structure of the last 4 swings to the history CSV."""
    if len(swings_df) < 4:
        return None

    s0, s1, s2, s3 = (swings_df.iloc[-k]["price"] for k in range(1, 5))

    last_structure = None
    if os.path.exists(STRUCTURES_FILE):
        history = pd.read_csv(STRUCTURES_FILE)
        previous = history.loc[history["Symbol"] == symbol, "Структура"]
        if len(previous):
            last_structure = previous.iloc[-1]

    if s0 > s1 and s2 > s3:
        status = "LONG" if last_structure in ("LONG", "Начало LONG") else "Начало LONG"
    elif s0 < s1 and s2 < s3:
        status = "SHORT" if last_structure in ("SHORT", "Начало SHORT") else "Начало SHORT"
    else:
        status = "Нет четкой структуры"

    os.makedirs(STRUCTURES_FILE.parent, exist_ok=True)
    pd.DataFrame([[datetime.now(), symbol, status, s0]], columns=STRUCTURE_COLUMNS).to_csv(
        STRUCTURES_FILE,
        mode="a",
        header=not os.path.exists(STRUCTURES_FILE),
        index=False,
    )
    return status
