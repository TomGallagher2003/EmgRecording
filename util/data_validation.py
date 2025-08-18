from config import Config

def validate_data(data, use_emg, use_eeg):
    if use_emg and not zero_check(data[Config.MUOVI_EMG_CHANNELS[0]]):
        return False
    if use_eeg and not zero_check(data[Config.MUOVI_PLUS_EEG_CHANNELS[0]]):
        return False
    print("Data found for all selected devices")
    return True

def zero_check(channel):
    return not all(sample == 0 for sample in channel)