import gc
import struct
import numpy as np
import time

from configuration_processing import calculate_crc8, validate_config, process_config
from socket_handling import SocketHandler
from config import Config


class EmgSession:
    def __init__(self):
        self.socket_handler = SocketHandler(Config.IP_ADDRESS, Config.TCP_PORT)
        self.socket_handler.connect()
        self.conf_string = None
        self.tot_num_byte = None
        self.tot_num_chan = None
        self.recording = False
        self.start()

    def start(self):
        # Validate the contents of the configuration arrays
        validate_config(Config.DEVICE_EN, 1, "Error, set DeviceEN values equal to 0 or 1")
        validate_config(Config.EMG, 1, "Error, set EMG values equal to 0 or 1")
        validate_config(Config.MODE, 3, "Error, set Mode values between to 0 and 3")

        # Process the configuration to get the configuration string and other required fields
        self.conf_string, conf_str_len, sync_stat_chan, self.tot_num_chan, self.tot_num_byte, plotting_info = (
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

    def emg_recording(self, rec_time, movement, rep):
        """ Make a single EMG recording"""

        print(f"Recording for movement {movement} rep {rep}")
        data = np.zeros((self.tot_num_chan + 1, Config.SAMPLE_FREQUENCY * rec_time))
        block_data = self.tot_num_byte * Config.SAMPLE_FREQUENCY * rec_time

        chan_ready = 1
        data_buffer = b""  # Buffer to store the received data

        chunk_size = 512
        loop_start_time = time.time()
        self.recording = True
        while len(data_buffer) < block_data:
            remaining_data = block_data - len(data_buffer)
            buffer_size = min(chunk_size, remaining_data)
            data_temp = self.socket_handler.receive(buffer_size)

            if not data_temp:
                break
            data_buffer += data_temp
        print(f"Elapsed time for receiving data: {time.time() - loop_start_time:.2f} seconds")
        self.recording = False

        print("Successful recording: " + str(len(data_buffer)))

        temp_array = np.frombuffer(data_buffer, dtype=np.uint8)
        temp = np.reshape(temp_array, (Config.SAMPLE_FREQUENCY * rec_time, self.tot_num_byte)).T

        # Processing data
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

        aux_starting_byte = self.tot_num_byte - (6 * 2)
        ch_ind = np.arange(aux_starting_byte, aux_starting_byte + 12, 2)
        data_sub_matrix = temp[ch_ind].astype(np.uint32) * 256 + temp[ch_ind + 1].astype(np.uint32)

        # Search for the negative values and make the two's complement
        ind = np.where(data_sub_matrix >= 32768)
        data_sub_matrix[ind] = data_sub_matrix[ind] - 65536

        data[chan_ready:chan_ready + 6, :] = data_sub_matrix
        np.savetxt(Config.DATA_DESTINATION_PATH + rf"\emg_data_M{movement}R{rep}.csv", data, delimiter=',')
        del ind
        del data_sub_matrix
        gc.collect()


    def receive_and_ignore(self, duration):
        print("Ignoring")
        end_time = time.time() + duration
        while self.recording:
            time.sleep(0.05)
        while time.time() < end_time:
            if not self.recording:
                data = self.socket_handler.receive(1024)
                if not data:
                    break

