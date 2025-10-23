# Images & Assets

- Paths are defined in `util/images.py` (e.g., `Images.REST`, `Images.MOVEMENT_IMAGES_A`, `Images.MOVEMENT_IMAGES_B`).
- UI loads images via `core/ui/image_loader.py`:
  - `load_scaled_tk(path, max_w, max_h)` caches raw loads and returns a scaled `PhotoImage`.
- The main screen shows:
  - **Current image** (right panel)
  - **Next image preview** (left panel; red border during pre-rest)

To add or swap assets, update `util/images.py`. The UI will pick them up without code changes.
