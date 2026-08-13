#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import sys
import shutil
from multiprocessing import Pool
from pathlib import Path
from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging
from dycov.model.pcs import Pcs


def _generate_pcs(pcs_args: tuple[GFMParameters, str, str]) -> None:
    """
    Parameters
    ----------
    pcs_args : tuple[GFMParameters, str, str]
    """
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name=producer_name, pcs_name=pcs_name, parameters=parameters)
    try:
        if not pcs.is_valid():
            dycov_logging.get_logger(name="GFMGeneration").error(
                msg=f"{pcs.get_name()} is not a valid PCS"
            )
            return
        pcs.generate()
    except (FileNotFoundError, IOError, ValueError) as e:
        # Avoid crashing parallel processes by catching specific errors and logging gracefully
        if dycov_logging.get_logger(name="GFMGeneration").getEffectiveLevel() == logging.DEBUG:
            dycov_logging.get_logger(name="GFMGeneration").exception(
                msg=f"Aborted execution for {pcs.get_name()}. {e}"
            )
        else:
            dycov_logging.get_logger(name="GFMGeneration").error(
                msg=f"Aborted execution for {pcs.get_name()}. {e}"
            )
        return


class GFMGeneration:
    def __init__(self, parameters: GFMParameters) -> None:
        """
        Parameters
        ----------
        parameters : GFMParameters
        """
        self._parameters = parameters
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            dycov_logging.get_logger(name="GFMGeneration").warning(
                msg="Exiting. Please rename your current Results directory, otherwise it will be erased and a new one will be created."
            )
            sys.exit()
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        """
        Returns
        -------
        list[str]
        """
        dycov_logging.get_logger(name="GFMGeneration").info(msg="DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()
        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())
        self.__populate_validation_pcs(
            validation_pcs=validation_pcs, validation_key="gridforming_pcs", validation_path="gfm"
        )
        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
    ) -> None:
        """
        Parameters
        ----------
        validation_pcs : set[str]
        validation_key : str
        validation_path : str
        """
        tool_path = Path(__file__).resolve().parent.parent
        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))
        if not validation_pcs:
            if not self._parameters.get_only_dtr():
                validation_pcs.update(
                    manage_files.list_directories(
                        config.get_config_dir() / self._templates_path / validation_path
                    )
                )
            validation_pcs.update(
                manage_files.list_directories(tool_path / self._templates_path / validation_path)
            )
        for item in list(validation_pcs):
            if "aliases" in item:
                validation_pcs.remove(item)

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """
        Returns
        -------
        list[tuple[GFMParameters, str, str]]
        """
        pcs_list: list[tuple[GFMParameters, str, str]] = []
        all_producer_files = self._parameters.get_producer().get_filenames()
        for producer_name in all_producer_files:
            pcs_list.extend(
                (self._parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
            )
        return pcs_list

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
        """
        Parameters
        ----------
        use_parallel : bool, optional
        num_processes : int, optional
        """
        if use_parallel:
            dycov_logging.get_logger(name="GFMGeneration").info(
                msg=f"Generating envelopes in parallel using {num_processes} processes."
            )
            with Pool(processes=num_processes) as pool:
                pool.map(func=_generate_pcs, iterable=self._pcs_list)
        else:
            dycov_logging.get_logger(name="GFMGeneration").info(
                msg="Generating envelopes sequentially."
            )
            for pcs_tuple in self._pcs_list:
                _generate_pcs(pcs_args=pcs_tuple)

        for _, pcs_name, producer_name in self._pcs_list:
            src_dir = self._parameters.get_working_dir() / producer_name
            dst_dir = self._parameters.get_output_dir() / pcs_name

            if src_dir.exists():
                shutil.copytree(src=src_dir, dst=dst_dir, dirs_exist_ok=True)

        manage_files.remove_dir(self._parameters.get_working_dir())
