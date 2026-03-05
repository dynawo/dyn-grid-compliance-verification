import argparse
import sys

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("curves_file", help="enter output curves file")
args = parser.parse_args()


def main():
    # Get curves file

    curves_file = args.curves_file
    df_curves = pd.read_csv(curves_file, sep=";", skipinitialspace=True)
    time = df_curves["time"]
    df_curves.drop(columns=["time"])

    mu, sigma = 0, 0.001
    row, col = df_curves.shape
    noise = np.random.normal(mu, sigma, [row, col])

    df_noise_curves = df_curves * (1 + noise)

    df_noise_curves["time"] = time
    df_noise_curves = df_noise_curves.set_index("time")
    df_noise_curves.to_csv(curves_file, sep=";", float_format="%.3e")


if __name__ == "__main__":
    sys.exit(main())
