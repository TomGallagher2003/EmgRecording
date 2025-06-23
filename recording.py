import gc
import struct
from datetime import datetime
from pathlib import Path
import os

import numpy as np
import time
import h5py
from channel_alignment import simple_alignment
from configuration_processing import calculate_crc8, validate_config, process_config
from socket_handling import SocketHandler
from config import Config

SAMPLE_TOLERANCE = 200

class EmgSession:
    def __init__(self):
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
        self.record(True, rest_time, movement, perform_time=perform_time, rep=rep, save_h5=True)
    def record_initial_rest(self, rest_time, movement, perform_time):
        """ Make a single EMG recording for the rest period before a movement"""
        print(f"Recording initial rest for movement {movement} ({rest_time} seconds)")
        self.record(False, rest_time, movement, perform_time=perform_time, save_h5=True)

    def record(self, is_movement, rest_time, movement, perform_time=0, rep=None, save_h5=False):
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

        self.recording = False
        print(f"Elapsed time for receiving data: {time.time() - start_time:.2f} seconds")
        print("Total bytes received:", len(data_buffer))

        offset = simple_alignment(data_buffer)
        if offset != 0:
            data_buffer = data_buffer[:-offset]
        sample_size = 88
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



        # Processing data
        for DevId in range(16):
            if Config.DEVICE_EN[DevId] == 1:
                if Config.EMG[DevId] == 1:
                    ch_ind = np.arange(0, 33 * 2, 2)
                    ch_ind_aux = np.arange(33*2, 38 * 2, 2)
                    data_sub_matrix = temp[ch_ind].astype(np.int32) * 256 + temp[ch_ind + 1].astype(np.int32)
                    data_sub_matrix_aux = temp[ch_ind_aux].astype(np.int32) * 256 + temp[ch_ind_aux + 1].astype(np.int32)

                    # Search for the negative values and make the two's complement (not on aux)
                    ind = np.where(data_sub_matrix >= 32768)
                    data_sub_matrix[ind] = data_sub_matrix[ind] - 65536

                    # converting raw volts to mV using the ratios from the documentation
                    data_sub_matrix = data_sub_matrix * Config.EMG_GAIN_RATIOS[Config.EMG_GAIN_MODE] * 1e3

                    data[chan_ready:chan_ready + 33, :] = data_sub_matrix
                    data[chan_ready+33:chan_ready + 38, :] = data_sub_matrix_aux

                else:
                    ch_ind = np.arange(0, Config.NUM_CHAN[DevId] * 3, 3)
                    data_sub_matrix = temp[ch_ind] * 65536 + temp[ch_ind + 1] * 256 + temp[ch_ind + 2]

                    # Search for the negative values and make the two's complement
                    ind = np.where(data_sub_matrix >= 8388608)
                    data_sub_matrix[ind] = data_sub_matrix[ind] - 16777216

                    # will need to convert to correct unit here

                    data[chan_ready:chan_ready + Config.NUM_CHAN[DevId], :] = data_sub_matrix

                del ch_ind
                del ind
                del data_sub_matrix
                chan_ready += Config.NUM_CHAN[DevId]

        aux_starting_byte = self.tot_num_byte - (6 * 2)
        ch_ind = np.arange(aux_starting_byte, aux_starting_byte + 12, 2)
        data_sub_matrix = temp[ch_ind].astype(np.int32) * 256 + temp[ch_ind + 1].astype(np.int32)
        # Search for the negative values and make the two's complement
        # ind = np.where(data_sub_matrix >= 32768)
        # data_sub_matrix[ind] = data_sub_matrix[ind] - 65536

        data[chan_ready:chan_ready + 6, :] = data_sub_matrix
        emg_data = data[Config.MUOVI_EMG_CHANNELS]
        mouvi_sample_counter = data[Config.MUOVI_AUX_CHANNELS[1]]
        syncstation_sample_counter = data[Config.SYNCSTATION_CHANNELS[1]]
        labels = np.array([movement] * int(perform_time * Config.SAMPLE_FREQUENCY) + [0] * int(rest_time * Config.SAMPLE_FREQUENCY))
        destination_path = Path(Config.DATA_DESTINATION_PATH)

        suffix = f"M{movement}R{rep}" if is_movement else f"M{movement}rest"
        exercise_group = "EA" if movement < 13 else "EB"

        np.savetxt(destination_path / f'{self.id}'/ exercise_group / "csv" / f"emg_data_{self.dateString}_{int(perform_time*1000)}ms_{suffix}.csv", emg_data.transpose(), delimiter=',')
        np.savetxt(destination_path / f'{self.id}' / exercise_group / "csv" / f"label_{self.dateString}_{int(perform_time*1000)}ms_{suffix}.csv", labels.transpose(), delimiter=',')
        #np.savetxt(destination_path / "csv" / f"sample_counter_ID{self.id}_{self.dateString}_{suffix}.csv", syncstation_sample_counter, delimiter=',')


        if save_h5:
            with h5py.File(destination_path / f'{self.id}' / exercise_group / "hdf5" / f"emg_data_{self.dateString}_{int(perform_time*1000)}ms_{suffix}.h5", 'w') as hf:
                hf.create_dataset('emg_data', data=emg_data.transpose())
                hf.create_dataset("label", data=labels)

        del data_sub_matrix
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


