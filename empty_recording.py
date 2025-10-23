"""EMG/EEG recording session controller.

This module provides the `Session` class to configure a SyncStation/EMG device,
send start/stop commands, stream raw frames over TCP, align/parse frames into
per-channel samples, and save EMG/EEG/counter channels with labels for
movement/rest segments. Designed for synchronous EMG/EEG experiments with
optional counter channels and HDF5/CSV persistence.
"""

import gc
import struct
from datetime import datetime
import os

import numpy as np
import time
from util.channel_alignment import simple_alignment
from util.OTB_refactored.configuration_processing import calculate_crc8, validate_config, process_config
from util.file_pathing import save_channels, make_subject_directory
from util.processing import process
from util.socket_handling import SocketHandler
from config import Config

SAMPLE_TOLERANCE = 200

class Session:
    """Manage a recording session for EMG/EEG data acquisition.

        This class encapsulates configuration validation, SyncStation communication,
        streaming/collection of raw bytes, alignment (with or without EEG counters),
        decoding into channel-wise arrays, and saving labeled segments.

        Attributes:
            config (Config): Runtime configuration (devices, channels, sample rate, paths).
            socket_handler (SocketHandler): TCP socket wrapper for the SyncStation/device.
            conf_string (list[int] | None): Mutable configuration command buffer (bytes-as-ints).
            tot_num_byte (int | None): Bytes per frame (all enabled channels in one frame).
            tot_num_chan (int | None): Number of enabled channels in the stream.
            recording (bool): True while actively receiving bytes for a segment.
            emg_channels (list[int] | None): Indices of EMG channels within the frame.
            id (int): Subject/session identifier used in file names.
            dateString (str): Short date string (dd-mm) used in file naming.
            ind (int): Internal counter for segments recorded in this process.
        """
    def __init__(self, use_emg, use_eeg):
        """Initialize a recording session and connect to the device.

                Args:
                    use_emg (bool): Whether EMG channels are enabled.
                    use_eeg (bool): Whether EEG channels are enabled.
                """
        self.id = 0


    def start(self):
        """Validate and send the start/configuration command to the device.

                Validates `DEVICE_EN`, `EMG`, and `MODE`, computes the packed
                configuration with `process_config`, and sends it over the socket.
                Populates: `conf_string`, `emg_channels`, `tot_num_chan`, `tot_num_byte`.
                """





    def finish(self):
        """Send a stop command and close the socket.

                Mutates the configuration header to craft a stop command, sends it,
                and closes the TCP connection.
                """



    def emg_recording(self, perform_time, rest_time, movement, rep):
        """Record one movement + following rest segment for EMG.

        Args:
            perform_time (float): Duration of the movement in seconds.
            rest_time (float): Rest duration immediately after the movement in seconds.
            movement (int): Movement label/index (used for file naming and labels).
            rep (int): Repetition number (used for file naming).
        """
        return
    def record_initial_rest(self, rest_time, movement, perform_time):
        """Record the initial rest period before a movement.

        Args:
            rest_time (float): Rest duration in seconds.
            movement (int): Movement label/index (used in labels and naming).
            perform_time (float): Planned movement duration (for label sizing).
        """
        return

    def record(self, is_movement, rest_time, movement, perform_time=0, rep=None):
        """Record a single segment (movement or rest), align, decode, and save.

        Streams raw bytes for `rec_time`, aligns frames (EEG-aware if enabled),
        reshapes to frames, decodes to channel arrays, builds movement/rest labels,
        and saves EMG/EEG/counter channels according to config.

        Args:
            is_movement (bool): If True, records `perform_time + rest_time`; else only rest.
            rest_time (float): Rest duration in seconds.
            movement (int): Movement label/index.
            perform_time (float, optional): Movement duration in seconds. Defaults to 0.
            rep (int | None): Repetition index for naming when `is_movement=True`.

        Notes:
            - Uses `SAMPLE_TOLERANCE` to accept minor sample count drift.
            - Uses `simple_alignment` when EEG is not enabled; otherwise no offset trim here.
        """
        return
    def receive_and_ignore(self, duration, no_print=False):
        """Passively read and discard incoming bytes for a duration.

                Useful for flushing the socket or letting the device stream while
                the UI prepares, without recording.

                Args:
                    duration (float): Seconds to continue ignoring data.
                    no_print (bool): Suppress the default 'Ignoring' print if True.
                """
        return

    def set_id(self, new_id):
        """Set the current subject/session identifier.

                Args:
                    new_id (int): Identifier to embed in output file paths.
                """
        self.id = new_id

    def make_directory(self):
        """Ensure the base data destination directory exists."""
        return

    def make_subject_directory(self, subject_id, exercise_set):
        """Create (if needed) the subject directory tree for an exercise set.

                Args:
                    subject_id (int | str): Subject identifier used in the folder structure.
                    exercise_set (str): Exercise set label (e.g., 'EA' or 'EB').
                """
        return

    def save_channels(self, data, labels, type_string, perform_time, exercise_group, suffix):
        """Persist a set of channels plus labels to disk.

                Args:
                    data (np.ndarray): Channel-major array to save (shape: [n_channels, n_samples]).
                    labels (np.ndarray): 1D label array per-sample for movement/rest.
                    type_string (str): Type key ('emg', 'eeg', or 'counters').
                    perform_time (float): Movement duration used in naming/metadata.
                    exercise_group (str): Exercise set/group label, e.g., 'EA'/'EB'.
                    suffix (str): File suffix encoding movement/rep or rest segment.
                """
        save_channels(
            self.config.DATA_DESTINATION_PATH,
            self.id,
            type_string,
            exercise_group,
            perform_time,
            suffix,
            data,
            labels,
            save_h5=self.config.SAVE_H5,
            date_str=self.dateString
        )

    def get_record(self, rec_time):
        """Capture a raw segment for `rec_time` seconds and return decoded channels. Used to make sure there is nonzero data for each device.

               Streams bytes for the specified duration, aligns frames (EEG-aware if
               enabled), decodes into channel arrays, and returns the numeric data.

               Args:
                   rec_time (float): Segment duration in seconds.

               Returns:
                   np.ndarray: Array of shape [n_channels, n_samples] for the captured segment.
               """
        return np.array([])
