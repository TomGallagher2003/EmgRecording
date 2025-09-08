""" Defines the Configurations for data collection"""
class Config:

    def __init__(self, use_emg, use_eeg):
        self.USE_EMG = use_emg
        self.USE_EEG = use_eeg
        self.SAVE_COUNTERS = True
        self.SAVE_H5 = True

        # Set the Gain Mode here : 0 -> 8, 1 -> 4
        self.EMG_MODE = 0
        self.EEG_MODE = 0
        self.GAIN_RATIOS = {
            0: 286.1e-9,   # MODE=00 → 286.1 nV
            1: 572.2e-9,   # MODE=01 → 572.2 nV
            2: 1.0e-3,     # TEST MODE
            3: 1.0e-3      # TEST MODE
            }




        eeg_on = 1 if self.USE_EEG else 0
        emg_on = 1 if self.USE_EMG else 0
        self.DEVICE_EN = [emg_on, 0, 0, 0, eeg_on, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.EMG = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.MODE = [self.EMG_MODE, 0, 0, 0, self.EEG_MODE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


        # Configuration parameters
        self.TCP_PORT = 54320
        self.OFFSET_EMG = 1000
        self.PLOT_TIME = 1
        self.IP_ADDRESS = '192.168.76.1'



        self.NUM_CHAN = [38, 38, 38, 38, 70, 70, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]
        self.SAMPLE_FREQUENCY = 2000
        self.DATA_DESTINATION_PATH = "./data"
        self.LABEL_DESTINATION_PATH = "./labels"
        self.IMAGE_SOURCE_PATH = "./movement_library/EA"


        num_channels_used = 0
        self.MUOVI_EMG_CHANNELS = list(range(0, 32))
        self.MUOVI_AUX_CHANNELS = list(range(32, 38))
        if self.USE_EMG:
            num_channels_used += 38

        self.MUOVI_PLUS_EEG_CHANNELS = list(range(num_channels_used, num_channels_used + 64))
        self.MUOVI_PLUS_AUX_CHANNELS = list(range(num_channels_used + 64, num_channels_used + 70))
        if self.USE_EEG:
            num_channels_used += 70

        self.SYNCSTATION_CHANNELS = list(range(num_channels_used, num_channels_used + 6))

        self.SYNCSTATION_COUNTER_CHANNEL = self.SYNCSTATION_CHANNELS[4]
        self.MUOVI_COUNTER_CHANNEL = self.MUOVI_AUX_CHANNELS[4]
        self.MUOVI_PLUS_COUNTER_CHANNEL = self.MUOVI_PLUS_AUX_CHANNELS[5]

