#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from dycov.model import parameters as mp


def line_pimodel(line: mp.LineParams) -> mp.PimodelParams:
    """Obtains the pi-model parameters from the line parameters.

    Obtains the pi-model parameters from the Dynawo line model
    parameters R, X, G, B.

    Parameters
    ----------
    line: LineParams
        Params of the line

    Returns
    -------
    PimodelParams
        Pi-model parameters
    """

    ytr = 1 / complex(line.r, line.x)
    ysh = complex(line.g, line.b)

    return mp.PimodelParams(y_tr=ytr, y_sh1=ysh, y_sh2=ysh)


def xfmr_pimodel(xfmr: mp.XfmrParams) -> mp.PimodelParams:
    """Obtains the pi-model parameters from the transformer parameters.

    Obtains the pi-model parameters from the Dynawo transformer model
    parameters R, X, G, B, rTfo. It also follows the Dynawo conventions
    for terminal 1 and 2.
    Parameters
    ----------
    xfmr: XfmrParams
        Params of the transformer

    Returns
    -------
    PimodelParams
        Pi-model parameters
    """

    y = 1 / complex(xfmr.r, xfmr.x)
    ytr = xfmr.r_tfo * y
    ysh1 = (xfmr.r_tfo - 1) * ytr
    ysh2 = (1 - xfmr.r_tfo) * y + complex(xfmr.g, xfmr.b)

    return mp.PimodelParams(y_tr=ytr, y_sh1=ysh1, y_sh2=ysh2)
