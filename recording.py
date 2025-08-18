import gc
import struct
from datetime import datetime
from pathlib import Path
import os

import numpy as np
import time
import h5py

from util.buffer_functions import save_buffer
from util.channel_alignment import simple_alignment
from util.OTB_refactored.configuration_processing import calculate_crc8, validate_config, process_config
from util.eeg_offset_util import offset_with_eeg
from util.processing import process
from util.socket_handling import SocketHandler
from config import Config

SAMPLE_TOLERANCE = 200

class EmgSession:
    def __init__(self, use_emg, use_eeg):
        self.USE_EMG = use_emg
        self.USE_EEG = use_eeg
        self.socket_handler = SocketHandler(Config.IP_ADDRESS, Config.TCP_PORT)
        self.socket_handler.connect()
        self.conf_string = None
        self.tot_num_byte = None
        self.tot_num_chan = None
        self.recording = False
        self.emg_channels = None
        self.start()
        self.id = 0
        self.dateString = datetime.today().strftime('%d-%m')
        self.make_directory()
        self.ind = 0

    def start(self):
        # Validate the contents of the configuration arrays
        validate_config(Config.DEVICE_EN, 1, "Error, set DeviceEN values equal to 0 or 1")
        validate_config(Config.EMG, 1, "Error, set EMG values equal to 0 or 1")
        validate_config(Config.MODE, 3, "Error, set Mode values between to 0 and 3")

        # Process the configuration to get the configuration string and other required fields
        self.conf_string, conf_str_len, self.emg_channels, self.tot_num_chan, self.tot_num_byte, plotting_info = (
            process_config(Config.DEVICE_EN, Config.EMG, Config.MODE, Config.NUM_CHAN))

        # Send the configuration to syncstation
        start_command = self.conf_string[0:conf_str_len]
        packed_data = struct.pack('B' * conf_str_len, *start_command)
        data_sent = self.socket_handler.send(packed_data)
        print(f"Start Command Sent: {start_command}")



    def finish(self):
        # Send the stop command to syncstation
        for i in range(18):
            self.conf_string[i] = 0
        self.conf_string[1] = calculate_crc8(self.conf_string, 1)
        stop_command = self.conf_string[0:1]
        packed_data = struct.pack('B' * len(stop_command), *stop_command)
        print("Stop Command Sent")
        data_sent = self.socket_handler.send(packed_data)
        self.socket_handler.close()

    def emg_recording(self, perform_time, rest_time, movement, rep):
        """ Make a single EMG recording for the movement and following rest"""
        print(f"Recording for movement {movement} rep {rep} ({perform_time + rest_time} seconds)")
        self.record(True, rest_time, movement, perform_time=perform_time, rep=rep)
    def record_initial_rest(self, rest_time, movement, perform_time):
        """ Make a single EMG recording for the rest period before a movement"""
        print(f"Recording initial rest for movement {movement} ({rest_time} seconds)")
        self.record(False, rest_time, movement, perform_time=perform_time)

    def record(self, is_movement, rest_time, movement, perform_time=0, rep=None):
        """ Make a single EMG recording"""
        if is_movement: rec_time = perform_time + rest_time
        else: rec_time = rest_time


        total_samples = int(Config.SAMPLE_FREQUENCY * rec_time)
        expected_bytes = self.tot_num_byte * total_samples
        data = np.zeros((self.tot_num_chan, int(Config.SAMPLE_FREQUENCY * rec_time)))

        chan_ready = 0
        data_buffer = b""  # Buffer to store the received data

        chunk_size = 512
        start_time = time.time()
        self.recording = True

        while time.time() - start_time < rec_time:
            data_temp = self.socket_handler.receive(chunk_size)
            if not data_temp:
                break
            data_buffer += data_temp
        save_buffer(data_buffer, f"test_buffer{self.ind}.bin")
        self.ind +=1
        self.recording = False
        print(f"Elapsed time for receiving data: {time.time() - start_time:.2f} seconds")
        print("Total bytes received:", len(data_buffer))
        if not self.USE_EEG:
            offset = simple_alignment(data_buffer)
        else:
            offset = offset_with_eeg(data_buffer)
        if offset != 0:
            data_buffer = data_buffer[:-offset]
        sample_size = self.tot_num_byte
        remainder = len(data_buffer) % sample_size
        if remainder != 0:
            data_buffer = data_buffer[remainder:]
        if len(data_buffer) >= expected_bytes:
            data_buffer = data_buffer[-expected_bytes:]
        else:
            print("Warning: received less data than expected")


        temp_array = np.frombuffer(data_buffer, dtype=np.uint8)
        temp = np.reshape(temp_array, (-1, self.tot_num_byte)).T  # dynamic reshape

        num_samples = temp.shape[1]
        expected_samples = Config.SAMPLE_FREQUENCY * rec_time

        if num_samples != expected_samples and expected_samples - num_samples < SAMPLE_TOLERANCE:
            data = np.zeros((self.tot_num_chan, num_samples))
            print(f"Allowed {num_samples} samples")

        data = process(temp, data, self.tot_num_byte, chan_ready)

        labels = np.array([movement] * int(perform_time * Config.SAMPLE_FREQUENCY) + [0] * int(rest_time * Config.SAMPLE_FREQUENCY))
        labels = labels if is_movement else np.array([0] * int(rest_time * Config.SAMPLE_FREQUENCY))


        suffix = f"M{movement}R{rep}" if is_movement else f"M{movement}rest"
        exercise_group = "EA" if movement < 13 else "EB"

        if self.USE_EMG:
            self.save_channels(data[Config.MUOVI_EMG_CHANNELS], labels, "emg", perform_time, exercise_group, suffix)

        if self.USE_EEG:
            self.save_channels(data[Config.MUOVI_PLUS_EEG_CHANNELS], labels, "eeg", perform_time, exercise_group, suffix)

        if Config.SAVE_COUNTERS and self.USE_EMG and self.USE_EEG:
            self.save_channels(np.array([data[Config.SYNCSTATION_COUNTER_CHANNEL], data[Config.MUOVI_COUNTER_CHANNEL],
                                         data[Config.MUOVI_PLUS_COUNTER_CHANNEL]]), labels, "counters", perform_time, exercise_group,
                               suffix)

        gc.collect()
    def receive_and_ignore(self, duration, no_print=False):
        if not no_print: print("Ignoring")
        end_time = time.time() + duration
        while self.recording:
            time.sleep(0.05)
        while time.time() < end_time:
            if not self.recording:
                data = self.socket_handler.receive(1024)
                if not data:
                    break

    def set_id(self, new_id):
        self.id = new_id

    def make_directory(self):

        dir_path = Config.DATA_DESTINATION_PATH

        # Check if it exists and is a directory
        if not os.path.isdir(dir_path):
            # Create the directory (and any missing parent directories)
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
        else:
            print(f"Directory already exists: {dir_path}")

    def make_subject_directory(self, subject_id, exercise_set):

        dir_path = Path(Config.DATA_DESTINATION_PATH) / f'{subject_id}'

        # Check if it exists and is a directory
        if not os.path.isdir(dir_path):
            # Create the directory (and any missing parent directories)
            os.makedirs(dir_path)
            if exercise_set == "A" or exercise_set == "AB":
                os.makedirs(dir_path / 'EA')
                os.makedirs(dir_path / 'EA' / 'csv')
                os.makedirs(dir_path / 'EA' / 'hdf5')
            if exercise_set == "B" or exercise_set == "AB":
                os.makedirs(dir_path / 'EB')
                os.makedirs(dir_path / 'EB' / 'csv')
                os.makedirs(dir_path / 'EB' / 'hdf5')
            print(f"Created directory: {dir_path}")


        else:
            print(f"Directory already exists: {dir_path}")


    def save_channels(self, data, labels, type_string, perform_time, exercise_group, suffix):

        destination_path = Path(Config.DATA_DESTINATION_PATH)

        np.savetxt(
            destination_path / f'{self.id}' / exercise_group / "csv" / f"{type_string}_data_{self.dateString}_{int(perform_time * 1000)}ms_{suffix}.csv",
            data.transpose(), delimiter=',')
        np.savetxt(
            destination_path / f'{self.id}' / exercise_group / "csv" / f"{type_string}_label_{self.dateString}_{int(perform_time * 1000)}ms_{suffix}.csv",
            labels.transpose(), delimiter=',')
        # np.savetxt(destination_path / "csv" / f"sample_counter_ID{self.id}_{self.dateString}_{suffix}.csv", syncstation_sample_counter, delimiter=',')

        if Config.SAVE_H5:
            with h5py.File(
                    destination_path / f'{self.id}' / exercise_group / "hdf5" / f"{type_string}_data_{self.dateString}_{int(perform_time * 1000)}ms_{suffix}.h5",
                    'w') as hf:
                hf.create_dataset('{type_string}_data', data=data.transpose())
                hf.create_dataset("{type_string}_label", data=labels)

    def get_record(self, rec_time):

        data_buffer = b""
        chunk_size = 512
        start_time = time.time()
        self.recording = True

        while time.time() - start_time < rec_time:
            data_temp = self.socket_handler.receive(chunk_size)
            if not data_temp:
                break
            data_buffer += data_temp

        total_samples = int(Config.SAMPLE_FREQUENCY * rec_time)
        expected_bytes = self.tot_num_byte * total_samples
        data = np.zeros((self.tot_num_chan, int(Config.SAMPLE_FREQUENCY * rec_time)))

        chan_ready = 0
        data_buffer = b""  # Buffer to store the received data

        chunk_size = 512
        start_time = time.time()
        self.recording = True

        while time.time() - start_time < rec_time:
            data_temp = self.socket_handler.receive(chunk_size)
            if not data_temp:
                break
            data_buffer += data_temp
        self.recording = False
        if not self.USE_EEG:
            offset = simple_alignment(data_buffer)
        else:
            offset = offset_with_eeg(data_buffer)
        if offset != 0:
            data_buffer = data_buffer[:-offset]
        sample_size = self.tot_num_byte
        remainder = len(data_buffer) % sample_size
        if remainder != 0:
            data_buffer = data_buffer[remainder:]
        if len(data_buffer) >= expected_bytes:
            data_buffer = data_buffer[-expected_bytes:]
        else:
            print("Warning: received less data than expected")

        temp_array = np.frombuffer(data_buffer, dtype=np.uint8)
        temp = np.reshape(temp_array, (-1, self.tot_num_byte)).T  # dynamic reshape
        data = process(temp, data, self.tot_num_byte, chan_ready)
        return data
