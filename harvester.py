#!/usr/bin/env python3
import os
import time
import argparse
from tqdm import tqdm

import config
import db
import agencies
import engines
from harvest import get_pdf_links, launch_downloads


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def matrix_state_menu():
    clear()
    print("\033[92m")
    print("\u2554" + "\u2550" * 78 + "\u2557")
    print("\u2551   JEDISEC MULTI-STATE PDF HARVESTER \u2013 PLUGIN EDITION" + " " * 21 + "\u2551")
    print("\u255a" + "\u2550" * 78 + "\u255d\033[0m")
    print(f"\033[96m  Engines available: {', '.join(engines.available_engines())}"
          f" | Concurrent downloads: {config.MAX_CONCURRENT_DOWNLOADS}\033[0m")
    print("\033[93m")
    for code, state in sorted(agencies.all_states().items()):
        print(f"  \033[96m[{code}]\033[0m  {state.state_name}  ({len(state.agencies)} agencies)")
    print("\033[92m")
    print("  [A]  \u2192  SWEEP EVERY STATE, EVERY AGENCY (MEGA SWEEP)")
    print("  [Q]  \u2192  Exit")
    print("\033[0m" + "\u2500" * 80)
    return input("\033[92mPick a state \u2192 \033[0m").strip().upper()


def matrix_agency_menu(state):
    clear()
    print("\033[92m")
    print(f"\u2554{'\u2550'*78}\u2557")
    print(f"\u2551  {state.state_name.upper():74} \u2551")
    print(f"\u255a{'\u2550'*78}\u255d\033[0m")
    print("\033[93m")
    for code, agency in sorted(state.agencies.items()):
        print(f"  \033[96m[{code}]\033[0m  {agency.name}")
    print("\033[92m")
    print("  [Z]  \u2192  SWEEP ALL AGENCIES IN THIS STATE")
    print("  [B]  \u2192  Back to state list")
    print("\033[0m" + "\u2500" * 80)
    return input("\033[92mThe swamp awaits... \u2192 \033[0m").strip().upper()


def _within_interval(state_code, agency_code, min_interval_hours):
    if min_interval_hours is None:
        return False
    last = db.get_last_run(state_code, agency_code)
    if not last:
        return False
    last_ts = time.mktime(time.strptime(last, '%Y-%m-%d %H:%M:%S'))
    return (time.time() - last_ts) / 3600.0 < min_interval_hours


def sweep_state(state, incremental=False, min_interval_hours=None, overall_bar=None):
    for code, agency in state.agencies.items():
        if _within_interval(state.state_code, code, min_interval_hours):
            print(f"  \033[90m[{agency.name}] ran within the last {min_interval_hours}h \u2014 skipping.\033[0m")
            if overall_bar:
                overall_bar.update(1)
            continue

        print(f"\n\033[95m{'='*25} [{state.state_code}/{code}] {agency.name} {'='*25}\033[0m")
        pdfs = get_pdf_links(agency.query, agency.name, incremental=incremental)
        if pdfs:
            launch_downloads(pdfs, state.state_code, code, agency.name)
        else:
            db.record_agency_run(state.state_code, code, agency.name, docs_found=0, docs_new=0)
        if overall_bar:
            overall_bar.update(1)


def mega_sweep(incremental=False, min_interval_hours=None):
    all_states = agencies.all_states()
    total_agencies = sum(len(s.agencies) for s in all_states.values())
    overall_bar = tqdm(total=total_agencies, desc="\033[95mTOTAL MEGA-SWEEP PROGRESS\033[0m",
                        position=config.MAX_CONCURRENT_DOWNLOADS, leave=True, unit="agency",
                        dynamic_ncols=True)
    for state in all_states.values():
        sweep_state(state, incremental=incremental, min_interval_hours=min_interval_hours, overall_bar=overall_bar)
    overall_bar.close()


def interactive():
    print("\033[92m\n> Welcome to the JediSec multi-state matrix. PDFs incoming.\033[0m")
    time.sleep(1.0)
    while True:
        choice = matrix_state_menu()
        if choice == "Q":
            print("\033[91m> Gator's gone.\033[0m")
            break
        elif choice == "A":
            mega_sweep()
            break
        elif choice in agencies.all_states():
            state = agencies.get_state(choice)
            while True:
                ac = matrix_agency_menu(state)
                if ac == "B":
                    break
                elif ac == "Z":
                    overall_bar = tqdm(total=len(state.agencies),
                                        desc=f"\033[95m{state.state_name} SWEEP PROGRESS\033[0m",
                                        position=config.MAX_CONCURRENT_DOWNLOADS, leave=True,
                                        unit="agency", dynamic_ncols=True)
                    sweep_state(state, overall_bar=overall_bar)
                    overall_bar.close()
                    break
                elif ac in state.agencies:
                    agency = state.agencies[ac]
                    print(f"\n\033[96m> Diving into {agency.name}...\033[0m")
                    pdfs = get_pdf_links(agency.query, agency.name)
                    if pdfs:
                        launch_downloads(pdfs, state.state_code, ac, agency.name)
                    else:
                        db.record_agency_run(state.state_code, ac, agency.name, 0, 0)
                else:
                    print("\033[91m> Invalid path.\033[0m")
                    time.sleep(1)
        else:
            print("\033[91m> Invalid path.\033[0m")
            time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description="JediSec multi-state PDF harvester")
    ap.add_argument("--incremental", action="store_true",
                     help="Only keep documents not already fingerprinted/seen; bail out of a "
                          "query early once results are clearly all previously-known.")
    ap.add_argument("--all", action="store_true", help="Sweep every state/agency non-interactively.")
    ap.add_argument("--state", help="Sweep a single state code (e.g. LA) non-interactively.")
    ap.add_argument("--min-interval-hours", type=float, default=None,
                     help="Skip agencies whose last run was within this many hours (scheduler use).")
    args = ap.parse_args()

    if args.all:
        mega_sweep(incremental=args.incremental, min_interval_hours=args.min_interval_hours)
    elif args.state:
        state = agencies.get_state(args.state.upper())
        overall_bar = tqdm(total=len(state.agencies), desc=f"\033[95m{state.state_name} SWEEP\033[0m",
                            position=config.MAX_CONCURRENT_DOWNLOADS, leave=True, unit="agency")
        sweep_state(state, incremental=args.incremental, min_interval_hours=args.min_interval_hours,
                    overall_bar=overall_bar)
        overall_bar.close()
    else:
        interactive()


if __name__ == "__main__":
    main()
