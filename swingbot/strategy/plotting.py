"""Chart: price, swings, trend ranges, premium/discount zones, trailing stop and backtest stats."""
import matplotlib

matplotlib.use("Agg")  # files only, no GUI

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from swingbot.config import GRAPHS_DIR, SL_ATR_BUFFER  # noqa: E402
from swingbot.utils import hourly_output_path  # noqa: E402

GREEN, RED, YELLOW = "#00e676", "#ff4560", "#ffeb3b"
PANEL, BORDER, TEXT = "#202938", "#475569", "#e2e8f0"


def trailing_stop(candles_df, swings_df, start, end, trend):
    """Swing-based trailing stop for one range. Returns (points, hit_point | None)."""
    swings_df = swings_df.copy()
    swings_df["time"] = pd.to_datetime(swings_df["time"])

    stop_type, extreme_type = ("LOW", "HIGH") if trend == "LONG" else ("HIGH", "LOW")
    stop_swings = swings_df[swings_df["type"] == stop_type]
    extreme_swings = swings_df[swings_df["type"] == extreme_type]

    stops_before = stop_swings[stop_swings["time"] <= start]
    extremes_before = extreme_swings[extreme_swings["time"] <= start]
    candles = candles_df[(candles_df["TimeStamp"] >= start) & (candles_df["TimeStamp"] <= end)]

    if stops_before.empty or extremes_before.empty or candles.empty:
        return [], None

    extreme_price = extremes_before["price"].iloc[-1]
    extreme_time = extremes_before["time"].iloc[-1]

    atr = candles["ATR"].iloc[0]
    atr = 0 if pd.isna(atr) else atr
    stop_price = stops_before["price"].iloc[-1]
    stop = stop_price - atr * SL_ATR_BUFFER if trend == "LONG" else stop_price + atr * SL_ATR_BUFFER

    points = []
    for time, close, atr in zip(candles["TimeStamp"], candles["Close"], candles["ATR"]):
        atr = 0 if pd.isna(atr) else atr

        if (trend == "LONG" and close < stop) or (trend == "SHORT" and close > stop):
            points.append([time, stop])
            return points, [time, stop]

        new_extreme = close > extreme_price if trend == "LONG" else close < extreme_price
        if new_extreme:
            pullback = stop_swings[(stop_swings["time"] > extreme_time) & (stop_swings["time"] < time)]
            if not pullback.empty:
                if trend == "LONG":
                    stop = max(stop, pullback["price"].min() - atr * SL_ATR_BUFFER)
                else:
                    stop = min(stop, pullback["price"].max() + atr * SL_ATR_BUFFER)
            extreme_price, extreme_time = close, time

        points.append([time, stop])

    return points, None


def draw_stop_loss(ax, candles_df, swings_df, ranges):
    first_line = first_hit = True

    for start, end, trend in ranges[:-1]:
        points, hit = trailing_stop(candles_df, swings_df, pd.to_datetime(start), pd.to_datetime(end), trend)
        if not points:
            continue

        ax.step([p[0] for p in points], [p[1] for p in points], where="post", color=YELLOW,
                linewidth=1.8, label="Stop loss" if first_line else None, zorder=5)
        first_line = False

        if hit:
            ax.scatter(hit[0], hit[1], color=YELLOW, marker="X", s=110, edgecolors="black",
                       linewidths=0.7, label="Stop hit" if first_hit else None, zorder=9)
            first_hit = False


def draw_premium_discount(ax, candles_df):
    high, low = candles_df["Close"].max(), candles_df["Close"].min()
    if high <= low:
        return
    middle = (high + low) / 2
    axis = ax.get_yaxis_transform()

    ax.axhspan(middle, high, color="#a78bfa", alpha=0.07, zorder=0)
    ax.axhspan(low, middle, color="#38bdf8", alpha=0.07, zorder=0)
    ax.axhline(high, color="#a78bfa", linewidth=0.9, alpha=0.6, zorder=1)
    ax.axhline(low, color="#38bdf8", linewidth=0.9, alpha=0.6, zorder=1)
    ax.axhline(middle, color="#f8fafc", linestyle="-.", linewidth=1.3, alpha=0.85, label="EQ 0.5", zorder=3)

    label = dict(transform=axis, fontsize=9, fontweight="bold", ha="right", zorder=8)
    ax.text(0.995, (middle + high) / 2, "PREMIUM", color="#a78bfa", va="center", **label)
    ax.text(0.995, (middle + low) / 2, "DISCOUNT", color="#38bdf8", va="center", **label)
    ax.text(0.995, middle, f"0.5  {middle:g}", color="#f8fafc", va="bottom", **label)


def _stats_text(all_pnl, duration):
    hours = [item[2].total_seconds() / 3600 for item in duration]
    total = len(all_pnl)
    wins = sum(p > 0 for p in all_pnl)
    losses = sum(p < 0 for p in all_pnl)
    win_rate = wins / total * 100 if total else 0
    avg_pnl = sum(all_pnl) / total if total else 0
    avg_hold = sum(hours) / len(hours) if hours else 0

    return (
        f"TRADES     {total}\n"
        f"WINS / LOSS  {wins} / {losses}\n"
        f"WIN RATE   {win_rate:.1f}%\n"
        f"TOTAL PnL  {sum(all_pnl):+.2f}%\n"
        f"AVG PnL    {avg_pnl:+.2f}%\n"
        f"AVG HOLD   {avg_hold:.1f} h"
    )


