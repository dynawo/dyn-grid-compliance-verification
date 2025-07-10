#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#


import re
from pathlib import Path

import pandas as pd

from dycov.model.producer import Producer


class CSVProducer(Producer):
    """
    A class used to represent a producer from a CSV file.

    This class extends the Producer class and provides methods to
    access producer-related data stored in a CSV file.
    """

    def __init__(self, producer_csv: Path) -> None:
        """
        Initializes the CSVProducer with the path to the producer CSV file.

        Parameters
        ----------
        producer_csv : Path
            The path to the producer CSV file.
        """
        super().__init__(None, producer_csv)
        self._data = pd.read_csv(producer_csv, sep=";")

    def get_producer_path(self) -> Path:
        """
        Get the path to the producer CSV file.

        Returns
        -------
        Path
            The path to the producer CSV file.
        """
        return self._producer_csv_path

    def get_filenames(self, zone: int = 0) -> list[str]:
        """
        Get the filenames of the producer model.

        Parameters
        ----------
        zone : int, optional
            Zone to test, only applies to model validation. Defaults to 0.

        Returns
        -------
        list[str]
            List of filenames.
        """
        pattern = re.compile(r".*.[cC][sS][vV]")
        return sorted(
            [
                file.stem
                for file in self._producer_csv_path.resolve().iterdir()
                if pattern.match(str(file))
            ]
        )

    def get_sim_type_str(self) -> str:
        """
        Gets a string according to the type of validation executed.

        Returns
        -------
        str
            'gfm'
        """
        return "gfm"

    def get_effective_reactance(self) -> float:
        """
        Get the effective reactance from the producer data.

        Returns
        -------
        float
            The effective reactance.
        """
        return self._data["Xeff"][0]

    def get_damping_constant(self) -> float:
        """
        Get the damping constant from the producer data.

        Returns
        -------
        float
            The damping constant.
        """
        return self._data["D"][0]

    def get_inertia_constant(self) -> float:
        """
        Get the inertia constant from the producer data.

        Returns
        -------
        float
            The inertia constant.
        """
        return self._data["H"][0]

    def get_nominal_voltage(self) -> float:
        """
        Get the nominal voltage from the producer data.

        Returns
        -------
        float
            The nominal voltage.
        """
        return self._data["Unom"][0]

    def get_nominal_apparent_power(self) -> float:
        """
        Get the nominal apparent power from the producer data.

        Returns
        -------
        float
            The nominal apparent power.
        """
        return self._data["Snom"][0]
