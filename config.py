""" Defines the Configurations for data collection"""
class Config:

    READ_EMG = True
    READ_EEG = True

    # Set the Gain Mode here : 0 -> 8, 1 -> 4
    EMG_MODE = 0

    EEG_MODE = 3

    EMG_GAIN_RATIOS = {
    0: 286.1e-9,   # MODE=00 → 286.1 nV
    1: 572.2e-9,   # MODE=01 → 572.2 nV
}



    emg_on = 1 if READ_EMG else 0
    eeg_on = 1 if READ_EEG else 0
    DEVICE_EN = [emg_on, 0, 0, 0, eeg_on, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    EMG = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    MODE = [EMG_MODE, 0, 0, 0, EEG_MODE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


    # Configuration parameters
    TCP_PORT = 54320
    OFFSET_EMG = 1000
    PLOT_TIME = 1
    IP_ADDRESS = '192.168.76.1'



    NUM_CHAN = [38, 38, 38, 38, 70, 70, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]
    SAMPLE_FREQUENCY = 2000
    DATA_DESTINATION_PATH = "./emg_data"
    LABEL_DESTINATION_PATH = "./labels"
    IMAGE_SOURCE_PATH = "./movement_library/EA"


    # These channel lists are determined in configuration processing but are defined here to simplify plotting
    num_channels_used = 0
    MUOVI_EMG_CHANNELS = list(range(0, 32))
    MUOVI_AUX_CHANNELS = list(range(32, 38))
    if READ_EMG:
        num_channels_used += 38

    MUOVI_PLUS_EEG_CHANNELS = list(range(num_channels_used, num_channels_used + 64))
    MUOVI_PLUS_AUX_CHANNELS = list(range(num_channels_used + 64, num_channels_used + 70))
    if READ_EEG:
        num_channels_used += 70

    SYNCSTATION_CHANNELS = list(range(num_channels_used, num_channels_used + 6))

    PLOT = False