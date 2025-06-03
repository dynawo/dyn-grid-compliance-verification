#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import configparser
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dycov.model.parameters import Gen_params

# TODO: remove generator types ("WTG", "WT", "Photovoltaics", etc. ==> we'll need
#       entries in the master dictionary).
#       The same goes for generator families ("IEC", "Wecc").
#
FAMILY_LEVEL_MAP = {
    "Wecc": {
        "family": "WECC",
        "types": {
            "WTG": "Plant",
            "WT": "Turbine",
            "Photovoltaics": "Plant",
            "BESS": "Plant",
            "NoPlantControl": "Turbine",
        },
    },
    "IEC": {"family": "IEC", "types": {"IECWPP": "Plant", "IECWT": "Turbine"}},
}


def _load_dictionary(filename: str, variables: configparser.ConfigParser):
    """
    Loads configuration from a dictionary file into a ConfigParser object.

    It first attempts to load from the tool's dictionary directory and then
    from a user-specific dictionary directory, allowing for overrides.

    Parameters
    ----------
    filename: str
        The name of the dictionary file (e.g., "Bus.ini").
    variables: configparser.ConfigParser
        The ConfigParser instance to load the dictionary into.
    """
    dictionary = Path(__file__).resolve().parent / "dictionary"
    if os.name == "nt":
        config_dir = Path.home() / "AppData/Local/dycov/user_models/dictionary"
    else:
        config_dir = Path.home() / ".config/dycov/user_models/dictionary"

    # Load the tool dictionary
    variables.read(dictionary / filename)

    # Load the user dictionary, if it exists, to allow for custom overrides
    if (config_dir / filename).exists():
        variables.read(config_dir / filename)


def _is_valid_control_mode_parameters(generator_parameters: dict, valid_parameters: dict) -> bool:
    """
    Checks if a given set of generator parameters matches the valid parameters for a control mode.

    Parameters
    ----------
    generator_parameters: dict
        The parameters provided for the generator's control mode.
    valid_parameters: dict
        The valid parameters defined for a specific control mode.

    Returns
    -------
    bool
        True if all valid parameters are present in generator_parameters and their
        values match (case-insensitive), False otherwise.
    """
    for parameter_name in valid_parameters.keys():
        if (
            parameter_name not in generator_parameters
            or generator_parameters[parameter_name].lower()
            != valid_parameters[parameter_name].lower()
        ):
            return False
    return True


def get_generator_family_level(generator: Gen_params) -> tuple[str, str]:
    """
    Determines the family and level of a generator based on its library.

    Parameters
    ----------
    generator: Gen_params
        Generator parameters, including its library (lib).

    Returns
    -------
    tuple[str, str]
        A tuple containing the generator family and level. Returns empty strings
        if the family or type is not found in the `FAMILY_LEVEL_MAP`.
    """
    for key, value in FAMILY_LEVEL_MAP.items():
        if key in generator.lib:
            family = value["family"]
            for type_key, level in value["types"].items():
                if type_key in generator.lib:
                    return family, level
            return family, ""  # Return family if type is not found
    return "", ""  # Return empty if family is not found


