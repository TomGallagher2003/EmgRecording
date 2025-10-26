"""
No functionality version of the recorder for testing UI changes without the device
"""

import numpy as np

from util.file_pathing import save_channels
from util.socket_handling import SocketHandler
from config import Config

SAMPLE_TOLERANCE = 200

class Session:
    """ Has the same method signatures as main recording session class, replaced with passthrough
        """
    def __init__(self, use_emg, use_eeg, data_path):
        """Initialize a recording session
                """
        self.id = 0


    def start(self):
        """Passthrough
                """
        return



    def finish(self):
        """Passthrough
                """
        return


    def emg_recording(self, perform_time, rest_time, movement, rep):
        """Passthrough with log
        """
        print("RECORDING: ", rest_time, perform_time, movement, rep)
        return
    def record_initial_rest(self, rest_time, movement, perform_time):
        """Passthrough with log
                """
        print("RECORDING REST")

        return

    def record(self, is_movement, rest_time, movement, perform_time=0, rep=None):
        """Passthrough with log
        """
        print("RECORDING: ", rest_time, perform_time, movement, rep)
        return
    def receive_and_ignore(self, duration, no_print=False):
        """Passthrough
                """
        return

    def set_id(self, new_id):
        """Set the current subject/session identifier.

                Args:
                    new_id (int): Identifier to embed in output file paths.
                """
        self.id = new_id

    def make_directory(self):
        """Passthrough"""
        return

    def make_subject_directory(self, subject_id, exercise_set):
        """Passthrough
                """
        return


    def get_record(self, rec_time):
        """ Returns ['skip']
               """

        return np.array(['skip'])
