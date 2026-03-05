#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import argparse
import sys

import pandas as pd

from dycov.logging.logging import dycov_logging

# Set args

parser = argparse.ArgumentParser()

parser.add_argument("curves_file", help="enter output curves file")

parser.add_argument(
    "steady_time",
    help="set target time in seconds in order to define if an state is steady or not",
)

parser.add_argument("curve_name", help="define which is the target curve")

args = parser.parse_args()

THRESH = 0.002


def main():
    # Get curves file and steady time

    curves_file = args.curves_file
    df_curves = pd.read_csv(curves_file, sep=";", skipinitialspace=True)
    steady_time = float(args.steady_time)
    curve_name = args.curve_name

    if steady_time <= 0:
        raise NameError("steady time is a non-valid value")

    # Get the first position of steady time in the dataframe
    time_pos = -1

    real_time = df_curves["time"][len(df_curves["time"]) - 1] - steady_time

    for i in range(len(df_curves["time"])):
        if real_time <= df_curves["time"][i]:
            time_pos = i
            break

    if time_pos == -1:
        raise NameError("steady time is bigger than simulation time")

    lst_val = list(df_curves[curve_name])[time_pos:]

    # If the value is less than 1, we use absolute value
    if abs(lst_val[-1]) <= 1:
        mean_val_max = lst_val[-1] + THRESH
        mean_val_min = lst_val[-1] - THRESH
    # If the value is more than 1, we use relative value
    else:
        mean_val = lst_val[-1]
        mean_val_max = mean_val + abs(THRESH * mean_val)
        mean_val_min = mean_val - abs(THRESH * mean_val)

    dycov_logging.get_logger("Attic").info("Min threshold value = " + str(mean_val_min))
    dycov_logging.get_logger("Attic").info("Max threshold value = " + str(mean_val_max))

    # Check all values inside the steady time
    steady_state = True
    for i in lst_val:
        if i < mean_val_min or i > mean_val_max:
            steady_state = False
            break

    if steady_state:
        dycov_logging.get_logger("Attic").info("\nThe curve has reached steady state")

        # Get the first position of the steady state
        lst_val = list(df_curves[curve_name])
        first_steady = 0
        for i in range(len(lst_val)):
            pos = len(lst_val) - (i + 1)
            if lst_val[pos] < mean_val_min or lst_val[pos] > mean_val_max:
                first_steady = pos
                break

        dycov_logging.get_logger("Attic").info(
            "The steady state is reached in " + str(df_curves["time"][first_steady]) + " seconds"
        )

    else:
        dycov_logging.get_logger("Attic").info("\nThe curve has NOT reached steady state")

    return 0


if __name__ == "__main__":
    sys.exit(main())
