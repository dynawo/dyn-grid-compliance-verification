#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from dgcv.model import parameters as mp


def line_pimodel(line: mp.Line_params) -> mp.Pimodel_params:
    """Obtains the pi-model parameters from the line parameters.

    Obtains the pi-model parameters from the Dynawo line model
    parameters R, X, G, B.

    Parameters
    ----------
    line: Line_params
        Params of the line

    Returns
    -------
    Pimodel_params
        Pi-model parameters
    """

    ytr = 1 / complex(line.R, line.X)
    ysh = complex(line.G, line.B)

    return mp.Pimodel_params(Ytr=ytr, Ysh1=ysh, Ysh2=ysh)


def xfmr_pimodel(xfmr: mp.Xfmr_params) -> mp.Pimodel_params:
    """Obtains the pi-model parameters from the transformer parameters.

    Obtains the pi-model parameters from the Dynawo transformer model
    parameters R, X, G, B, rTfo. It also follows the Dynawo conventions
    for terminal 1 and 2.
    Parameters
    ----------
    xfmr: Xfmr_params
        Params of the transformer

    Returns
    -------
    Pimodel_params
        Pi-model parameters
    """

    y = 1 / complex(xfmr.R, xfmr.X)
    ytr = xfmr.rTfo * y
    ysh1 = (xfmr.rTfo - 1) * ytr
    ysh2 = (1 - xfmr.rTfo) * y + complex(xfmr.G, xfmr.B)

    return mp.Pimodel_params(Ytr=ytr, Ysh1=ysh1, Ysh2=ysh2)
