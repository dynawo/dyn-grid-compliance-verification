#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""``python -m dycov.excel``: the generator on its own, until it is a DyCoV subcommand."""

import sys

from dycov.excel.generator import main

if __name__ == "__main__":
    sys.exit(main())
