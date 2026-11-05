"""Run: python -m scripts.run_telegram_bot"""
import asyncio

from swingbot.reports.telegram_bot import main

if __name__ == "__main__":
    asyncio.run(main())
