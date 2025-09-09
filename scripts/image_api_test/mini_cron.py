from __future__ import annotations
from datetime import datetime, time as dtime, timedelta
from typing import Callable, Optional
import os
import time


def run_every(
    fn: Callable[[], None],
    interval: timedelta,
    start: Optional[dtime] = None,
    end: Optional[dtime] = None,
    sentinel_path: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """在可選的時段窗內，每隔 interval 執行一次 fn；若 sentinel 不存在則不執行。"""
    while True:
        if sentinel_path and not os.path.exists(sentinel_path):
            time.sleep(interval.total_seconds())
            continue
        now = datetime.now().time()
        if start and end:
            in_window = (
                (start <= now <= end) if start <= end else (now >= start or now <= end)
            )
            if not in_window:
                time.sleep(interval.total_seconds())
                continue
        if verbose:
            print(f"[mini-cron] {now} - {fn.__name__}")
        try:
            fn()
        except Exception as e:
            print(f"\n[mini-cron] error: {e}")
        if verbose:
            print(f"\n[mini-cron] {now} - {fn.__name__} done")
            print(
                f"[mini-cron] {now} - {fn.__name__} sleep {interval.total_seconds()} seconds"
            )
        time.sleep(interval.total_seconds())


# 使用範例：
if __name__ == "__main__":

    def task() -> None:
        os.system("python t0_compact_base64_new.py | ./plot_base64.sh")

    run_every(
        fn=task,
        interval=timedelta(minutes=1),
        start=dtime(9, 30),  # 9:30
        end=dtime(15, 0),  # 15:00
        # sentinel_path=os.path.expanduser("~/.mini-cron.enabled"),
        # verbose=True,
    )
