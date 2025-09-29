#!/usr/bin/env python3
# verify_packet_loss.py — start/end check only, headerless CSV, fixed modulo 2^16

import os, glob
import numpy as np
import pandas as pd
from tabulate import tabulate

DATA_DIR   = "./test_recordings/with_counters/test_A/counters/EA/csv"       # <- set your folder
FILE_GLOB  = "counters_data_*.csv"   # e.g. "counters_data_*.csv"
EEG_REPEAT = 4
MOD        = 2**16                   # fixed 16-bit counters

def load_three_cols(path: str):
    df = pd.read_csv(path, header=None)
    if df.shape[1] < 3:
        raise ValueError(f"{os.path.basename(path)}: expected 3 columns, got {df.shape[1]}")
    a = df.iloc[:, 0].to_numpy(np.int64)
    b = df.iloc[:, 1].to_numpy(np.int64)
    c = df.iloc[:, 2].to_numpy(np.int64)
    return a, b, c, df.shape[0]

def wrap_delta(first: int, last: int, modulo: int = MOD) -> int:
    return (int(last) - int(first)) % modulo

def check_sync_emg(delta: int, rows: int) -> tuple[bool, int, int]:
    expected = (rows - 1) % MOD
    return (delta == expected), expected, (delta - expected)

def check_eeg(delta: int, rows: int) -> tuple[bool, str, int]:
    exp_floor = (rows - 1) // EEG_REPEAT
    exp_exact = rows // EEG_REPEAT
    ok = (delta == exp_floor) or (delta == exp_exact)
    # pick the closer expectation for the diff display
    diff_floor = delta - exp_floor
    diff_exact = delta - exp_exact
    diff = diff_floor if abs(diff_floor) <= abs(diff_exact) else diff_exact
    exp_str = f"{exp_floor} | {exp_exact}"
    return ok, exp_str, diff

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, FILE_GLOB)))
    if not files:
        print(f"No files found in {os.path.abspath(DATA_DIR)} matching {FILE_GLOB}")
        return

    rows_out = []
    ok_sync = ok_emg = ok_eeg = 0

    for path in files:
        try:
            sync, emg, eeg, nrows = load_three_cols(path)
        except Exception as e:
            print(f"[WARN] load failed {os.path.basename(path)}: {e}")
            continue

        d_sync = wrap_delta(sync[0], sync[-1])
        d_emg  = wrap_delta(emg[0],  emg[-1])
        d_eeg  = wrap_delta(eeg[0],  eeg[-1])
        print(sync[0], sync[-1], d_eeg)

        s_ok, s_exp, s_diff = check_sync_emg(d_sync, nrows)
        m_ok, m_exp, m_diff = check_sync_emg(d_emg,  nrows)
        e_ok, e_exp_str, e_diff = check_eeg(d_eeg, nrows)

        ok_sync += int(s_ok); ok_emg += int(m_ok); ok_eeg += int(e_ok)

        rows_out.append([
            os.path.basename(path), nrows,
            d_sync, s_exp, ("OK" if s_ok else "FAIL"), s_diff,
            d_emg,  m_exp, ("OK" if m_ok else "FAIL"), m_diff,
            d_eeg,  e_exp_str, ("OK" if e_ok else "FAIL"), e_diff,
        ])

    headers = [
        "file", "rows",
        "syncΔ", "sync_expected", "sync_status", "sync_diff",
        "emgΔ",  "emg_expected",  "emg_status",  "emg_diff",
        "eegΔ",  "eeg_expected(floor|exact)", "eeg_status", "eeg_diff",
    ]

    print("\n=== Start–End Counter Check (fixed modulo 2^16) ===")
    print(tabulate(rows_out, headers=headers, tablefmt="github"))
    print("\nSummary:")
    print(f"SYNC OK: {ok_sync}/{len(rows_out)}  |  EMG OK: {ok_emg}/{len(rows_out)}  |  EEG OK: {ok_eeg}/{len(rows_out)}")
    print(f"(EEG repeats={EEG_REPEAT}, modulo={MOD})")

if __name__ == "__main__":
    main()
