"""All PostgreSQL access. Table definitions: sql/create_tables.sql."""
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import Json

from swingbot.config import DB_CONFIG


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def save_trade(symbol, direction, entry_time, exit_time,
               entry_price, exit_price, pnl_pct, mae_pct, duration_hours):
    """Backtest trade -> swing_trades_table."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO public.swing_trades_table (
                symbol, direction, entry_time, exit_time,
                entry_price, exit_price, pnl_pct, mae_pct, duration_hours,
                checked_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, direction, entry_time, exit_time) DO NOTHING
        """, (
            symbol,
            direction,
            entry_time.time(),
            exit_time.time(),
            float(entry_price),
            float(exit_price),
            float(pnl_pct),
            float(mae_pct) if mae_pct is not None else 0.0,
            float(duration_hours),
            datetime.now(),
        ))


def insert_paper_trade(symbol, direction, time_open, time_closed,
                       price_open, price_closed, pnl_percentage, duration_hours):
    """Closed paper trade -> trading_paper."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO trading_paper (
                symbol, direction, time_open, time_closed,
                price_open, price_closed, pnl_percentage, duration_hours
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            symbol, direction,
            time_open.to_pydatetime(), time_closed.to_pydatetime(),
            float(price_open), float(price_closed),
            float(pnl_percentage), float(duration_hours),
        ))


def save_bingx_log(symbol, direction, action, status, message=None, response=None):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO public.bingx_order_logs
                (symbol, direction, action, status, message, exchange_response)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            symbol, direction, action, status, message,
            Json(response) if response is not None else None,
        ))


def read_sql(query: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()
