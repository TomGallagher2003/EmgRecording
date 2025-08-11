from pathlib import Path
import numpy as np

def save_buffer(buf, path: str | Path):
    """buf can be `bytes`, `bytearray`, or a NumPy uint8 array."""
    p = Path(path)
    if isinstance(buf, (bytes, bytearray, memoryview)):
        p.write_bytes(buf)
    elif isinstance(buf, np.ndarray):
        p.write_bytes(np.ascontiguousarray(buf).tobytes())
    else:
        raise TypeError(f"Unsupported type: {type(buf)}")

def load_buffer(path: str | Path) -> bytes:
    return Path(path).read_bytes()

