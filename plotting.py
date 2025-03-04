import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')
class Plotter:
    def __init__(self, plotting_info, offset_emg, sync_stat_chan, upper_limit ):
        """ Initialize the Plotter object with the necessary information."""
        self.plotting_info = plotting_info
        self.offset_emg = offset_emg
        self.sync_stat_chan = sync_stat_chan
        
        # Initialize the plot figure
        self.fig = plt.figure()
        plt.xlim([0, upper_limit])  # You can adjust the x-axis range based on your data

    def plot_cycle(self, data, cycle_number, movement_number):
        """ Adds the data from a single cycle to the plot."""
        plt.cla()
        k = 0
        
        if self.plotting_info.mouvi_connected:
            for j in self.plotting_info.mouvi_emg_chan:
                plt.plot(data[j, :] + self.offset_emg * k)
                k += 1
            for j in self.plotting_info.muovi_aux_chan:
                plt.plot(data[j, :])

        if self.plotting_info.sessan_connected:
            k = 0
            for j in self.plotting_info.sessn_emg_chan:
                plt.plot(data[j, :] + self.offset_emg * k)
                k += 1
            for j in self.plotting_info.sessn_aux_chan:
                plt.plot(data[j, :])

        if self.plotting_info.due_pl_connected:
            k = 0
            for j in self.plotting_info.due_pl_emg_chan:
                plt.plot(data[j, :] + self.offset_emg * k)
                k += 1
            for j in self.plotting_info.due_pl_aux_chan:
                plt.plot(data[j, :])

        for j in self.sync_stat_chan:
            plt.plot(data[j, :])

        plt.title(f"Movement {movement_number}, Cycle {cycle_number}")

        plt.pause(0.02)  # Pause to allow rendering and updating of the plots
        plt.draw()

    def show(self):
        """ Shows the plot after all cycles are finished."""
        plt.show()

    def close(self):
        """closes the plot for this iteration"""
        plt.close()


