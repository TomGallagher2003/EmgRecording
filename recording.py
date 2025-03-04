import datetime
import struct
import time
import gc

import numpy as np

from configuration_processing import calculate_crc8, validate_config, process_config, get_sorted_file_paths
from plotting import Plotter
from socket_handling import SocketHandler
from config import Config
class EmgSession:
    def __init__(self):
        self.socket_handler = SocketHandler(Config.IP_ADDRESS, Config.TCP_PORT)
        self.socket_handler.connect()

    def finish(self):
        self.socket_handler.close()

    def emg_recording(self, total_time, movement_number):
        """ Make a single EMG recording"""

        # Validate the contents of the configuration arrays
        validate_config(Config.DEVICE_EN, 1, "Error, set DeviceEN values equal to 0 or 1")
        validate_config(Config.EMG, 1, "Error, set EMG values equal to 0 or 1")
        validate_config(Config.MODE, 3, "Error, set Mode values between to 0 and 3")

        # Process the configuration to get the configuration string and other required fields
        conf_string, conf_str_len, sync_stat_chan, tot_num_chan, tot_num_byte, plotting_info = (
            process_config(Config.DEVICE_EN, Config.EMG, Config.MODE, Config.NUM_CHAN))

        if Config.PLOT:
            plotter = Plotter(plotting_info, Config.OFFSET_EMG, sync_stat_chan, Config.SAMPLE_FREQUENCY * Config.PLOT_TIME)

        num_cycles = total_time

        # Send the configuration to syncstation
        start_command = conf_string[0:conf_str_len]
        packed_data = struct.pack('B' * conf_str_len, *start_command)
        data_sent = self.socket_handler.send(packed_data)

        print(f"Start Command Sent: {start_command}")

        data = np.zeros((tot_num_chan + 1, Config.SAMPLE_FREQUENCY * Config.PLOT_TIME))
        block_data = tot_num_byte * Config.SAMPLE_FREQUENCY * Config.PLOT_TIME

        for i in range(num_cycles):
            print(f"Cycle {i + 1}")

            chan_ready = 1
            data_buffer = b""  # Buffer to store the received data

            while len(data_buffer) < block_data:
                buffer_size = block_data - len(data_buffer)
                data_temp = self.socket_handler.receive(buffer_size)
                if not data_temp:
                    # The socket was closed by the remote side
                    break
                data_buffer += data_temp

            print("Data packet ready: " + str(len(data_buffer)))
            temp_array = np.frombuffer(data_buffer, dtype=np.uint8)
            temp = np.reshape(temp_array, (Config.SAMPLE_FREQUENCY * Config.PLOT_TIME, tot_num_byte)).T

            for DevId in range(16):
                if Config.DEVICE_EN[DevId] == 1:
                    if Config.EMG[DevId] == 1:
                        ch_ind = np.arange(0, Config.NUM_CHAN[DevId] * 2, 2)
                        data_sub_matrix = temp[ch_ind].astype(np.uint32) * 256 + temp[ch_ind + 1].astype(np.uint32)

                        # Search for the negative values and make the two's complement
                        ind = np.where(data_sub_matrix >= 32768)
                        data_sub_matrix[ind] = data_sub_matrix[ind] - 65536

                        data[chan_ready:chan_ready + Config.NUM_CHAN[DevId], :] = data_sub_matrix
                    else:
                        ch_ind = np.arange(0, Config.NUM_CHAN[DevId] * 3, 3)
                        data_sub_matrix = temp[ch_ind] * 65536 + temp[ch_ind + 1] * 256 + temp[ch_ind + 2]

                        # Search for the negative values and make the two's complement
                        ind = np.where(data_sub_matrix >= 8388608)
                        data_sub_matrix[ind] = data_sub_matrix[ind] - 16777216

                        data[chan_ready:chan_ready + Config.NUM_CHAN[DevId], :] = data_sub_matrix

                    del ch_ind
                    del ind
                    del data_sub_matrix
                    chan_ready += Config.NUM_CHAN[DevId]

            aux_starting_byte = tot_num_byte - (6 * 2)
            ch_ind = np.arange(aux_starting_byte, aux_starting_byte + 12, 2)
            data_sub_matrix = temp[ch_ind].astype(np.uint32) * 256 + temp[ch_ind + 1].astype(np.uint32)

            # Search for the negative values and make the two's complement
            ind = np.where(data_sub_matrix >= 32768)
            data_sub_matrix[ind] = data_sub_matrix[ind] - 65536

            data[chan_ready:chan_ready + 6, :] = data_sub_matrix
            del ind
            del data_sub_matrix

            # Add the data for this cycle to the plot
            if Config.PLOT:
                plotter.plot_cycle(data, i, movement_number)

        print("Cycles finished")

        # Send the stop command to syncstation
        for i in range(18):
            conf_string[i] = 0
        conf_string[1] = calculate_crc8(conf_string, 1)
        stop_command = conf_string[0:1]
        packed_data = struct.pack('B' * len(stop_command), *stop_command)
        print("Stop Command Sent")
        data_sent = self.socket_handler.send(packed_data)
        if Config.PLOT:
            plotter.close()
        return data

    def iterate_recordings(self, image_file_path, data_destination_path):
        """ Get Multiple recordings for the images in the given file"""
        image_list = get_sorted_file_paths(image_file_path)
        sampling_rate = 2000  # Sampling rate in Hz
        exercise_set = 'A'  # Exercise set label
        recording_date = datetime.datetime.now().strftime("%Y-%m-%d")

        try:
            for i, value in enumerate(image_list):
                if i != 0:
                    time.sleep(2)
                print(f"recording for movement {i + 1}")
                starttime = time.time()
                emg_data = self.emg_recording(10, i +1)
                endtime = time.time()
                movement = f'M{i + 1}'
                starttime_str = datetime.datetime.fromtimestamp(starttime).strftime('%H:%M:%S.%f')[:-3]
                endtime_str = datetime.datetime.fromtimestamp(endtime).strftime('%H:%M:%S.%f')[:-3]

                import numpy as np

                # Save the data
                np.savetxt(Config.DATA_DESTINATION_PATH + rf"\emg_data_M{i + 1}.csv", emg_data, delimiter=',')

                # free up memory when no longer needed
                del emg_data
                gc.collect()


        except Exception as e:
            print(e)