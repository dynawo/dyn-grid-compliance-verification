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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dycov.logging import dycov_logging


@dataclass(frozen=True)
class Config:
    """Manages application configuration from various sources.

    Configuration is loaded with the following priority:
    1. User Performance Checking Sheet (PCS) description
    2. User configuration
    3. PCS description of the selected DTR revision
    4. PCS description shipped with the tool
    5. Default configuration

    The three PCS layers describe one PCS at a time, and load_pcs_config rebuilds them
    every time a PCS is prepared. The user configuration outlives them, because it also
    holds the runtime overrides and the file given on the command line.

    Attributes
    ----------
    _config_dir: Path
        The directory where configuration files are located.
    _default_config: configparser.ConfigParser
        Parser for the default configuration.
    _user_config: configparser.ConfigParser
        Parser for the user-specific configuration.
    _pcs_user_config: configparser.ConfigParser
        Parser for the PCS description written by the user.
    _pcs_dtr_config: configparser.ConfigParser
        Parser for the PCS description of the selected DTR revision.
    _pcs_default_config: configparser.ConfigParser
        Parser for the PCS description shipped with the tool.
    _pcs_user_files: list[str]
        Path of the user PCS description in preparation, used to locate an option in its
        source file when reporting errors.
    _pcs_dtr_files: list[str]
        Path of the DTR revision description in preparation, used to locate an option in
        its source file when reporting errors.
    _pcs_default_files: list[str]
        Path of the shipped PCS description in preparation, used to locate an option in
        its source file when reporting errors.
    """

    _config_dir: Path
    _default_config: configparser.ConfigParser
    _user_config: configparser.ConfigParser
    _pcs_user_config: configparser.ConfigParser
    _pcs_dtr_config: configparser.ConfigParser
    _pcs_default_config: configparser.ConfigParser
    _pcs_user_files: list[str] = field(default_factory=list)
    _pcs_dtr_files: list[str] = field(default_factory=list)
    _pcs_default_files: list[str] = field(default_factory=list)

    def _layers(self) -> tuple[configparser.ConfigParser, ...]:
        """Configuration parsers, from the highest precedence to the lowest."""
        return (
            self._pcs_user_config,
            self._user_config,
            self._pcs_dtr_config,
            self._pcs_default_config,
            self._default_config,
        )

    def _is_valid_value(self, value: str) -> bool:
        """Internal helper to validate if a string value is not None or empty.

        Parameters
        ----------
        value: str
            The string value to validate.

        Returns
        -------
        bool
            True if the validated string is not None or empty, otherwise False.
        """
        return value is not None and value != ""

    def _has_valid_option(self, parser: configparser.ConfigParser, section: str, key: str) -> bool:
        """Internal helper to check that a parser defines a key with a valid value."""
        return parser.has_option(section, key) and self._is_valid_value(parser.get(section, key))

    def _get_config_value(self, section: str, key: str) -> Optional[str]:
        """Gets a configuration value for a given key and section.

        The priority defined in the configuration is:
          1. User Performance Checking Sheet (PCS) description
          2. User config
          3. PCS description of the selected DTR revision
          4. PCS description shipped with the tool
          5. Default config

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        Optional[str]
            The string value if it exists, None otherwise.
        """
        for parser in self._layers():
            if self._has_valid_option(parser, section, key):
                return parser.get(section, key)

        return None

    def load_user_config(self, user_config_path: Path) -> None:
        """Load the user-specific configuration file.

        Parameters
        ----------
        user_config_path: Path
            Path to the user configuration file to read.
        """
        dycov_logging.get_logger("Cfg").info(
            "Loading user configuration from: %s", user_config_path
        )
        try:
            self._user_config.read(user_config_path, encoding="utf-8")
            dycov_logging.get_logger("Cfg").info("Successfully loaded user configuration.")
        except Exception as e:
            dycov_logging.get_logger("Cfg").error(
                "Error loading user configuration from %s: %s", user_config_path, e
            )
            raise

    def load_pcs_config(
        self,
        pcs_path: Optional[Path],
        user_pcs_path: Optional[Path] = None,
        dtr_pcs_path: Optional[Path] = None,
    ) -> None:
        """Rebuild the Performance Checking Sheet (PCS) description layers from the files
        of a single PCS, discarding whatever a previously prepared PCS had left.

        Each file goes into the layer of its origin, so which one wins is a matter of
        precedence and not of the order in which they are read.

        Every layer then resolves the inheritance mechanism using alias files: any file
        named "*aliases*" located two levels above its PCS file. If a section contains an
        "inherit" key, the key-value pairs of the corresponding section in the alias files
        are loaded into it. This allows for shared, default configurations. Values already
        present in the section will NOT be overwritten.

        Parameters
        ----------
        pcs_path: Optional[Path]
            Path to the PCS description shipped with the tool.
        user_pcs_path: Optional[Path]
            Path to the PCS description written by the user.
        dtr_pcs_path: Optional[Path]
            Path to the PCS description of the selected DTR revision.
        """
        self._load_pcs_layer(self._pcs_user_config, self._pcs_user_files, user_pcs_path)
        self._load_pcs_layer(self._pcs_dtr_config, self._pcs_dtr_files, dtr_pcs_path)
        self._load_pcs_layer(self._pcs_default_config, self._pcs_default_files, pcs_path)

    def _load_pcs_layer(
        self,
        parser: configparser.ConfigParser,
        layer_files: list[str],
        path: Optional[Path],
    ) -> None:
        """Internal helper to replace the contents of one PCS layer with the given file."""
        parser.clear()
        layer_files.clear()
        if path is None:
            return

        dycov_logging.get_logger("Cfg").info("Loading PCS configuration from: %s", path)
        try:
            parser.read(path, encoding="utf-8")
            layer_files.append(str(path))
            _resolve_inherited_sections(parser, _alias_files(path))
            dycov_logging.get_logger("Cfg").info("Successfully loaded PCS configuration.")
        except Exception as e:
            dycov_logging.get_logger("Cfg").error(
                "Error loading PCS configuration from %s: %s", path, e
            )
            raise

    def get_config_dir(self) -> Path:
        """Returns the configuration directory path.

        Returns
        -------
        Path
            The defined configuration directory path.
        """
        return self._config_dir

    def has_option(self, section: str, key: str) -> bool:
        """Check if config contains the specified key within any configuration source.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        bool
            True if the key exists in any of the configuration sources, False otherwise.
        """
        return any(parser.has_option(section, key) for parser in self._layers())

    def describe_option(self, section: str, key: str) -> str:
        """Locates an option in the configuration files, to point the user to its origin.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        str
            Human-readable location of the option, naming the source file and line
            number when they can be determined.
        """
        for path in self._option_files():
            line = _find_option_line(path, section, key)
            if line is not None:
                return f"'{key}' in section [{section}] of '{path}', line {line}"

        return f"'{key}' in section [{section}]"

    def _option_files(self) -> list[Path]:
        """Configuration files that may define an option, in precedence order."""
        return [
            *(Path(pcs_file) for pcs_file in self._pcs_user_files),
            _user_config_path(self._config_dir),
            *(Path(pcs_file) for pcs_file in self._pcs_dtr_files),
            *(Path(pcs_file) for pcs_file in self._pcs_default_files),
            _default_config_path(),
        ]

    def set_value(self, section: str, key: str, value: str) -> None:
        """Sets (or overrides) a configuration value at runtime using the same
        precedence policy as get_value().

        Concretely:
        - If (section, key) exists with a valid (non-empty) value (checked with
        _is_valid_value), the override is applied in that same source.
        - The DTR revision layer describes a published revision, so it is never written:
        an option whose effective value comes from it is overridden in the user config,
        which outranks it.
        - If it does not exist in any source with a valid value, the key is created in
        the user config.

        This method updates the in-memory configuration and creates the section if it
        does not exist. It does not persist values to disk.

        Parameters
        ----------
        section : str
            Section header.
        key : str
            Key within the section.
        value : str
            New value to set.

        Returns
        -------
        None
            The value is set in-memory. No value is returned.
        """
        target_parser = self._override_target(section, key)
        if not target_parser.has_section(section):
            target_parser.add_section(section)

        target_parser.set(section, key, value)

    def _override_target(self, section: str, key: str) -> configparser.ConfigParser:
        """Internal helper to choose the parser a runtime override must be written into."""
        if self._has_valid_option(self._pcs_user_config, section, key):
            return self._pcs_user_config

        if self._has_valid_option(self._user_config, section, key):
            return self._user_config

        if self._has_valid_option(self._pcs_dtr_config, section, key):
            return self._user_config

        if self._has_valid_option(self._pcs_default_config, section, key):
            return self._pcs_default_config

        if self._has_valid_option(self._default_config, section, key):
            return self._default_config

        return self._user_config

    def get_value(self, section: str, key: str, default: str = None) -> str:
        """Gets a configuration value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: str
            Default value to return if the key is not found.

        Returns
        -------
        str
            The string value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        return value

    def get_int(self, section: str, key: str, default: int) -> int:
        """Gets an integer value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: int
            Default value to return if the key is not found.

        Returns
        -------
        int
            The integer value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            dycov_logging.get_logger("Cfg").error(
                f"Could not convert value '{value}' to integer for "
                f"section '{section}', key '{key}'. Using default: {default}"
            )
            return default

    def get_float(self, section: str, key: str, default: float) -> float:
        """Gets a float value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: float
            Default value to return if the key is not found.

        Returns
        -------
        float
            The float value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            dycov_logging.get_logger("Cfg").error(
                f"Could not convert value '{value}' to float for "
                f"section '{section}', key '{key}'. Using default: {default}",
            )
            return default

    def get_boolean(self, section: str, key: str, default: bool = False) -> bool:
        """Gets a boolean value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: bool
            Default value to return if the key is not found (default is False).

        Returns
        -------
        bool
            The boolean value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        return value.lower() == "true"

    def get_list(self, section: str, key: str) -> list:
        """Gets a list of string values for a given key and section.
        Values are assumed to be comma-separated in the configuration file.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        list
            A list of strings if the key exists, an empty list otherwise.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return []
        return value.split(",")

    def get_options(self, section: str) -> list:
        """Returns a list of keys of a section, gathered from every layer that defines it.

        A layer describes a section by the keys it changes, so the keys of a section are
        the union of the layers and not the contents of the first one that defines it.
        The value behind each key still follows the precedence of get_value().

        Parameters
        ----------
        section: str
            Section header.

        Returns
        -------
        list
            A list of keys in the specified section, or an empty list otherwise.
        """
        options = dict.fromkeys(
            option
            for parser in self._layers()
            if parser.has_section(section)
            for option in parser.options(section)
        )
        return list(options)


def _new_parser() -> configparser.ConfigParser:
    """A parser that reads DyCoV configuration files, preserving the case of the keys."""
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.optionxform = str
    return parser


def _alias_files(path: Path) -> list[str]:
    """Alias files that the given PCS file may inherit from, two levels above it."""
    aliases_path = Path(path).resolve().parent.parent
    return [str(alias) for alias in aliases_path.rglob("*aliases*") if alias.is_file()]


def _resolve_inherited_sections(parser: configparser.ConfigParser, alias_files: list[str]) -> None:
    """Fills every section declaring an "inherit" key with the keys of its alias section."""
    aliases_config = configparser.ConfigParser()
    aliases_config.optionxform = str
    aliases_config.read(alias_files, encoding="utf-8")

    for section_to_modify in list(parser.sections()):
        if not parser.has_option(section_to_modify, "inherit"):
            continue

        alias_section_name = parser.get(section_to_modify, "inherit")
        if not aliases_config.has_section(alias_section_name):
            dycov_logging.get_logger("Cfg").warning(
                f"  [WARNING] The alias section '[{alias_section_name}]' was not found"
                " in the alias files."
            )
            continue

        for key_to_inherit, value_to_inherit in aliases_config.items(alias_section_name):
            if not parser.has_option(section_to_modify, key_to_inherit):
                parser.set(section_to_modify, key_to_inherit, value_to_inherit)
        parser.remove_option(section_to_modify, "inherit")


def _user_config_path(config_dir: Path) -> Path:
    """Path of the user configuration file."""
    return config_dir / "config.ini"


def _default_config_path() -> Path:
    """Path of the default configuration file shipped with the package."""
    return Path(__file__).resolve().parent / "defaultConfig.ini"


def _find_option_line(path: Path, section: str, key: str) -> Optional[int]:
    """Line number at which an option is defined in an INI file, None if absent."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    option_pattern = re.compile(rf"^\s*{re.escape(key)}\s*[:=]")
    current_section = None
    for number, line in enumerate(lines, start=1):
        header = re.match(r"^\s*\[(?P<name>[^]]+)\]", line)
        if header:
            current_section = header.group("name").strip()
        elif current_section == section and option_pattern.match(line):
            return number

    return None


