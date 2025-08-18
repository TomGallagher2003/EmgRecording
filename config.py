""" Defines the Configurations for data collection"""
class Config:

    READ_EMG = True
    READ_EEG = True

    SAVE_COUNTERS = True
    SAVE_H5 = True

    # Set the Gain Mode here : 0 -> 8, 1 -> 4
    EMG_MODE = 0

    EEG_MODE = 0

    GAIN_RATIOS = {
    0: 286.1e-9,   # MODE=00 → 286.1 nV
    1: 572.2e-9,   # MODE=01 → 572.2 nV
    2: 1.0e-3,     # TEST MODE
    3: 1.0e-3      # TEST MODE
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
    DATA_DESTINATION_PATH = "./data"
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

    SYNCSTATION_COUNTER_CHANNEL = SYNCSTATION_CHANNELS[4]
    MUOVI_COUNTER_CHANNEL = MUOVI_AUX_CHANNELS[4]
    MUOVI_PLUS_COUNTER_CHANNEL = MUOVI_PLUS_AUX_CHANNELS[5]

    MOVEMENT_IMAGES_A = [
        "movement_library/EA/Index_flexion_M1.png",
        "movement_library/EA/Index_Extension_M2.png",
        "movement_library/EA/Middle_Flexion_M3.png",
        "movement_library/EA/Middle_Extension_M4.png",
        "movement_library/EA/Ring_Flexion_M5.png",
        "movement_library/EA/Ring_Extension_M6.png",
        "movement_library/EA/Little_Flexion_M7.png",
        "movement_library/EA/Little_Extension_M8.png",
        "movement_library/EA/Thurmb_Adduction_M9.png",
        "movement_library/EA/Thurmb_Abduction_M10.png",
        "movement_library/EA/Thurmb_Flexion_M11.png",
        "movement_library/EA/Thurmb_Extension_M12.png"
    ]
    MOVEMENT_IMAGES_B = [
        "movement_library/EB/Thrumb_up_M13.png",
        "movement_library/EB/Extension_of_index_and_middle_M14.PNG.png",
        "movement_library/EB/Flexion_of_little_and_ring_M15.PNG.png",
        "movement_library/EB/Thumb_opposing_of base_of_little_finger_M16.PNG.png",
        "movement_library/EB/hands_open_M17.PNG.png",
        "movement_library/EB/Fingures_fixed_together_in_fist_M18.PNG.png",
        "movement_library/EB/pointing_index_M19.PNG.png",
        "movement_library/EB/adduction_of_extended_fingers_M20.PNG.png",
        "movement_library/EB/wrist_supination_middile_finger_M21.PNG.png",
        "movement_library/EB/wrist_pronation_M22.PNG.png",
        "movement_library/EB/wrist_supination_little_finger_M23.PNG.png",
        "movement_library/EB/wrist_pronation_little_finger_M24.PNG.png",
        "movement_library/EB/wrist_flexion_M25.PNG.png",
        "movement_library/EB/wrist_extension_M26.PNG.png",
        "movement_library/EB/wrist_radial_deviation_M27.PNG.png",
        "movement_library/EB/wrist_ular_deviation_M28.PNG.png",
        "movement_library/EB/wrist_extension_with_closed_hand_M29.PNG.png"
    ]