# Swing Bot

Bot for BingX futures. Every hour it takes 15-minute candles, finds swings and trend changes,
paper-trades the signals, opens real orders on BingX and saves a chart for each token.

> ⚠️ The bot places **real orders** with your API keys.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in your keys
psql -U postgres -d swing_trade_edition_2 -f sql/create_tables.sql
```

Tokens and settings: `swingbot/config.py`.

## Run

```bash
python -m scripts.run_bot             # main bot
python -m scripts.run_telegram_bot    # reports to Telegram
python -m scripts.run_drive_report paper   # reports to Google Drive
```
