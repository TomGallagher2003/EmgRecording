# Prompted Biometric Data Collection

Real-time **EMG (+ EEG soon)** capture and labelled data saving and plotting to aid prosthetic-hand control research.

---

## 1 . Quick Start (desktop demo)

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