def build_graph(candles_df, ranges, symbol, significant_highs, significant_lows, swings_df, backtest):
    candles_df = candles_df.copy()
    swings_df = swings_df.copy()
    candles_df["TimeStamp"] = pd.to_datetime(candles_df["TimeStamp"])
    swings_df["time"] = pd.to_datetime(swings_df["time"])
    candles_df = candles_df.sort_values("TimeStamp").reset_index(drop=True)
    swings_df = swings_df.sort_values("time").reset_index(drop=True)
    candles_df["Close"] = pd.to_numeric(candles_df["Close"])
    swings_df["price"] = pd.to_numeric(swings_df["price"])

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(18, 9))
    fig.patch.set_facecolor("#10141c")
    ax.set_facecolor("#161b26")

    # price
    ax.plot(candles_df["TimeStamp"], candles_df["Close"], color=TEXT, linewidth=1.5, label="Close price", zorder=2)
    ax.fill_between(candles_df["TimeStamp"], candles_df["Close"], candles_df["Close"].min(),
                    color="#94a3b8", alpha=0.06)
    draw_premium_discount(ax, candles_df)

    # trend ranges
    for start, end, trend in ranges:
        start, end = pd.to_datetime(start), pd.to_datetime(end)
        if start >= end:
            continue
        color = GREEN if trend == "LONG" else RED
        ax.axvspan(start, end, color=color, alpha=0.10, zorder=0)
        ax.text(start + (end - start) / 2, 0.97, trend, transform=ax.get_xaxis_transform(), color=color,
                fontsize=9, fontweight="bold", ha="center", va="top", alpha=0.9)

    # swings
    highs = swings_df[swings_df["type"] == "HIGH"]
    lows = swings_df[swings_df["type"] == "LOW"]
    ax.scatter(highs["time"], highs["price"], color=GREEN, marker="^", s=65, edgecolors="black",
               linewidths=0.5, label="Swing High", zorder=4)
    ax.scatter(lows["time"], lows["price"], color=RED, marker="v", s=65, edgecolors="black",
               linewidths=0.5, label="Swing Low", zorder=4)
    if not swings_df.empty:
        last = swings_df.iloc[-1]
        ax.scatter(last["time"], last["price"], color="#ffd166", marker="*", s=240, edgecolors="black",
                   linewidths=0.7, label="Latest swing", zorder=6)

    # untouched levels
    right_edge = candles_df["TimeStamp"].iloc[-1]
    for levels, color in [(significant_highs, GREEN), (significant_lows, RED)]:
        for time, price, _ in levels:
            ax.hlines(y=price, xmin=pd.to_datetime(time), xmax=right_edge, color=color,
                      linestyle="--", linewidth=1.1, alpha=0.75)

    # trade exits with PnL
    all_pnl = []
    for trades, color, marker in [(backtest["long_pnl"], GREEN, "^"), (backtest["short_pnl"], RED, "v")]:
        for start, end, pnl in trades:
            end = pd.to_datetime(end)
            exit_rows = candles_df.loc[candles_df["TimeStamp"] == end, "Close"]
            if exit_rows.empty or candles_df.loc[candles_df["TimeStamp"] == pd.to_datetime(start)].empty:
                continue
            exit_price = exit_rows.iloc[0]
            all_pnl.append(pnl)

            ax.scatter(end, exit_price, color=color, marker=marker, s=100, edgecolors="white",
                       linewidths=0.6, zorder=7)
            ax.annotate(f"{pnl:+.2f}%", (end, exit_price), xytext=(0, 12 if pnl >= 0 else -17),
                        textcoords="offset points", color=color, fontsize=8, fontweight="bold",
                        ha="center", zorder=8)

    # max adverse excursion
    for mae_data, color in [(backtest["mae_long"], "#ffb74d"), (backtest["mae_short"], "#ba68c8")]:
        for time, price, _ in mae_data:
            ax.scatter(pd.to_datetime(time), price, color=color, marker="x", s=75, linewidths=2, zorder=6)

    ax.text(0.015, 0.96, _stats_text(all_pnl, backtest["duration"]), transform=ax.transAxes, fontsize=10,
            fontfamily="monospace", color=TEXT, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.7", facecolor=PANEL, edgecolor=BORDER, alpha=0.95), zorder=10)

    ax.set_title(f"{symbol}  |  SWING STRUCTURE & BACKTEST", fontsize=17, fontweight="bold",
                 color="white", pad=20)
    ax.set_xlabel("Date", color="#cbd5e1", labelpad=10)
    ax.set_ylabel("Close Price", color="#cbd5e1", labelpad=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    ax.grid(True, color=BORDER, linestyle=":", linewidth=0.6, alpha=0.45)
    ax.tick_params(colors="#94a3b8")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BORDER)

    draw_stop_loss(ax, candles_df, swings_df, ranges)

    ax.legend(loc="upper right", frameon=True, facecolor=PANEL, edgecolor=BORDER, fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()

    path = hourly_output_path(GRAPHS_DIR, f"graph_{symbol}", "png")
    fig.savefig(path, dpi=250, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path
