"""Deletes the graphs folder from GRAPHS_KEEP_DAYS days ago. Run: python -m scripts.cleanup_graphs"""
import os
import shutil
import time

import pandas as pd

from swingbot.config import GRAPHS_DIR, GRAPHS_KEEP_DAYS


def cleanup_loop():
    deleted = False
    while True:
        day = (pd.Timestamp.now() - pd.Timedelta(days=GRAPHS_KEEP_DAYS)).strftime("%Y-%m-%d")
        folder = GRAPHS_DIR / day

        if os.path.exists(folder) and not deleted:
            shutil.rmtree(folder)
            print(pd.Timestamp.now(), f"{folder} папка удалена")
            deleted = True
        elif not os.path.exists(folder):
            print(pd.Timestamp.now(), f"{folder} папка не найдена")

        if deleted:
            time.sleep(24 * 60 * 60)
            deleted = False
        else:
            time.sleep(60 * 60)


if __name__ == "__main__":
    cleanup_loop()
