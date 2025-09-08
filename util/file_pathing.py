from pathlib import Path
import os
import numpy as np
import h5py
from datetime import datetime


def make_subject_directory(base_path, subject_id, exercise_set,
                           use_emg=True, use_eeg=True, save_counters=True):
    """
    Creates the subject folder structure under base_path/subject_id.
    exercise_set = 'A', 'B', or 'AB'
    """
    dir_path = Path(base_path) / str(subject_id)
    dir_path.mkdir(parents=True, exist_ok=True)

    want_A = exercise_set in ("A", "AB")
    want_B = exercise_set in ("B", "AB")

    def make_branch(kind: str):
        if want_A:
            (dir_path / kind / "EA" / "csv").mkdir(parents=True, exist_ok=True)
            (dir_path / kind / "EA" / "hdf5").mkdir(parents=True, exist_ok=True)
        if want_B:
            (dir_path / kind / "EB" / "csv").mkdir(parents=True, exist_ok=True)
            (dir_path / kind / "EB" / "hdf5").mkdir(parents=True, exist_ok=True)

    if use_emg: make_branch("emg")
    if use_eeg: make_branch("eeg")
    if save_counters: make_branch("counters")

    return dir_path


def save_channels(base_path, subject_id, type_string, group, perform_time,
                  suffix, data, labels, save_h5=True, date_str=None):
    """
    Save data + labels for emg/eeg/counters.
    group = 'EA' or 'EB'
    """
    date_str = date_str or datetime.today().strftime('%d-%m')
    perform_ms = int(perform_time * 1000)
    stem = f"{type_string}_data_{date_str}_{perform_ms}ms_{suffix}"

    root = Path(base_path) / str(subject_id) / type_string / group
    root.mkdir(parents=True, exist_ok=True)

    csv_data  = root / "csv"  / f"{stem}.csv"
    csv_label = root / "csv"  / f"{type_string}_label_{date_str}_{perform_ms}ms_{suffix}.csv"
    h5_path   = root / "hdf5" / f"{stem}.h5"

    np.savetxt(csv_data,  data.T, delimiter=",")
    np.savetxt(csv_label, labels.T, delimiter=",")

    if save_h5:
        h5_path.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(h5_path, "w") as hf:
            hf.create_dataset(f"{type_string}_data", data=data.T)
            hf.create_dataset(f"{type_string}_label", data=labels)
