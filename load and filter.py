import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
import util.filters as filters
from view_csv import plot_file, plot_channel

matplotlib.use('TkAgg')


FILENAME = "data/6/eeg/EA/csv/eeg_data_09-09_2000ms_M2R1.csv"

def filter_file(file_path):
    """
    Filter the given raw eeg data file
    """


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    print(data.shape)

    data = filter_pipeline(data)

    outfile = file_path.split('.cs')[0] + "_filtered.csv"
    np.savetxt(outfile, data.transpose(), delimiter=',')
    print("Filtering Complete for", file_path.split("/")[-1])
    print("Saved to", outfile)
    return outfile
def filter_pipeline(data):

    data = filters.preprocess_eeg(data)
    return data



if __name__ == '__main__':

    outfile = filter_file("../" + FILENAME)
    #plot_file(outfile)
    plot_channel(outfile, 61)

