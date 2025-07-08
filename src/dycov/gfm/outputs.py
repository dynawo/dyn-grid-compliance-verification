#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
) -> None:
    """
    Save the calculated results (PCC, down, up) to a CSV file.

    Parameters
    ----------
    path : Path
        The file path where the CSV file will be saved.
    magnitude : str
        Name of the mangnitude.
    time_array : np.ndarray
        The time array corresponding to the power signals.
    pcc : np.ndarray
        The calculated power at the point of common coupling.
    down : np.ndarray
        The lower power envelope.
    up : np.ndarray
        The upper power envelope.
    """
    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            f"{magnitude} PCC (pu)": pcc,
            f"{magnitude} down (pu)": down,
            f"{magnitude} up (pu)": up,
        }
    )
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def plot_results(
    path: Path,
    title: str,
    magnitude: str,
    time: np.ndarray,
    event_time: float,
    shift_time: float,
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
) -> None:
    """
    Plot the results of the GFM phase jump: theoretical response,
    upper envelope, and lower envelope.

    Parameters
    ----------
    path : Path
        The file path where the plot image will be saved.
    title : str
        The title of the plot, which will also be used as the filename.
    magnitude : str
        Name of the plotted mangnitude.
    time : np.ndarray
        The time array for the x-axis.
    event_time : float
        The time (in seconds) when the phase jump event occurred.
    shift_time : float
        A time shift (in milliseconds) to adjust the event time marker
        for plotting purposes.
    pcc : np.ndarray
        The calculated power at the point of common coupling.
    down : np.ndarray
        The lower power envelope.
    up : np.ndarray
        The upper power envelope.
    """
    plt.figure(figsize=(8, 5))

    plt.plot(
        time,
        pcc,
        label=f"{magnitude} at PCC",
        linewidth=3,
    )
    plt.plot(time, down, label=f"{magnitude} envelopes", linewidth=2, color="red")
    plt.plot(time, up, linewidth=2, color="red")
    plt.xlabel("sec")
    plt.ylabel(f"{magnitude} pu")
    plt.title(title)

    plt.axvline(
        x=event_time + shift_time / 1000,  # Convert ms to seconds
        color="black",
        linestyle="--",
        label="t at Event Time",
    )
    plt.legend(loc="lower right")
    plt.grid(True)
    plt.savefig(path, bbox_inches="tight", dpi=300)
    plt.close()
