import pandas as pd

from swingbot.config import ATR_PERIOD, ZIGZAG_ATR_MULTIPLIER


def add_percentage_change(df: pd.DataFrame) -> None:
    """Adds '% change' and 'Change' columns in place."""
    previous = df["Close"].shift()
    df["% change"] = round((df["Close"] - previous) / previous * 100, 3)
    df["Change"] = df["Close"] - previous


def add_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.DataFrame:
    """Returns a sorted copy with numeric OHLC and an 'ATR' column."""
    df = df.copy()
    df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])
    df = df.sort_values("TimeStamp").reset_index(drop=True)

    for col in ["Close", "High", "Low"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    true_range = pd.concat([
        df["High"] - df["Low"],
        abs(df["High"] - df["Close"].shift()),
        abs(df["Low"] - df["Close"].shift()),
    ], axis=1).max(axis=1)

    df["ATR"] = true_range.rolling(period).mean()
    return df


def zigzag_swings(df: pd.DataFrame, atr_multiplier: float = ZIGZAG_ATR_MULTIPLIER) -> pd.DataFrame:
    """Close-based zigzag: a swing is confirmed once price reverses by ATR * multiplier."""
    columns = ["time", "price", "type"]
    swings = []

    if df.empty:
        return pd.DataFrame(columns=columns)

    direction = 0
    high = low = df.iloc[0]["Close"]
    high_time = low_time = df.iloc[0]["TimeStamp"]

    for row in df.itertuples(index=False):
        close = row.Close
        time = row.TimeStamp
        threshold = row.ATR * atr_multiplier

        if pd.isna(close):
            continue

        if close >= high:
            high, high_time = close, time
        if close <= low:
            low, low_time = close, time

        if pd.isna(threshold) or threshold <= 0:
            continue

        if direction == 0:
            if high - close >= threshold:
                swings.append([high_time, high, "HIGH"])
                direction = -1
                low, low_time = close, time
            elif close - low >= threshold:
                swings.append([low_time, low, "LOW"])
                direction = 1
                high, high_time = close, time

        elif direction == 1:
            if close >= high:
                high, high_time = close, time
            elif high - close >= threshold:
                swings.append([high_time, high, "HIGH"])
                direction = -1
                low, low_time = close, time

        else:
            if close <= low:
                low, low_time = close, time
            elif close - low >= threshold:
                swings.append([low_time, low, "LOW"])
                direction = 1
                high, high_time = close, time

    # the still-forming swing
    if direction == 1 or (direction == 0 and high_time > low_time):
        last_swing = [high_time, high, "HIGH"]
    elif direction == -1 or (direction == 0 and low_time > high_time):
        last_swing = [low_time, low, "LOW"]
    else:
        last_swing = None

    if last_swing is not None and (
        not swings
        or swings[-1][0] != last_swing[0]
        or swings[-1][2] != last_swing[2]
    ):
        swings.append(last_swing)

    swings_df = pd.DataFrame(swings, columns=columns)
    if swings_df.empty:
        return swings_df

    return (
        swings_df.drop_duplicates(["time", "type"], keep="last")
        .sort_values("time")
        .reset_index(drop=True)
    )
