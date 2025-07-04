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

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.files.producer_curves import check_curves, create_producer_curves
from dycov.files.producer_dyd_file import check_dynamic_models, create_producer_dyd_file
from dycov.files.producer_ini_file import check_ini_parameters, create_producer_ini_file
from dycov.files.producer_par_file import check_parameters, create_producer_par_file
from dycov.logging.logging import dycov_logging

LOGGER = dycov_logging.get_logger("Input Template Generator")


class InputTemplateGenerator:
    """
    A class to generate input templates for Dynawo simulations.
    """

    def _get_input(self, text: str) -> str:
        """
        Prompts the user for input and returns the response.

        Parameters
        ----------
        text: str
            The message to display to the user.

        Returns
        -------
        str
            The user's input.
        """
        return input(text)

    def _copy_input_templates(self, target: Path, template: str) -> None:
        """
        Copies input template files to the target directory.

        Parameters
        ----------
        target: Path
            The target directory where templates will be copied.
        template: str
            The name of the template to copy.
        """
        input_templates_path = config.get_value("Global", "input_templates_path")
        manage_files.copy_path(
            Path(input_templates_path) / template.replace("_", "/"), target, dirs_exist_ok=True
        )

    def _create_and_validate_file(
        self,
        file_type: str,
        target: Path,
        topology: str,
        template: str,
        creation_func,
        check_func,
        prompt_message: str,
    ) -> None:
        """
        Creates a producer file and repeatedly prompts the user to edit it until it passes
        validation.

        Parameters
        ----------
        file_type: str
            The type of file being created (e.g., "DYD", "PAR", "INI", "curves").
        target: Path
            The target directory for the file.
        topology: str
            The topology relevant to the file creation.
        template: str
            The template name used for file creation.
        creation_func: callable
            The function responsible for creating the file.
        check_func: callable
            The function responsible for validating the file.
        prompt_message: str
            The message to display to the user for editing instructions.
        """
        LOGGER.info(f"Creating the input {file_type} file in {target}.")
        if file_type == "PAR":
            # _create_par_template requires an additional argument 'launcher_dwo'
            # This needs to be handled if we want to truly generalize; for now,
            # this method assumes creation_func only needs (target, topology, template)
            # A more flexible solution would be to pass *args and **kwargs to creation_func
            # or have separate handlers for each file type.
            raise NotImplementedError(
                "PAR file creation needs specific handling for 'launcher_dwo' argument."
            )
        else:
            creation_func(target, topology, template)

        self._get_input(
            f"Edit Producer.{file_type.lower()} to {prompt_message}. Press Enter when done."
        )
        while not check_func(
            target if file_type != "curves" else (target / "ReferenceCurves"),
            template if file_type != "curves" else None,
        ):
            self._get_input(
                f"Editing Producer.{file_type.lower()} is necessary to {prompt_message}. "
                "Press Enter when done."
            )

    def _create_dyd_template(self, target: Path, topology: str, template: str) -> None:
        """
        Creates and validates the Producer.dyd template.

        Parameters
        ----------
        target: Path
            The target directory for the DYD file.
        topology: str
            The topology of the DYD file.
        template: str
            The template name.
        """
        LOGGER.info(f"Creating the input DYD file in {target}.")
        create_producer_dyd_file(target, topology, template)
        self._get_input(
            "Edit Producer.dyd to complete each equipment with a dynamic model. "
            "Press Enter when done."
        )
        while not check_dynamic_models(target, template):
            self._get_input(
                "Edit Producer.dyd is necessary to complete each equipment with a dynamic model. "
                "Press Enter when done."
            )

    def _create_par_template(
        self, launcher_dwo: Path, target: Path, topology: str, template: str
    ) -> None:
        """
        Creates and validates the Producer.par template.

        Parameters
        ----------
        launcher_dwo: Path
            Dynawo launcher path.
        target: Path
            The target directory for the PAR file.
        topology: str
            The topology of the PAR file.
        template: str
            The template name.
        """
        LOGGER.info(f"Creating the input PAR file in {target}.")
        create_producer_par_file(launcher_dwo, target, topology, template)
        self._get_input(
            "Edit Producer.par to complete each parameter with a value. Press Enter when done."
        )
        while not check_parameters(target, template):
            self._get_input(
                "Edit Producer.par is necessary to complete each parameter with a value. "
                "Press Enter when done."
            )

    def _create_ini_template(self, target: Path, topology: str, template: str) -> None:
        """
        Creates and validates the Producer.ini template.

        Parameters
        ----------
        target: Path
            The target directory for the INI file.
        topology: str
            The topology of the INI file.
        template: str
            The template name.
        """
        LOGGER.info(f"Creating the input INI file in {target}.")
        create_producer_ini_file(target, topology, template)
        self._get_input(
            "Edit Producer.ini to complete each parameter with a value. Press Enter when done."
        )
        while not check_ini_parameters(target, template):
            self._get_input(
                "Edit Producer.ini is necessary to complete each parameter with a value. "
                "Press Enter when done."
            )

    def _create_curves_template(self, target: Path, topology: str, template: str) -> None:
        """
        Creates and validates the reference curves files.

        Parameters
        ----------
        target: Path
            The base target directory.
        topology: str
            The topology relevant to the curves creation.
        template: str
            The template name.
        """
        ref_target = target / "ReferenceCurves"
        LOGGER.info(f"Creating the reference curves files in {ref_target}.")
        create_producer_curves(target, ref_target, template)
        self._get_input(
            "Edit CurvesFiles.ini to complete each parameter with a curves file. "
            "Press Enter when done."
        )
        while not check_curves(ref_target):
            self._get_input(
                "Edit CurvesFiles.ini is necessary to complete each parameter with a curves file. "
                "Press Enter when done."
            )

    def create_input_template(
        self, launcher_dwo: Path, target: Path, topology: str, template: str
    ) -> None:
        """Create an input template in target path with the selected topology.

        Parameters
        ----------
        launcher_dwo: Path
            Dynawo launcher path.
        target: Path
            Target path where the input template will be created.
        topology: str
            Topology used for the DYD file.
        template: str
            Input template name:
            * 'performance_SM' if it is electrical performance for Synchronous Machine Model
            * 'performance_PPM' if it is electrical performance for Power Park Module Model
            * 'performance_BESS' if it is electrical performance for Storage Model
            * 'model_PPM' if it is model validation for Power Park Module Model
            * 'model_BESS' if it is model validation for Storage Model
        """

        if target.exists():
            LOGGER.error("The output path already exists, please indicate a new path.")
            return

        manage_files.create_dir(target)
        self._copy_input_templates(target, template)

        # Create and validate DYD file
        self._create_dyd_template(target, topology, template)

        # Create and validate PAR file
        self._create_par_template(launcher_dwo, target, topology, template)

        # Create and validate INI file
        self._create_ini_template(target, topology, template)

        # Create and validate curves files
        self._create_curves_template(target, topology, template)

        print("Done")