@dataclass(frozen=True)
class Translator:
    """
    Provides translation services for Dynawo variables and control modes.

    This immutable class loads and holds mappings from various configuration files
    (Bus, Synch_Gen, Power_Park, etc.) to translate tool-specific variable names
    into Dynawo-compatible names and manage control mode parameters.
    """

    _bus: configparser.ConfigParser
    _synchronous_machine: configparser.ConfigParser
    _power_park: configparser.ConfigParser
    _storage: configparser.ConfigParser
    _line: configparser.ConfigParser
    _load: configparser.ConfigParser
    _transformer: configparser.ConfigParser
    _control_modes: configparser.ConfigParser

    def _get_control_modes_by_generator(
        self, generator: Gen_params, generator_control_mode: str
    ) -> list[str]:
        """
        Retrieves a list of valid control modes for a given generator and control mode name.

        Parameters
        ----------
        generator: Gen_params
            The generator parameters.
        generator_control_mode: str
            The name of the generator's control mode (e.g., "VoltageControl").

        Returns
        -------
        list[str]
            A list of valid control mode names (sections) that apply to the generator.
            Returns an empty list if no matching control modes are found.
        """
        family, level = get_generator_family_level(generator)
        option = f"{generator_control_mode}_{family}_{level}"
        if self._control_modes.has_option("ControlModes", option):
            return self._control_modes.get("ControlModes", option).split(",")
        else:
            return []

    def _get_control_mode_parameters(self, control_mode: str) -> dict[str, str]:
        """
        Retrieves all parameters and their values for a specific control mode.

        Parameters
        ----------
        control_mode: str
            The name of the control mode (which corresponds to a section in Control_Modes.ini).

        Returns
        -------
        dict[str, str]
            A dictionary where keys are parameter names and values are their string
            representations.
        """
        parameters = self._control_modes.options(control_mode)
        valid_parameters = {}
        for parameter in parameters:
            valid_parameters[parameter] = self._control_modes.get(control_mode, parameter)
        return valid_parameters

    def get_dynawo_variable(self, lib: str, name: str) -> tuple[int, Optional[str]]:
        """
        Gets the Dynawo variable name and its sign for a given tool variable name.

        This method searches across different configuration sections (bus, synchronous machine,
        power park, etc.) to find the corresponding Dynawo variable.

        Parameters
        ----------
        lib: str
            The Dynawo dynamic model name (e.g., "PSSE_GENROU").
        name: str
            The tool's variable name (e.g., "P0").

        Returns
        -------
        tuple[int, Optional[str]]
            A tuple where the first element is the sign of the variable (1 or -1)
            and the second element is the translated Dynawo variable name.
            Returns (1, None) if the variable is not found.
        """
        sign = 1
        translated_name = None
        # Check each configuration parser for the variable
        if self._bus.has_option(lib, name):
            translated_name = self._bus.get(lib, name)
        elif self._synchronous_machine.has_option(lib, name):
            translated_name = self._synchronous_machine.get(lib, name)
        elif self._power_park.has_option(lib, name):
            translated_name = self._power_park.get(lib, name)
        elif self._storage.has_option(lib, name):
            translated_name = self._storage.get(lib, name)
        elif self._line.has_option(lib, name):
            translated_name = self._line.get(lib, name)
        elif self._load.has_option(lib, name):
            translated_name = self._load.get(lib, name)
        elif self._transformer.has_option(lib, name):
            translated_name = self._transformer.get(lib, name)
        elif self._control_modes.has_option(lib, name):
            translated_name = self._control_modes.get(lib, name)

        # Check for negative sign prefix
        if translated_name and translated_name.startswith("-"):
            sign = -1
            translated_name = translated_name[1:]

        return sign, translated_name

    def get_curve_variable(self, equipment_id: str, lib: str, name: str) -> Optional[str]:
        """
        Gets the Dynawo curve name for a given equipment and variable.

        The curve name is constructed by concatenating the equipment ID and the
        translated Dynawo variable name.

        Parameters
        ----------
        equipment_id: str
            The identifier of the equipment (e.g., "Generator_1").
        lib: str
            The Dynawo dynamic model name associated with the equipment.
        name: str
            The tool's variable name for which the curve name is desired.

        Returns
        -------
        Optional[str]
            The Dynawo curve name, or None if the Dynawo variable name cannot be found.
        """
        _, suffix = self.get_dynawo_variable(lib, name)
        if not suffix:
            return None

        # The configuration files store variables for the PAR file; in the case of curves,
        # the ID of the element must be concatenated with the variable using the character '_'.
        return equipment_id + "_" + suffix

    def get_bus_models(self) -> list[str]:
        """
        Gets a list of available dynamic bus models.

        Returns
        -------
        list[str]
            A list of section names from the bus configuration, representing available models.
        """
        return self._bus.sections()

    def get_synchronous_machine_models(self) -> list[str]:
        """
        Gets a list of available dynamic synchronous machine models.

        Returns
        -------
        list[str]
            A list of section names from the synchronous machine configuration.
        """
        return self._synchronous_machine.sections()

    def get_power_park_models(self) -> list[str]:
        """
        Gets a list of available dynamic power park models.

        Returns
        -------
        list[str]
            A list of section names from the power park configuration.
        """
        return self._power_park.sections()

    def get_storage_models(self) -> list[str]:
        """
        Gets a list of available dynamic storage models.

        Returns
        -------
        list[str]
            A list of section names from the storage configuration.
        """
        return self._storage.sections()

    def get_line_models(self) -> list[str]:
        """
        Gets a list of available dynamic line models.

        Returns
        -------
        list[str]
            A list of section names from the line configuration.
        """
        return self._line.sections()

    def get_load_models(self) -> list[str]:
        """
        Gets a list of available dynamic load models.

        Returns
        -------
        list[str]
            A list of section names from the load configuration.
        """
        return self._load.sections()

    def get_transformer_models(self) -> list[str]:
        """
        Gets a list of available dynamic transformer models.

        Returns
        -------
        list[str]
            A list of section names from the transformer configuration.
        """
        return self._transformer.sections()

    def get_control_mode(self, section: str, control_option: int) -> list[str]:
        """
        Gets the control mode parameters for a given section and control option index.

        Parameters
        ----------
        section: str
            The name of the section in the 'ControlModes' configuration.
        control_option: int
            The 1-based index of the desired control mode within the section's list.

        Returns
        -------
        list[str]
            A list of control mode parameters. Returns an empty list if the section
            or the specified control option is not found.
        """
        if not self._control_modes.has_option("ControlModes", section):
            return []

        control_modes = self._control_modes.get("ControlModes", section).split(",")
        if len(control_modes) < control_option:
            return []

        control_mode = control_modes[control_option - 1]
        return self._get_control_mode_parameters(control_mode)

    def is_valid_control_mode(
        self, generator: Gen_params, generator_control_mode: str, generator_parameters: dict
    ) -> bool:
        """
        Checks if the provided generator control mode and its parameters are valid.

        This method iterates through valid control modes for the given generator type
        and control mode, comparing the provided parameters against predefined valid sets.

        Parameters
        ----------
        generator: Gen_params
            The generator parameters.
        generator_control_mode: str
            The name of the generator's control mode to validate.
        generator_parameters: dict
            A dictionary of parameters associated with the generator's control mode.

        Returns
        -------
        bool
            True if a valid control mode and its parameters are found, False otherwise.
        """
        valid_control_modes = self._get_control_modes_by_generator(
            generator, generator_control_mode
        )
        for control_mode in valid_control_modes:
            valid_parameters = self._get_control_mode_parameters(control_mode)
            if _is_valid_control_mode_parameters(generator_parameters, valid_parameters):
                return True
        return False


