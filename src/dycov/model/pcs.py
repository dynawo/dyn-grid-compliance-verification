#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path
from typing import Union

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.logging.logging import dycov_logging
from dycov.model.benchmark import Benchmark
from dycov.model.producer import Producer


class Pcs:
    """High-level representation of the pcs described in the DTR.

    Args
    ----
    pcs_name: str
        Name of the pcs
    parameters: Parameters
        Tool parameters
    """

    def __init__(self, pcs_name: str, parameters: Parameters):
        self._name = pcs_name
        self._producer = parameters.get_producer()
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._figures_description = {}

        self._has_pcs_config = False
        self._has_user_config = False

        # TODO: (M-topologies) New variable to save the current Zone1 DYD file
        #       (Its an input parameter)
        report_name, bms_by_pcs, pcs_id, pcs_zone = self.__prepare_pcs_config(
            parameters.get_producer()
        )
        self._report_name = report_name
        self._id = int(pcs_id)
        self._zone = int(pcs_zone)
        self._bm_list = [
            Benchmark(pcs_name, pcs_id, pcs_zone, report_name, bm_name, parameters)
            for bm_name in bms_by_pcs
        ]

    def __repr__(self):
        return self._name

    def __str__(self):
        return self._name

    def __prepare_pcs_config(self, producer: Producer) -> tuple[str, list, int]:

        # It checks if the PCS configuration file exists in the tool and reads it.
        pcs_path = self.__get_pcs_path(producer, Path(__file__).resolve().parent.parent)
        dycov_logging.get_logger("PCS").debug(f"PCS Path {pcs_path}")
        if pcs_path and pcs_path.exists():
            config.load_pcs_config(pcs_path)
            self._has_pcs_config = True

        # It checks if the PCS configuration file exists in the user directory and reads it.
        # The order is important, since the user configuration must override the tool
        #  configuration if both files exists
        pcs_path = self.__get_pcs_path(producer, config.get_config_dir())
        dycov_logging.get_logger("PCS").debug(f"User PCS Path {pcs_path}")
        if pcs_path and pcs_path.exists():
            config.load_pcs_config(pcs_path)
            self._has_user_config = True

        # Read configurations
        report_name = config.get_value(self._name, "report_name")
        pcs_id = config.get_int(self._name, "id", 0)
        pcs_zone = config.get_int(self._name, "zone", 0)
        bms_by_pcs = config.get_list("PCS-Benchmarks", self._name)

        return report_name, bms_by_pcs, pcs_id, pcs_zone

    def __get_pcs_path(self, producer: Producer, source_path: Path) -> Union[Path, None]:
        path = source_path / self._templates_path / producer.get_sim_type_str() / self._name
        if not path.exists():
            return None

        files = {file.stem.lower(): file for file in list(path.glob("*.[iI][nN][iI]"))}
        if "pcsdescription" in files:
            return files["pcsdescription"]
        elif len(files) > 0:
            file = files[list(files.keys())[0]]
            dycov_logging.get_logger("PCS").warning(
                f"Loading '{file.name}'. To avoid confusion it is recommended to rename the "
                f"configuration file to use the name: 'PCS_Description.ini'"
            )
            return file

        return None

    def validate(
        self,
        summary_list: list,
    ) -> tuple[str, bool, dict]:
        """Validate the current pcs.

        Parameters
        ----------
        summary_list: list
            Compliance summary by pcs

        Returns
        -------
        str
            Name of the LaTex file template
        bool
            True if all pcs are success, False otherwise
        dict
            Results of the validations applied in the pcs
        """
        pcs_results = {}
        success = False
        self._producer.set_zone(self._zone)
        for bm in self._bm_list:
            success |= bm.validate(
                summary_list,
                pcs_results,
            )
            self._figures_description[self._name + CASE_SEPARATOR + bm.get_name()] = (
                bm.get_figures_description()
            )

        return self._report_name, success, pcs_results

    def get_name(self) -> str:
        """Get the PCS name.

        Returns
        -------
        str
            PCS name
        """
        return self._name

    def get_figures_description(self) -> dict:
        """Get the figure description.

        Returns
        -------
        dict
            Description of every figure to plot by PCS
        """
        return self._figures_description

    def is_valid(self) -> bool:
        """Check if the PCS is well-formed.

        Returns
        -------
        bool
            True if it is a valid PCS
        """
        return self._has_pcs_config or self._has_user_config
