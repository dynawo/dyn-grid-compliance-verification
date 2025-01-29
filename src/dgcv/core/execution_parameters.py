#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import getpass
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from dgcv.configuration.cfg import config
from dgcv.files import manage_files
from dgcv.model.producer import Producer


class Parameters:
    """Parameters defined in the command arguments.

    Args
    ----
    launcher_dwo: Path
        Dynawo launcher
    producer_model: Path
        Producer Model directory
    producer_curves_path: Path
        Producer curves directory
    selected_pcs: str
        Individual PCS to validate
    output_dir: Path
        User output directory
    only_dtr: bool
        option to validate a model using only the PCS defined in the DTR
    sim_type: int
        0 if it is an electrical performance for Synchronous Machine Model
        1 if it is an electrical performance for Power Park Module Model
        2 if it is a model validation
    """

    def __init__(
        self,
        launcher_dwo: Path,
        producer_model: Path,
        producer_curves_path: Path,
        reference_curves_path: Path,
        selected_pcs: str,
        output_dir: Path,
        only_dtr: bool,
        sim_type: int,
    ):
        # Inputs parameters
        self._launcher_dwo = launcher_dwo
        self._selected_pcs = selected_pcs
        self._output_dir = output_dir
        self._only_dtr = only_dtr

        # Read producer inputs
        self._producer = Producer(
            producer_model, producer_curves_path, reference_curves_path, sim_type
        )

        tmp_path = config.get_value("Global", "temporal_path")
        username = getpass.getuser()
        working_dir = Path(tempfile.gettempdir()) / f"{tmp_path}_{username}"
        manage_files.create_dir(working_dir, clean_first=False, all=True)

        # Remove old executions
        current_time = time.time()
        for execution_path in working_dir.iterdir():
            modification_time = execution_path.stat().st_mtime
            if (current_time - modification_time) // (24 * 3600) >= 1:
                shutil.rmtree(execution_path)

        self._working_dir = working_dir / Path(str(uuid.uuid4()))

    def get_launcher_dwo(self) -> Path:
        """Get the Dynawo launcher.

        Returns
        -------
        Path
            Dynawo launcher
        """
        return self._launcher_dwo

    def get_selected_pcs(self) -> str:
        """Get the selected PCS

        Returns
        -------
        str
            PCS name
        """
        return self._selected_pcs

    def get_producer(self) -> Producer:
        """Get the producer model

        Returns
        -------
        Producer
            Producer
        """
        return self._producer

    def get_working_dir(self) -> Path:
        """Get the temporal working directory.

        Returns
        -------
        Path
            Temporal working directory
        """
        return self._working_dir

    def get_output_dir(self) -> Path:
        """Get the user output directory.

        Returns
        -------
        Path
            User output directory
        """
        return self._output_dir

    def get_sim_type(self) -> int:
        """Get the executed validation type:
            * 0 if it is electrical performance for Synchronous Machine Model
            * 1 if it is electrical performance for Power Park Module Model
            * 10 if it is model validation

        Returns
        -------
        int
            Validation type
        """
        return self._producer.get_sim_type()

    def get_only_dtr(self) -> bool:
        """Use only the PCS of the DTR:

        Returns
        -------
        bool
            True if use only the PCS of the DTR
        """
        return self._only_dtr

    def is_valid(self) -> bool:
        """Checks if the execution of the tool is valid,
        for this the tool must have the dynamic model of the user or, failing that, the
        curves file.

        Returns
        -------
        bool
            True if it is a valid execution, False otherwise
        """
        return self._producer.is_dynawo_model() or self._producer.is_user_curves()

    def is_complete(self):
        """Checks if the execution of the tool is complete,
        for this the tool must have the dynamic model of the user and the curves file.

        Returns
        -------
        bool
            True if it is a complete execution, False otherwise
        """
        return self.is_valid() and self._producer.has_reference_curves_path()
