"""Trades every trend flip at the BOS candle (table `third_option`) and mirrors it on BingX."""
import pandas as pd

from swingbot.database import get_connection
from swingbot.trading.live_orders import open_bingx_position


def update_virtual_trade(candles_df, transitions, symbol, atr):
    if candles_df.empty or not transitions:
        return

    candles = candles_df.copy()
    candles["TimeStamp"] = pd.to_datetime(candles["TimeStamp"])
    candles["Close"] = pd.to_numeric(candles["Close"], errors="coerce")
    candles = (
        candles.dropna(subset=["TimeStamp", "Close"])
        .sort_values("TimeStamp")
        .drop_duplicates("TimeStamp", keep="last")
        .reset_index(drop=True)
    )
    if candles.empty:
        return

    bos_time = pd.to_datetime(transitions[-1][0])
    new_direction = transitions[-1][1]
    if new_direction not in ("LONG", "SHORT"):
        return

    entry_rows = candles.loc[candles["TimeStamp"] == bos_time, "Close"]
    if entry_rows.empty:
        print(f"[PAPER] {symbol}: no candle at transition time {bos_time}")
        return
    new_entry_price = float(entry_rows.iloc[-1])

    previous_candles = candles[candles["TimeStamp"] < bos_time]
    if previous_candles.empty:
        exit_time = exit_price = None
    else:
        exit_time = previous_candles.iloc[-1]["TimeStamp"]
        exit_price = float(previous_candles.iloc[-1]["Close"])

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, direction, time_open, price_open
            FROM public.third_option
            WHERE symbol = %s AND time_closed IS NULL
            ORDER BY time_open DESC
            LIMIT 1
        """, (symbol,))
        open_trade = cur.fetchone()

        if open_trade:
            trade_id, old_direction, time_open, price_open = open_trade
            price_open = float(price_open)

            if old_direction == new_direction or bos_time <= pd.Timestamp(time_open):
                return

            if exit_time is None:
                print(f"[PAPER] {symbol}: cannot close the existing trade; "
                      "there is no candle before the transition.")
                return

            if old_direction == "LONG":
                pnl_pct = (exit_price - price_open) / price_open * 100
            else:
                pnl_pct = (price_open - exit_price) / price_open * 100
            duration_hours = (pd.Timestamp(exit_time) - pd.Timestamp(time_open)).total_seconds() / 3600

            cur.execute("""
                UPDATE public.third_option
                SET time_closed = %s, price_closed = %s, pnl_percentage = %s, duration_hours = %s
                WHERE id = %s AND time_closed IS NULL
            """, (exit_time.to_pydatetime(), exit_price, float(pnl_pct), float(duration_hours), trade_id))

            print(f"[PAPER] CLOSED {symbol} {old_direction} entry={price_open} "
                  f"exit={exit_price} PnL={pnl_pct:+.2f}%")

        cur.execute("""
            INSERT INTO public.third_option
                (symbol, direction, time_open, time_closed,
                 price_open, price_closed, pnl_percentage, duration_hours)
            VALUES (%s, %s, %s, NULL, %s, NULL, NULL, NULL)
        """, (symbol, new_direction, bos_time.to_pydatetime(), new_entry_price))

        print(f"[PAPER] OPENED {symbol} {new_direction} time={bos_time} price={new_entry_price}")

    response = open_bingx_position(symbol, new_direction, atr)
    print(f"[BINGX] {symbol}: {response}")
