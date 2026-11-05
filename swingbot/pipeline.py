"""Full processing of one symbol: indicators -> swings -> structure -> trading -> backtest -> chart."""
import pandas as pd

from swingbot.config import SWINGS_DIR
from swingbot.strategy.backtest import run_backtest
from swingbot.strategy.indicators import add_atr, add_percentage_change, zigzag_swings
from swingbot.strategy.plotting import build_graph
from swingbot.strategy.structure import (
    alternate_swings, clean_inputs, find_transitions, log_structure_status,
    significant_levels, trend_ranges,
)
from swingbot.trading.paper_trader import track_structure_break
from swingbot.trading.virtual_trader import update_virtual_trade
from swingbot.utils import hourly_output_path


def process_symbol(candles_df: pd.DataFrame, symbol: str) -> None:
    add_percentage_change(candles_df)  # in place: also ends up in the saved candles CSV

    df = add_atr(candles_df)
    atr = df["ATR"].iloc[-1]

    swings_df = zigzag_swings(df)
    swings_df.to_csv(hourly_output_path(SWINGS_DIR, f"swings_df_{symbol}", "csv"),
                     encoding="utf-8", index=False)

    candles, swings = clean_inputs(df, swings_df)
    if candles.empty or swings.empty:
        return

    swings = alternate_swings(swings)
    if len(swings) < 4:
        return

    significant_highs, significant_lows = significant_levels(candles, swings)
    transitions = find_transitions(candles, swings)
    if not transitions:
        return

    track_structure_break(candles, transitions, symbol)
    update_virtual_trade(candles, transitions, symbol, atr)

    ranges = trend_ranges(candles, transitions)
    backtest = run_backtest(candles, ranges, symbol)
    build_graph(candles, ranges, symbol, significant_highs, significant_lows, swings, backtest)
    log_structure_status(swings, symbol)
