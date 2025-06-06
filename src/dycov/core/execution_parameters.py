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

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.producer import Producer

LOGGER = dycov_logging.get_logger("Execution Parameters")


class Parameters:
    """Parameters defined in the command arguments.

    Attributes
    ----
    launcher_dwo: Path
        Dynawo launcher.
    producer_model: Path
        Producer Model directory.
    producer_curves_path: Path
        Producer curves directory.
    reference_curves_path: Path
        Reference curves directory.
    selected_pcs: str
        Individual PCS to validate.
    output_dir: Path
        User output directory.
    only_dtr: bool
        Option to validate a model using only the PCS defined in the DTR.
    verification_type: int
        0 if it is an electrical performance verification.
        10 if it is a model validation.
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
        verification_type: int,
    ):
        """
        Initializes the Parameters instance with provided execution arguments.
        """
        self._launcher_dwo = launcher_dwo
        self._selected_pcs = selected_pcs
        self._output_dir = output_dir
        self._only_dtr = only_dtr

        # Initialize Producer model
        self._producer = Producer(
            producer_model, producer_curves_path, reference_curves_path, verification_type
        )

        self._working_dir = self._create_working_dir()
        LOGGER.info(f"Working directory created at: {self._working_dir}")

    def _create_working_dir(self) -> Path:
        """Creates a unique temporary working directory for the current execution.

        The directory name is based on the current username, timestamp, and a UUID.

        Returns
        -------
        Path
            The path to the newly created working directory.
        """
        tmp_path_prefix = config.get_value("Global", "temporal_path")
        username = getpass.getuser()
        base_working_dir = Path(tempfile.gettempdir()) / f"{tmp_path_prefix}_{username}"
        manage_files.create_dir(base_working_dir, clean_first=False, all=True)

        # Remove old executions (older than 24 hours)
        current_time = time.time()
        for execution_path in base_working_dir.iterdir():
            if current_time - execution_path.stat().st_mtime >= 24 * 3600:
                LOGGER.debug(f"Removing old execution: {execution_path}")
                shutil.rmtree(execution_path)

        return base_working_dir / Path(str(uuid.uuid4()))

    def get_launcher_dwo(self) -> Path:
        """Get the Dynawo launcher path.

        Returns
        -------
        Path
            Dynawo launcher path.
        """
        return self._launcher_dwo

    def get_selected_pcs(self) -> str:
        """Get the name of the selected PCS.

        Returns
        -------
        str
            PCS name.
        """
        return self._selected_pcs

    def get_producer(self) -> Producer:
        """Get the Producer object.

        Returns
        -------
        Producer
            The Producer object containing model and curve information.
        """
        return self._producer

    def get_working_dir(self) -> Path:
        """Get the temporal working directory path.

        Returns
        -------
        Path
            Temporal working directory path.
        """
        return self._working_dir

    def get_output_dir(self) -> Path:
        """Get the user output directory path.

        Returns
        -------
        Path
            User output directory path.
        """
        return self._output_dir

    def get_sim_type(self) -> int:
        """Get the executed validation type.

        Returns
        -------
        int
            Validation type:
            * 1: Electrical performance for Synchronous Machine Model.
            * 2: Electrical performance for Power Park Module Model.
            * 3: Electrical performance for Storage Model.
            * 11: Model validation for Power Park Module Model.
            * 12: Model validation for Storage Model.
        """
        return self._producer.get_sim_type()

    def get_only_dtr(self) -> bool:
        """Check if only PCS defined in the DTR should be used.

        Returns
        -------
        bool
            True if only DTR PCS should be used, False otherwise.
        """
        return self._only_dtr

    def is_dynawo_model_valid(self) -> bool:
        """Checks if the Dynawo model is valid.

        Returns
        -------
        bool
            True if the Dynawo model is valid, False otherwise.
        """
        return self._producer.is_dynawo_model()

    def is_user_curves_valid(self) -> bool:
        """Checks if the user-provided curves are valid.

        Returns
        -------
        bool
            True if the user curves are valid, False otherwise.
        """
        return self._producer.is_user_curves()

    def has_reference_curves_path(self) -> bool:
        """Check if a reference curves directory is provided.

        Returns
        -------
        bool
            True if a reference curves directory exists, False otherwise.
        """
        return self._producer.has_reference_curves_path()

    def is_valid(self) -> bool:
        """Checks if the execution of the tool is valid.
        The tool requires either a valid dynamic model or valid user curves.

        Returns
        -------
        bool
            True if it is a valid execution, False otherwise.
        """
        return self.is_dynawo_model_valid() or self.is_user_curves_valid()

    def is_complete(self) -> bool:
        """Checks if the execution of the tool is complete.
        For a complete execution, both a valid dynamic model (or user curves) and
        reference curves must be available.

        Returns
        -------
        bool
            True if it is a complete execution, False otherwise.
        """
        return self.is_valid() and self.has_reference_curves_path()
