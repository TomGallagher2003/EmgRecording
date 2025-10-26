# Changing EMG/EEG Data Processing

To add any filters or other processes to the recording pipeline (they will occur before data saving), visit [util/processing.py](../api/util/processing.md). In this file, there are configuration points (currenlty doing nothing), where processes can be defined for each data type. Some basic filter types are available in [util/filters.py](../api/util/filters.md)