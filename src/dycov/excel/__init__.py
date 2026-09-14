#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""Excel -> DyCoV input generation.

Reads an RTE workbook and writes the producer files of both zones plus the reference-curve tree,
which is what the rest of DyCoV consumes. The family-specific part is confined to the front-end
that parses the workbook and resolves the selected variants to a Dynawo model; everything
downstream depends only on that resolution, the workbook values and the topology.
"""
