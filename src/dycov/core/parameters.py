#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
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

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.model.producer import Producer


class Parameters:
    """Parent class to define the common parameters.

    Args
    ----
    launcher_dwo: Path
        Dynawo launcher
    selected_pcs: str
        Individual PCS to validate
    output_dir: Path
        User output directory
    """

    def __init__(
        self,
        launcher_dwo: Path,
        selected_pcs: str,
        output_dir: Path,
        only_dtr: bool,
    ):
        # Inputs parameters
        self._launcher_dwo = launcher_dwo
        self._selected_pcs = selected_pcs
        self._output_dir = output_dir
        self._only_dtr = only_dtr

        tmp_path = config.get_value("Global", "temporal_path")
        username = getpass.getuser()
        working_dir = Path(tempfile.gettempdir()) / f"{tmp_path}_{username}"
        manage_files.create_dir(working_dir, clean_first=False, all=True)

        # Remove old executions
        current_time = time.time()
        for execution_path in working_dir.iterdir():
            modification_time = execution_path.stat().st_mtime
            # Delete old directories (24h)
            if current_time - modification_time >= 24 * 3600:
                shutil.rmtree(execution_path)

        self._working_dir = working_dir / Path(str(uuid.uuid4()))

        # The parameter is initialized in the child class
        self._producer = None

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

    def get_output_dir(self) -> Path:
        """Get the user output directory.

        Returns
        -------
        Path
            User output directory
        """
        return self._output_dir

    def get_only_dtr(self) -> bool:
        """Use only the PCS of the DTR:

        Returns
        -------
        bool
            True if use only the PCS of the DTR
        """
        return self._only_dtr

    def get_working_dir(self) -> Path:
        """Get the temporal working directory.

        Returns
        -------
        Path
            Temporal working directory
        """
        return self._working_dir

    def get_producer(self) -> Producer:
        """Get the producer model

        Returns
        -------
        Producer
            Producer
        """
        return self._producer

    def is_valid(self) -> bool:
        """Checks if the execution of the tool is valid.

        Returns
        -------
        bool
            True if it is a valid execution, False otherwise
        """
        pass
