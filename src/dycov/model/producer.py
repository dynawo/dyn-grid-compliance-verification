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

from dycov.configuration.cfg import config


class Producer:
    def __init__(self, producer_model: Path, producer_ini: Path):
        self._s_nref = config.get_float("Dynawo", "s_nref", 100.0)
        self._f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        self._producer_model_path = producer_model
        self._producer_ini_path = producer_ini.parent if producer_ini else None
        self._sim_type = None

    def get_producer_path(self) -> Path:
        """Get the Producer directory.

        Returns
        -------
        Path
            Producer directory
        """
        pass

    def get_filenames(self, zone: int = 0) -> list[str]:
        """Get the filenames of the producer model.

        Parameters
        ----------
        zone: int
            Zone to test, only applies to model validation

        Returns
        -------
        list[str]
            List of filenames.
        """
        pass

    def is_gfm(self) -> bool:
        """Check if it is a GFM producer model, only performance verification
        and model validation set the _sim_type variable.

        Returns
        -------
        bool
            True if it is a GFM producer model.
        """
        return True if self._sim_type is None else False

    def get_sim_type(self) -> int:
        """Gets the type of validation executed."""
        pass

    def get_sim_type_str(self) -> str:
        """Gets a string according to the type of validation executed."""
        pass
