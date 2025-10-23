# core/ui/image_loader.py
from functools import lru_cache
from PIL import Image, ImageTk

@lru_cache(maxsize=64)
def _load_raw(path: str) -> Image.Image:
    """Cache raw loads so repeated previews don't hit disk every time."""
    return Image.open(path)

def load_scaled_tk(path: str, max_w: int, max_h: int) -> ImageTk.PhotoImage:
    """Return a cached, scaled PhotoImage without mutating the cached original."""
    img = _load_raw(path).copy()  # copy so thumbnail doesn't mutate the cached Image
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return ImageTk.PhotoImage(img)
