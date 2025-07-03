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
    time_array: np.ndarray,
    p_pcc: np.ndarray,
    p_down: np.ndarray,
    p_up: np.ndarray,
) -> None:
    """
    Save the calculated results (P_PCC, P_down, P_up) to a CSV file.

    Parameters
    ----------
    path : Path
        The file path where the CSV file will be saved.
    time_array : np.ndarray
        The time array corresponding to the power signals.
    p_pcc : np.ndarray
        The calculated power at the point of common coupling.
    p_down : np.ndarray
        The lower power envelope.
    p_up : np.ndarray
        The upper power envelope.
    """
    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            "P_PCC (pu)": p_pcc,
            "P_down (pu)": p_down,
            "P_up (pu)": p_up,
        }
    )
    # Save the DataFrame to a CSV file without including the index.
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def plot_results(
    path: Path,
    title: str,
    time: np.ndarray,
    event_time: float,
    shift_time: float,
    p_pcc: np.ndarray,
    p_down: np.ndarray,
    p_up: np.ndarray,
) -> None:
    """
    Plot the results of the GFM phase jump: theoretical response,
    upper envelope, and lower envelope.

    Parameters
    ----------
    path : Path
        The file path where the plot image will be saved.
    time : np.ndarray
        The time array for the x-axis.
    event_time : float
        The time (in seconds) when the phase jump event occurred.
    shift_time : float
        A time shift (in milliseconds) to adjust the event time marker
        for plotting purposes.
    title : str
        The title of the plot, which will also be used as the filename.
    p_pcc : np.ndarray
        The calculated power at the point of common coupling.
    p_down : np.ndarray
        The lower power envelope.
    p_up : np.ndarray
        The upper power envelope.
    """
    plt.figure(figsize=(8, 5))  # Create a new figure with a specified size.
    # Plot the theoretical power response.
    plt.plot(
        time,
        p_pcc,
        label="Theoretical response from VSM",
        linewidth="3",
    )
    # Plot the lower power envelope.
    plt.plot(time, p_down, label="Pdown", linewidth=2)
    # Plot the upper power envelope.
    plt.plot(time, p_up, label="Pup", linewidth=2)
    plt.xlabel("sec")  # Set x-axis label.
    plt.ylabel("P at PCC (pu)")  # Set y-axis label.
    plt.title(title)  # Set the plot title.
    # Add a vertical line to mark the event time.
    plt.axvline(
        x=event_time + shift_time / 1000,  # Convert ms to seconds
        color="black",
        linestyle="--",
        label="t at Event Time",
    )
    plt.legend(loc="lower right")  # Display legend.
    plt.grid(True)  # Show grid.
    plt.savefig(path, bbox_inches="tight", dpi=300)  # Save the figure.
    plt.close()  # Close the figure to free up memory.
