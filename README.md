# Prompted Biometric Data Collection

Real-time **EMG (+ EEG soon)** capture and labelled data saving and plotting to aid prosthetic-hand control research.

---

## 1 . Quick Start (view example emg data)

```bash
# Clone the repo
git clone https://github.com/TomGallagher2003/EmgRecording.git
cd EmgRecording

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install core dependencies
pip install -r requirements.txt   # numpy, matplotlib, tk ...

# Plot the supplied demo recording
python view_csv.py
```

## 2 . EMG Recording

To record new emg data, connect the syncstation to the computer using a LAN connection,
and connect the MUOVI device to the syncstation wirelessly. 
With the hardware connected, run the file: timer.py
```bash
python timer.py
```
You will be prompted for the experiment parameters, then the recording experiment will run, saving the data based 
on the provided subject ID and date. This data will be saved in both csv and hdf5 format, in the /emg_data folder.

## 3 . Viewing Your Data
To view your data, run view_csv with the filename you would like to view. This can be configured at the top of the view.csv file to plot a single channel but plots all 32 EMG channels by default.
```bash
python view_csv filename.csv
```
Filenames are of the form emg_data_ID{id}_{date}_M{movement}R{rep}.csv, where the date is in dd-mm format.