def _get_instance() -> Translator:
    """
    Creates and returns a singleton instance of the Translator class.

    This function initializes all necessary ConfigParser objects and loads the
    respective dictionary files.

    Returns
    -------
    Translator
        A fully initialized Translator instance.
    """
    bus = configparser.ConfigParser(inline_comment_prefixes=("#",))
    bus.optionxform = str
    synchronous_machine = configparser.ConfigParser(inline_comment_prefixes=("#",))
    synchronous_machine.optionxform = str
    power_park = configparser.ConfigParser(inline_comment_prefixes=("#",))
    power_park.optionxform = str
    storage = configparser.ConfigParser(inline_comment_prefixes=("#",))
    storage.optionxform = str
    line = configparser.ConfigParser(inline_comment_prefixes=("#",))
    line.optionxform = str
    load = configparser.ConfigParser(inline_comment_prefixes=("#",))
    load.optionxform = str
    transformer = configparser.ConfigParser(inline_comment_prefixes=("#",))
    transformer.optionxform = str
    control_modes = configparser.ConfigParser(inline_comment_prefixes=("#",))
    control_modes.optionxform = str

    _load_dictionary("Bus.ini", bus)
    _load_dictionary("Synch_Gen.ini", synchronous_machine)
    _load_dictionary("Power_Park.ini", power_park)
    _load_dictionary("Storage.ini", storage)
    _load_dictionary("Line.ini", line)
    _load_dictionary("Load.ini", load)
    _load_dictionary("Transformer.ini", transformer)
    _load_dictionary("Control_Modes.ini", control_modes)

    return Translator(
        bus, synchronous_machine, power_park, storage, line, load, transformer, control_modes
    )


# Global instance of the Translator, loaded once when the module is imported
dynawo_translator = _get_instance()
