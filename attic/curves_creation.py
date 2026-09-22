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
import re
import sys

import numpy as np
import pandas as pd

# Set args

parser = argparse.ArgumentParser()

parser.add_argument("curves_file", help="enter output curves file")

args = parser.parse_args()


def main():
    # Get curves file

    curves_file = args.curves_file
    df_curves = pd.read_csv(curves_file, sep=";", skipinitialspace=True)

    cols = list(df_curves.columns)

    for i in cols:
        if i[:7] == "Unnamed":
            del df_curves[i]

    # Define regex

    p2_re = re.compile(".*_line_P2Pu")

    q2_re = re.compile(".*_line_Q2Pu")

    im_re = re.compile(".*_im")

    re_re = re.compile(".*_re")

    # Match regex

    p2_list = list(filter(p2_re.match, cols))

    q2_list = list(filter(q2_re.match, cols))

    im_list = list(filter(im_re.match, cols))

    re_list = list(filter(re_re.match, cols))

    # Add all P
    if len(p2_list) != 0:
        line_line_p2pu = list(df_curves[p2_list[0]])
        del df_curves[p2_list[0]]
        p2_list.pop(0)
        for i_name in p2_list:
            for i in range(len(df_curves[i_name])):
                line_line_p2pu[i] += df_curves[i_name][i]
            del df_curves[i_name]

    # Add all Q
    if len(q2_list) != 0:
        line_line_q2pu = list(df_curves[q2_list[0]])
        del df_curves[q2_list[0]]
        q2_list.pop(0)
        for i_name in q2_list:
            for i in range(len(df_curves[i_name])):
                line_line_q2pu[i] += df_curves[i_name][i]
            del df_curves[i_name]

    # Find im-re pairs
    if len(im_list) != 0 and len(re_list) != 0:
        im_re_pairs = dict()
        for i in range(len(im_list)):
            for j in range(len(re_list)):
                if im_list[i][:-3] == re_list[j][:-3]:
                    im_re_pairs[im_list[i][:-3]] = [im_list[i], re_list[j]]

        im_re_join = dict()
        for key, value in im_re_pairs.items():
            im_re_join[key] = np.sqrt(df_curves[value[0]] ** 2 + df_curves[value[1]] ** 2)
            del df_curves[value[0]]
            del df_curves[value[1]]

    # Create the new curves file
    curves_dict = dict()

    if len(p2_list) != 0:
        curves_dict["line_line_p2pu"] = line_line_p2pu

    if len(q2_list) != 0:
        curves_dict["line_line_q2pu"] = line_line_q2pu

    if len(im_list) != 0 and len(re_list) != 0:
        for key, value in im_re_join.items():
            curves_dict[key] = list(value)

    for i in df_curves.columns:
        curves_dict[i] = list(df_curves[i])

    # times = curves_dict["time"]

    # del curves_dict["time"]

    curves_final = pd.DataFrame(curves_dict)

    curves_final = curves_final.set_index("time")

    curves_final.to_csv(curves_file, sep=";", float_format="%.3e")

    return 0


if __name__ == "__main__":
    sys.exit(main())
