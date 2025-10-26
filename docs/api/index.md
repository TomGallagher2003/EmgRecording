# API

Browse the modules by category. 

---

## Top-level modules

- [**timer**](timer.md) — Main file - Tkinter experiment timer / runner UI.
- [**practice_timer**](practice_timer.md) — PyQt practice viewer with GIF prompts and radial countdown.
- [**view_csv**](view_csv.md) — quick plotting utilities for EMG/EEG CSVs.
- [**experiment_settings**](experiment_settings.md) — constants for window size, baseline, tick rate, and paths.
- [**recording**](recording.md) — `Session` controller: start/stop device, stream/parse frames, label & save segments.

---

## Core

- [**core.phase_manager**](core/phase_manager.md) — fixed-duration phase logic (animate arc, labels, pause/resume, callback).
- [**core.recording_helpers**](core/recording_helpers.md) — `RecordingController` façade for the recorder (logging/retries hooks).

### UI

- [**core.ui.device_screen**](core/ui/device_screen.md) — device selection screen (EMG/EEG) with validation.
- [**core.ui.image_loader**](core/ui/image_loader.md) — image/GIF loading utilities for prompts.
- [**core.ui.main_screen**](core/ui/main_screen.md) — main run screen (current/next image, countdown, controls).
- [**core.ui.parameter_screen**](core/ui/parameter_screen.md) — parameter entry / configuration screen.

---

## Utilities

- [**util.buffer_functions**](util/buffer_functions.md) — byte/packet helpers.
- [**util.channel_alignment**](util/channel_alignment.md) — frame/header alignment and offsets.
- [**util.data_validation**](util/data_validation.md) — sanity checks on arrays and shapes.
- [**util.file_pathing**](util/file_pathing.md) — directory creation and file naming/saving.
- [**util.filters**](util/filters.md) — signal filtering helpers.
- [**util.images**](util/images.md) — image utilities for the UI.
- [**util.processing**](util/processing.md) — decode/interleave to channel-major arrays.
- [**util.socket_handling**](util/socket_handling.md) — TCP receive/send wrappers.

### OT Bio (refactored)

- [**util.OTB_refactored.configuration_processing**](util/OTB_refactored/configuration_processing.md) — CRC, config validation, and `process_config`.
