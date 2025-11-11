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

from dycov.core.parameters import Parameters
from dycov.validate.producer import ModelProducer


class ValidationParameters(Parameters):
    """Parameters to define the validation of a model.

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
        # Inputs parameters
        super().__init__(launcher_dwo, selected_pcs, output_dir, only_dtr)

        # Read producer inputs
        self._producer = ModelProducer(
            producer_model, producer_curves_path, reference_curves_path, verification_type
        )

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
