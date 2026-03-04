#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import cmath

from dycov.model import parameters as mp


def line_pimodel(line: mp.Line_params) -> mp.Pimodel_params:
    """Obtains the symmetric pi-model parameters from the line parameters.

    Obtains the symmetric pi-model parameters from the Dynawo line model
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

    Y = 1 / complex(line.R, line.X)
    Ysh = complex(line.G, line.B)

    Y11 = Y + Ysh
    Y22 = Y + Ysh
    Y12 = -Y
    Y21 = -Y

    return mp.Pimodel_params(Y11=Y11, Y12=Y12, Y21=Y21, Y22=Y22)


def xfmr_pimodel(xfmr: mp.Xfmr_params) -> mp.Pimodel_params:
    """Obtains the general pi-model parameters from the transformer parameters.

    Obtains the general pi-model parameters from the Dynawo transformer model
    parameters R, X, G, B, rTfo, alphaTfo. It also follows the Dynawo conventions
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

    rho = xfmr.rTfo * cmath.exp(1j * xfmr.alphaTfo)
    a = 1 / rho
    Y = 1 / complex(xfmr.R, xfmr.X)
    Ysh = complex(xfmr.G, xfmr.B)

    Y11 = Y / (a * a.conjugate())
    Y22 = Y + Ysh
    Y12 = -Y / a.conjugate()
    Y21 = -Y / a

    return mp.Pimodel_params(Y11=Y11, Y12=Y12, Y21=Y21, Y22=Y22)
