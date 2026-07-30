#!/usr/bin/env python3
"""Scheduled incremental updates.

Two ways to use this:

1. Cron / Termux:Boot (recommended -- don't fight your OS's scheduler):
     0 */6 * * *  cd /path/to/jedisec_harvester && python3 harvester.py --incremental --all

2. Standalone long-running loop, if you'd rather not rely on cron:
     python3 scheduler.py --interval-hours 6
"""
import argparse
import time
import subprocess
import sys
import os


def run_once(min_interval_hours=None):
    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "harvester.py"),
           "--incremental", "--all"]
    if min_interval_hours is not None:
        cmd += ["--min-interval-hours", str(min_interval_hours)]
    subprocess.run(cmd, check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval-hours", type=float, default=6.0,
                     help="How often to trigger an incremental sweep.")
    args = ap.parse_args()
    print(f"[scheduler] running incremental sweep every {args.interval_hours}h "
          f"(Ctrl+C to stop; cron/Termux:Boot is the more idiomatic way to do this unattended)")
    while True:
        run_once(min_interval_hours=args.interval_hours)
        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    main()