def _get_instance() -> Config:
    """Internal function to create and return a singleton Config instance.

    This function sets up the configuration directories and loads default
    and user-specific configuration files.

    Returns
    -------
    Config
        A Config object initialized with default, user, and PCS config parsers.
    """
    logger = dycov_logging.get_logger("Cfg")
    logger.info("Initializing Config instance.")
    config_dir = Path.home() / ".config/dycov"
    logger.debug(f"Config directory set to: {config_dir}")

    default_config = _new_parser()
    user_config = _new_parser()
    pcs_user_config = _new_parser()
    pcs_dtr_config = _new_parser()
    pcs_default_config = _new_parser()

    # Load default configuration from the package
    default_config_path = _default_config_path()
    logger.info(f"Loading default configuration from: {default_config_path}")
    try:
        if not default_config_path.exists():
            logger.warning(f"Default configuration file not found at: {default_config_path}")
        default_config.read(default_config_path)
        logger.info("Successfully loaded default configuration.")
    except Exception as e:
        logger.error(f"Error loading default configuration from {default_config_path}: {e}")
        raise

    # Load user configuration
    user_config_file = _user_config_path(config_dir)
    logger.info(f"Loading user configuration from: {user_config_file}")
    try:
        if not user_config_file.exists():
            logger.debug(
                f"User configuration file not found at: {user_config_file} "
                "(This is often expected)",
                user_config_file,
            )
        user_config.read(user_config_file)
        logger.info("Successfully loaded user configuration.")
    except Exception:
        logger.warning(f"Could not load user configuration from {user_config_file}", exc_info=True)

    return Config(
        config_dir,
        default_config,
        user_config,
        pcs_user_config,
        pcs_dtr_config,
        pcs_default_config,
    )


# Global instance of the Config class
config = _get_instance()
