""" Defines the Configurations for data collection"""
class Config:

    # Configuration parameters
    TCP_PORT = 54320
    OFFSET_EMG = 1000
    PLOT_TIME = 1
    IP_ADDRESS = '192.168.76.1'

    # Configuration for muovi 1
    DEVICE_EN = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    EMG = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    MODE = [3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    NUM_CHAN = [38, 38, 38, 38, 70, 70, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]
    SAMPLE_FREQUENCY = 2000
    DATA_DESTINATION_PATH = "./emg_data"
    IMAGE_SOURCE_PATH = "./movement_library/EA"

    PLOT = False
