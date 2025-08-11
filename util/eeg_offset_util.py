# util/eeg_offset_util.py
from typing import Optional, Tuple
import numpy as np

FRAME_SIZE = 298  # 38*2 + 70*3 + 6*2

def _chan_off_w(ch: int) -> Tuple[int, int]:
    if 1 <= ch <= 38:    return ((ch - 1) * 2, 2)
    if 39 <= ch <= 108:  return (38*2 + (ch - 39) * 3, 3)
    if 109 <= ch <= 114: return (38*2 + 70*3 + (ch - 109) * 2, 2)
    raise ValueError(f"Channel {ch} out of range 1..114")

def _read_series(base_off: int, buf: bytes, ch: int, n_frames: int) -> Tuple[np.ndarray, int]:
    off, w = _chan_off_w(ch)
    vals = np.empty(n_frames, dtype=np.uint32)
    if w == 2:
        for i in range(n_frames):
            p = base_off + off + i * FRAME_SIZE
            vals[i] = int.from_bytes(buf[p:p+2], "big", signed=False)
    else:  # w == 3, big-endian
        for i in range(n_frames):
            p = base_off + off + i * FRAME_SIZE
            b = buf[p:p+3]
            vals[i] = (b[0] << 16) | (b[1] << 8) | b[2]
    return vals, w

def _score_periodic_counter(vals: np.ndarray, width_bytes: int, period: int) -> Tuple[float, int]:
    if vals.size < 2:
        return 0.0, 0
    mod = 1 << (8 * width_bytes)
    steps = (np.diff(vals.astype(np.uint64)) % mod).astype(np.uint32)
    best_score, best_phase = -1.0, 0
    for phi in range(period):
        exp_plus1 = (np.arange(steps.size) % period) == phi
        good = ((steps == 1) & exp_plus1) | ((steps == 0) & ~exp_plus1)
        score = float(np.mean(good))
        if score > best_score:
            best_score, best_phase = score, phi
    return best_score, best_phase

def offset_with_eeg(
    data_buffer: bytes,
    *,
    # fast-path defaults (keep small for speed)
    bytes_to_scan: Optional[int] = 8_192,
    max_frames_to_check: int = 120,
    min_frames_required: int = 24,
    skip_initial_frames: int = 0,
) -> int:
    """
    Tail-cut offset for your trimming logic.
    Counters:
      - ch 37 (2B), period=1 (every sample)
      - ch 108 (3B), period=4 (subsampled)
      - ch 109..114 (2B), choose best, period=1
    Fast→fallback: quick coarse scan first; if confidence low, auto refine.
    """

    def score_for_base_off(base_off: int, buf: bytes, frames_cfg: Tuple[int,int,int]) -> float:
        max_frames, min_frames, skip = frames_cfg
        total_frames = (len(buf) - base_off) // FRAME_SIZE
        need = max(min_frames + skip, 2)
        if total_frames < need:
            return -1.0
        frames = min(total_frames, max_frames + skip)

        v37, w37 = _read_series(base_off, buf, 37, frames)
        v108, w108 = _read_series(base_off, buf, 108, frames)
        if skip:
            v37  = v37[skip:]
            v108 = v108[skip:]

        s37, _  = _score_periodic_counter(v37,  w37,  period=1)
        s108, _ = _score_periodic_counter(v108, w108, period=4)

        # Auto tail (period=1)
        tail_best = -1.0
        for ch in range(109, 115):
            v, w = _read_series(base_off, buf, ch, frames)
            if skip:
                v = v[skip:]
            st, _ = _score_periodic_counter(v, w, period=1)
            if st > tail_best:
                tail_best = st

        # Weighted mean: lean on the two every-sample counters
        w_emg, w_tail, w_eeg = 0.45, 0.45, 0.10
        # If EEG periodic is very weak, ignore it in the score
        if s108 < 0.80:
            w_emg, w_tail, w_eeg = 0.5, 0.5, 0.0

        return (w_emg*s37 + w_tail*tail_best + w_eeg*s108) / (w_emg + w_tail + w_eeg)

    def scan(buf: bytes,
             coarse_step: int,
             refine_radius: int,
             early_exit: float,
             frames_cfg: Tuple[int,int,int]) -> Tuple[int, float]:
        # 1) coarse
        best_off, best_score = None, -1.0
        for base_off in range(0, FRAME_SIZE, max(1, coarse_step)):
            s = score_for_base_off(base_off, buf, frames_cfg)
            if s > best_score:
                best_off, best_score = base_off, s
                if best_score >= early_exit:
                    return best_off, best_score
        if best_off is None:
            return -1, -1.0
        # 2) refine
        start = max(0, best_off - refine_radius)
        end   = min(FRAME_SIZE - 1, best_off + refine_radius)
        for base_off in range(start, end + 1):
            s = score_for_base_off(base_off, buf, frames_cfg)
            if s > best_score:
                best_off, best_score = base_off, s
                if best_score >= early_exit:
                    return best_off, best_score
        return best_off, best_score

    # ---- fast path ----
    buf_fast = data_buffer[:bytes_to_scan] if (bytes_to_scan is not None) else data_buffer
    best_off, best_score = scan(
        buf_fast,
        coarse_step=4,
        refine_radius=4,
        early_exit=0.995,
        frames_cfg=(max_frames_to_check, min_frames_required, skip_initial_frames),
    )

    # Good enough? return tail-cut
    if best_off >= 0 and best_score >= 0.990:
        return (len(data_buffer) - best_off) % FRAME_SIZE

    # ---- fallback (slightly wider but still quick) ----
    # widen bytes + frames; tighter step/radius; stricter early-exit
    buf_slow = data_buffer[:min(len(data_buffer), 32_768)]
    best_off2, best_score2 = scan(
        buf_slow,
        coarse_step=2,
        refine_radius=6,
        early_exit=0.997,
        frames_cfg=(min(240, max_frames_to_check*2), max(min_frames_required, 32), skip_initial_frames),
    )
    if best_off2 >= 0 and best_score2 > best_score:
        best_off, best_score = best_off2, best_score2

    if best_off < 0:
        raise RuntimeError("Could not determine stream offset — buffer too short or counters not detectable.")

    return (len(data_buffer) - best_off) % FRAME_SIZE
