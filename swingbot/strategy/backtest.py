"""Backtest of trend ranges: PnL and MAE per trade, every trade stored in the DB."""
import pandas as pd

from swingbot.database import save_trade


def _close_at(candles_df: pd.DataFrame, ts):
    rows = candles_df.loc[candles_df["TimeStamp"] == ts, "Close"]
    return None if rows.empty else rows.iloc[0]


def run_backtest(candles_df: pd.DataFrame, ranges, symbol: str) -> dict:
    result = {"long_pnl": [], "short_pnl": [], "mae_long": [], "mae_short": [], "duration": []}

    for start, end, trend in ranges:
        entry_price = _close_at(candles_df, start)
        exit_price = _close_at(candles_df, end)
        if entry_price is None or exit_price is None:
            continue

        is_long = trend == "LONG"
        pnl = ((exit_price - entry_price) if is_long else (entry_price - exit_price)) / entry_price * 100
        result["long_pnl" if is_long else "short_pnl"].append([start, end, pnl])

        inside = candles_df.loc[
            (candles_df["TimeStamp"] > start) & (candles_df["TimeStamp"] < end),
            ["TimeStamp", "Close"],
        ]

        mae_pct = 0.0
        if not inside.empty:
            worst = inside.loc[inside["Close"].idxmin() if is_long else inside["Close"].idxmax()]
            worst_price = worst["Close"]
            mae_pct = ((worst_price - entry_price) if is_long else (entry_price - worst_price)) / entry_price * 100
            result["mae_long" if is_long else "mae_short"].append([worst["TimeStamp"], worst_price, mae_pct])

        save_trade(
            symbol=symbol,
            direction=trend,
            entry_time=start,
            exit_time=end,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pct=pnl,
            mae_pct=mae_pct,
            duration_hours=(end - start).total_seconds() / 3600,
        )

    result["duration"] = [[start, end, end - start] for start, end, _ in ranges]
    return result
