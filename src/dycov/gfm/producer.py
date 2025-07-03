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

import pandas as pd

from dycov.model.producer import Producer


class CSVProducer(Producer):

    def __init__(self, producer_csv: Path):

        super().__init__(None, producer_csv)
        self._data = pd.read_csv(producer_csv, sep=";")

    def get_sim_type_str(self) -> str:
        """Gets a string according to the type of validation executed.

        Returns
        -------
        str
            'gfm'
        """
        return "gfm"

    def get_producer_path(self) -> Path:
        return self._producer_csv_path

    def get_effective_reactance(self) -> float:
        return self._data["Xeff"][0]

    def get_damping_constant(self):
        return self._data["D"][0]

    def get_inertia_constant(self):
        return self._data["H"][0]

    def get_nominal_voltage(self):
        return self._data["Unom"][0]

    def get_nominal_apparent_power(self):
        return self._data["Snom"][0]
