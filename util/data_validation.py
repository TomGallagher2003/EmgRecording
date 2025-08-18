from config import Config

def validate_data(data, use_emg, use_eeg):
    print("forntite ", data[Config.MUOVI_AUX_CHANNELS[5]][0:10])
    print(data[Config.MUOVI_EMG_CHANNELS[1]][0:10])
    print(data[Config.MUOVI_EMG_CHANNELS[2]][0:10])
    print(data[Config.MUOVI_EMG_CHANNELS[3]][0:10])

    if use_emg and not zero_check(data[Config.MUOVI_EMG_CHANNELS[0]]):
        return False
    if use_eeg and not zero_check(data[Config.MUOVI_PLUS_EEG_CHANNELS[0]]):
        return False
    return True

def zero_check(channel):
    print(f"Checked for data in {len(channel)} samples")
    print(channel[0:30])
    return not all(sample == 0 for sample in channel)