import typing as t

import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

channel_colors = {"green": "green", "iso": "purple", "red": "red"}


def plot_sensor_floor(
    background_ch: t.Union[pd.Series, np.ndarray], channel: str
) -> t.Tuple[matplotlib.figure.Figure, float]:
    """
    Plot histograms for sensor floor values of three channels.
    """

    fig, ax = plt.subplots(2, 1, figsize=(10, 8))

    floor_mean = np.mean(background_ch).astype(float)

    def _make_hist(data, ax1, ax2, color, ch_name):
        ax1.hist(data, bins=100, range=(255, 270), color=color, alpha=0.7)
        ax1.set_xlim(255, 270)
        ax1.set_title(f"{ch_name} floor average: {floor_mean:.2f}")
        ax1.set_xlabel("CMOS pixel value")
        ax1.set_ylabel("Counts")

        ax2.hist(data, bins=100, color=color, alpha=0.7)
        ax2.set_title(f"{ch_name} - All data")
        ax2.set_xlabel("CMOS pixel value")
        ax2.set_ylabel("Counts")

    _make_hist(background_ch, ax[0], ax[1], channel_colors.get(channel, "black"), f"{channel.capitalize()} Channel")

    return (fig, floor_mean)
