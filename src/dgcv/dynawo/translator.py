import configparser
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union

# TODO: remove generator types ("WTG", "WT", "Photovoltaics", etc. ==> we'll need
#       entries in the master dictionary).
#       The same goes for generator families ("IEC", "Wecc").
#


def get_generator_family_level(generator):
    family = ""
    level = ""
    if "Wecc" in generator.lib:
        family = "WECC"
        if "WTG" in generator.lib:
            level = "Plant"
        elif "WT" in generator.lib:
            level = "Turbine"
        elif "Photovoltaics" in generator.lib:
            level = "Plant"
        elif "BESS" in generator.lib:
            level = "Plant"
            if "NoPlantControl" in generator.lib:
                level = "Turbine"
    elif "IEC" in generator.lib:
        family = "IEC"
        if "IECWPP" in generator.lib:
            level = "Plant"
        elif "IECWT" in generator.lib:
            level = "Turbine"
    return family, level


def _load_dictionary(filename: str, variables: configparser.ConfigParser):
    dictionary = Path(__file__).resolve().parent / "dictionary"
    if os.name == "nt":
        config_dir = Path.home() / "AppData/Local/dgcv/user_models/dictionary"
    else:
        config_dir = Path.home() / ".config/dgcv/user_models/dictionary"

    # Load the tool dictionary
    variables.read(dictionary / filename)

    # Load the user dictionary
    if (config_dir / filename).exists():
        variables.read(config_dir / filename)


def _is_valid_control_mode_paremeters(generator_parameters: dict, valid_parameters: dict):
    for parameter_name in valid_parameters.keys():
        if (
            parameter_name not in generator_parameters
            or generator_parameters[parameter_name] != valid_parameters[parameter_name]
        ):
            return False

    return True


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

    def _get_control_modes_by_generator(self, generator, generator_control_mode) -> list:
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

    def _get_control_mode_parameters(self, control_mode):
        parameters = self._control_modes.options(control_mode)
        valid_parameters = {}
        for parameter in parameters:
            valid_parameters[parameter] = self._control_modes.get(control_mode, parameter)

        return valid_parameters

    def get_dynawo_variable(self, lib: str, name: str) -> Union[str, None]:
        """Get the Dynawo variable name for a tool variable name.

        Parameters
        ----------
        lib: str
            Dynawo dinamic model name
        name: str
            Variable name

        Returns
        -------
        str
            Dynawo variable name
        """
        if self._bus.has_option(lib, name):
            return self._bus.get(lib, name)
        elif self._synchronous_machine.has_option(lib, name):
            return self._synchronous_machine.get(lib, name)
        elif self._power_park.has_option(lib, name):
            return self._power_park.get(lib, name)
        elif self._storage.has_option(lib, name):
            return self._storage.get(lib, name)
        elif self._line.has_option(lib, name):
            return self._line.get(lib, name)
        elif self._load.has_option(lib, name):
            return self._load.get(lib, name)
        elif self._transformer.has_option(lib, name):
            return self._transformer.get(lib, name)
        elif self._control_modes.has_option(lib, name):
            return self._control_modes.get(lib, name)

        return None

    def get_curve_variable(self, id: str, lib: str, name: str) -> Union[str, None]:
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
        suffix = self.get_dynawo_variable(lib, name)
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
        self, generator, generator_control_mode: str, generator_parameters: dict
    ) -> bool:

        valid_control_modes = self._get_control_modes_by_generator(
            generator, generator_control_mode
        )
        for control_mode in valid_control_modes:
            valid_parameters = self._get_control_mode_parameters(control_mode)
            if _is_valid_control_mode_paremeters(generator_parameters, valid_parameters):
                return True

        return False


def _get_instance() -> Translator:
    bus = configparser.ConfigParser()
    bus.optionxform = str
    synchronous_machine = configparser.ConfigParser()
    synchronous_machine.optionxform = str
    power_park = configparser.ConfigParser()
    power_park.optionxform = str
    storage = configparser.ConfigParser()
    storage.optionxform = str
    line = configparser.ConfigParser()
    line.optionxform = str
    load = configparser.ConfigParser()
    load.optionxform = str
    transformer = configparser.ConfigParser()
    transformer.optionxform = str
    control_modes = configparser.ConfigParser()
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
