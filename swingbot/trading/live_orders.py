"""Real market orders on BingX: close the opposite position, open a new one sized by ATR."""
from swingbot.config import (
    POSITION_BASE_USDT, POSITION_MAX_USDT, POSITION_MIN_USDT, POSITION_REFERENCE_ATR_PCT,
)
from swingbot.database import save_bingx_log
from swingbot.exchange.bingx_client import close_all_positions, get_price, has_position, place_market_order


def calculate_position_size(price: float, atr: float) -> float:
    """Higher volatility -> smaller position, clamped to [MIN, MAX] USDT."""
    atr_pct = atr / price * 100
    usdt_amount = POSITION_BASE_USDT * POSITION_REFERENCE_ATR_PCT / atr_pct
    return max(POSITION_MIN_USDT, min(usdt_amount, POSITION_MAX_USDT))


def open_bingx_position(symbol: str, new_direction: str, atr: float):
    old_direction = "LONG" if new_direction == "SHORT" else "SHORT"

    if has_position(symbol, old_direction):
        if not close_all_positions(symbol):
            save_bingx_log(symbol, old_direction, "CLOSE", "FAILED", "Failed to close old position")
            return None
        save_bingx_log(symbol, old_direction, "CLOSE", "SUCCESS")

    price = get_price(symbol)
    usdt_amount = calculate_position_size(price, atr)
    quantity = usdt_amount / price
    side = "BUY" if new_direction == "LONG" else "SELL"

    response = place_market_order(symbol, side, new_direction, quantity)

    if response.get("code") == 0:
        save_bingx_log(symbol, new_direction, "OPEN", "SUCCESS",
                       message=f"Position size: {usdt_amount:.2f} USDT", response=response)
        print(f"[BINGX] OPENED {symbol} {new_direction} SIZE={usdt_amount:.2f} USDT")
    else:
        save_bingx_log(symbol, new_direction, "OPEN", "FAILED", message=str(response), response=response)

    return response
