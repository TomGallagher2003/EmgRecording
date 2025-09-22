"""Utilities for saving and loading raw binary buffers.

This module provides simple helper functions to write raw data buffers
(e.g., EMG/EEG byte streams) to disk and read them back into memory.
"""

from pathlib import Path
import numpy as np


def save_buffer(buf, path: str | Path) -> None:
    """Save a raw buffer to disk.

    Args:
        buf (bytes | bytearray | memoryview | np.ndarray):
            The raw buffer to save. Can be:
            - `bytes`, `bytearray`, or `memoryview` (written directly)
            - A NumPy uint8 array (converted to contiguous bytes)
        path (str | Path): Destination file path.

    Raises:
        TypeError: If `buf` is not one of the supported types.
    """
    p = Path(path)
    if isinstance(buf, (bytes, bytearray, memoryview)):
        p.write_bytes(buf)
    elif isinstance(buf, np.ndarray):
        p.write_bytes(np.ascontiguousarray(buf).tobytes())
    else:
        raise TypeError(f"Unsupported type: {type(buf)}")


def load_buffer(path: str | Path) -> bytes:
    """Load a raw buffer from disk.

    Args:
        path (str | Path): Path to the file containing raw bytes.

    Returns:
        bytes: The contents of the file as a byte string.
    """
    return Path(path).read_bytes()
