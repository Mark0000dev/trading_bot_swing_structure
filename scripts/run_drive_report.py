"""Uploads trade reports to Google Drive every 15 minutes.

Run: python -m scripts.run_drive_report paper      (table trading_paper)
     python -m scripts.run_drive_report third      (table third_option)
"""
import argparse
import time
import traceback

from swingbot.config import DRIVE_REPORT_INTERVAL_SEC
from swingbot.reports.google_drive import REPORTS, run_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", choices=REPORTS)
    parser.add_argument("--once", action="store_true", help="upload once and exit")
    args = parser.parse_args()

    while True:
        try:
            run_report(args.report)
        except Exception:
            traceback.print_exc()

        if args.once:
            break
        print("Следующее обновление через 15 минут", flush=True)
        time.sleep(DRIVE_REPORT_INTERVAL_SEC)
