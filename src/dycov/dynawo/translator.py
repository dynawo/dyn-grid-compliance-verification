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
    dictionary = Path(__file__).resolve().parent / "dictionary"
    if os.name == "nt":
        config_dir = Path.home() / "AppData/Local/dycov/user_models/dictionary"
    else:
        config_dir = Path.home() / ".config/dycov/user_models/dictionary"

    # Load the tool dictionary
    variables.read(dictionary / filename)

    # Load the user dictionary
    if (config_dir / filename).exists():
        variables.read(config_dir / filename)


def _is_valid_control_mode_parameters(generator_parameters: dict, valid_parameters: dict):
    for parameter_name in valid_parameters.keys():
        if (
            parameter_name not in generator_parameters
            or generator_parameters[parameter_name].lower()
            != valid_parameters[parameter_name].lower()
        ):
            return False

    return True


def get_generator_family_level(generator: Gen_params) -> tuple[str, str]:
    """ "Get the family and level of a generator.

    Parameters
    ----------
    generator: Gen_params
        Generator parameters

    Returns
    -------
    str
        Generator family
    str
        generator level
    """

    for key, value in FAMILY_LEVEL_MAP.items():
        if key in generator.lib:
            family = value["family"]
            for type_key, level in value["types"].items():
                if type_key in generator.lib:
                    return family, level
            return family, ""
    return "", ""


@dataclass(frozen=True)
class Translator:
    """Immutable translator class"""

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
    ) -> list:
        """Get a list of valid control modes by generator and control mode name.

        Returns
        -------
        list
            Valid control modes by generator and control mode name
        """
        family, level = get_generator_family_level(generator)
        option = f"{generator_control_mode}_{family}_{level}"
        if self._control_modes.has_option("ControlModes", option):
            return self._control_modes.get("ControlModes", option).split(",")
        else:
            return list()

    def _get_control_mode_parameters(self, control_mode: str) -> dict:
        parameters = self._control_modes.options(control_mode)
        valid_parameters = {}
        for parameter in parameters:
            valid_parameters[parameter] = self._control_modes.get(control_mode, parameter)

        return valid_parameters

    def get_dynawo_variable(self, lib: str, name: str) -> tuple[int, Optional[str]]:
        """Get the Dynawo variable name for a tool variable name.

        Parameters
        ----------
        lib: str
            Dynawo dinamic model name
        name: str
            Variable name

        Returns
        -------
        int
            Sign of the variable
        str
            Dynawo variable name
        """
        sign = 1
        translated_name = None
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

        if translated_name and translated_name.startswith("-"):
            sign = -1
            translated_name = translated_name[1:]

        return sign, translated_name

    def get_curve_variable(self, id: str, lib: str, name: str) -> Optional[str]:
        """Get the Dynawo curve name for a equipment.

        Parameters
        ----------
        id: str
            Equipment Id
        lib: str
            Dynawo dinamic model name
        name: str
            Variable name

        Returns
        -------
        str
            Dynawo curve name
        """
        _, suffix = self.get_dynawo_variable(lib, name)
        if not suffix:
            return None

        # The configuration files store variables for the PAR file, in the case of the curves,
        # the id of the element must be concatenated with the variable by means of the char '_'.
        return id + "_" + suffix

    def get_bus_models(self) -> list:
        """Get a list of available dynamic bus models.

        Returns
        -------
        list
            Dynamic bus models
        """
        return self._bus.sections()

    def get_synchronous_machine_models(self) -> list:
        """Get a list of available dynamic synchronous machine models.

        Returns
        -------
        list
            Dynamic synchronous machine models
        """
        return self._synchronous_machine.sections()

    def get_power_park_models(self) -> list:
        """Get a list of available dynamic power park models.

        Returns
        -------
        list
            Dynamic power park models
        """
        return self._power_park.sections()

    def get_storage_models(self) -> list:
        """Get a list of available dynamic storage models.

        Returns
        -------
        list
            Dynamic storage models
        """
        return self._storage.sections()

    def get_line_models(self) -> list:
        """Get a list of available dynamic line models.

        Returns
        -------
        list
            Dynamic line models
        """
        return self._line.sections()

    def get_load_models(self) -> list:
        """Get a list of available dynamic load models.

        Returns
        -------
        list
            Dynamic load models
        """
        return self._load.sections()

    def get_transformer_models(self) -> list:
        """Get a list of available dynamic transformer models.

        Returns
        -------
        list
            Dynamic transformer models
        """
        return self._transformer.sections()

    def get_control_mode(self, section: str, control_option: int) -> list:
        """Get the control mode parameters by index.

        Returns
        -------
        list
            Control mode parameters
        """
        if not self._control_modes.has_option("ControlModes", section):
            return list()

        control_modes = self._control_modes.get("ControlModes", section).split(",")
        if len(control_modes) < control_option:
            return list()

        control_mode = control_modes[control_option - 1]
        return self._get_control_mode_parameters(control_mode)

    def is_valid_control_mode(
        self, generator: Gen_params, generator_control_mode: str, control_mode_parameters: dict
    ) -> str:
        """Check if the control mode is valid for the generator.

        Parameters
        ----------
        generator: Gen_params
            Generator parameters
        generator_control_mode: str
            Control mode name
        control_mode_parameters: dict
            Control mode parameters

        Returns
        -------
        str
            Valid control mode name or empty string if not valid
        """

        valid_control_modes = self._get_control_modes_by_generator(
            generator, generator_control_mode
        )
        for control_mode in valid_control_modes:
            valid_parameters = self._get_control_mode_parameters(control_mode)
            if _is_valid_control_mode_parameters(control_mode_parameters, valid_parameters):
                return control_mode

        return ""

    def is_reactive_control_mode(self, generator: Gen_params, control_mode_name: str) -> bool:
        """Check if the control mode is a reactive control mode.

        Parameters
        ----------
        generator: Gen_params
            Generator parameters
        control_mode_name: str
            Control mode name

        Returns
        -------
        bool
            True if the control mode is a reactive control mode, False otherwise
        """
        valid_control_modes = self._get_control_modes_by_generator(generator, "QSetpoint")
        return True if control_mode_name in valid_control_modes else False


def _get_instance() -> Translator:
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


dynawo_translator = _get_instance()
