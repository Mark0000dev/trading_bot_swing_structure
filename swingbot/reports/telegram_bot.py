"""Telegram bot that sends the last 50 paper trades as a CSV every 15 minutes."""
import asyncio
from datetime import datetime
from io import BytesIO

from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile, Message

from swingbot.config import TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_REPORT_INTERVAL_SEC
from swingbot.database import read_sql

dp = Dispatcher()


@dp.message()
async def handle_message(message: Message):
    print(f"Получено сообщение от {message.from_user.id}: {message.text}")


def get_csv_from_db() -> BufferedInputFile:
    df = read_sql("""
        SELECT symbol, direction, pnl_percentage, time_open, time_close
        FROM paper_trading
        ORDER BY id DESC
        LIMIT 50
    """)
    buffer = BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    return BufferedInputFile(buffer.getvalue(), filename="last_50_trades.csv")


async def send_reports(bot: Bot):
    while True:
        try:
            document = await asyncio.to_thread(get_csv_from_db)
            await bot.send_document(chat_id=TELEGRAM_CHAT_ID, document=document,
                                    caption=f"{datetime.now():%Y-%m-%d %H:%M} last 50 orders")
            print("CSV sent")
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(TELEGRAM_REPORT_INTERVAL_SEC)


async def main():
    if not TELEGRAM_API_TOKEN or not TELEGRAM_CHAT_ID:
        raise SystemExit("Set TELEGRAM_API_TOKEN and TELEGRAM_CHAT_ID in .env")

    async with Bot(token=TELEGRAM_API_TOKEN) as bot:
        await bot.delete_webhook(drop_pending_updates=False)
        await asyncio.gather(dp.start_polling(bot), send_reports(bot))
