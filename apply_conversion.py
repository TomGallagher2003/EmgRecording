import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
import util.filters as filters
from view_csv import plot_file, plot_channel

matplotlib.use('TkAgg')


FILENAME = "eeg_debug.csv"

def convert_file(file_path):
    """
    Filter the given raw eeg data file
    """
    config = Config(False, True)


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    print(data.shape)

    data = data * config.GAIN_RATIOS[config.EEG_MODE] * 1e3

    outfile = file_path.split('.cs')[0] + "_converted.csv"
    np.savetxt(outfile, data.transpose(), delimiter=',')
    print("Conversion Complete for", file_path.split("/")[-1])
    print("Saved to", outfile)
    return outfile



if __name__ == '__main__':

    outfile = convert_file(FILENAME)
    #plot_file(outfile)
    plot_channel(outfile, 61)

