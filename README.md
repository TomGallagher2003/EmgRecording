# Emg Recording
**Description**

A python project aiming to facilitate recording EMG (and eventually EEG) data for a collection of prompted hand movements.


**Configuration and Execution**

The program can be configured in the Config class within config.py, and can be executed by running the main.py. This program records EMG data for 10 cycles for each of the images in the configured movement library, and saves this data (currently as csv files)


**Data Visualisation**

Once collected, the contents of the csv files for each movement can be visualised by running csv_plotting.py. 
Live plotting of the collected data can be turned on by setting 'PLOT = True' in the Config class. 