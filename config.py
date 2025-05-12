""" Defines the Configurations for data collection"""
class Config:

    READ_EMG = True
    READ_EEG = False


    DEVICE_EN = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    EMG = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    MODE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

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


    # These channle lists are determined in configuration processing but are defined here to simplify plotting
    MUOVI_EMG_CHANNELS = list(range(1, 33))
    MUOVI_AUX_CHANNELS = list(range(33,39))
    SYNCSTATION_CHANNELS = list(range(39, 45))

    PLOT = False