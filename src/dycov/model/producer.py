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
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE,
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION,
    MODEL_VALIDATION_BESS,
    MODEL_VALIDATION_PPM,
)
from dycov.files import model_parameters
from dycov.logging.logging import dycov_logging
from dycov.sanity_checks import file_checks, parameter_checks


def _check_parameters_definition(producer_config, section, needs_consumption):
    if not producer_config.has_option(section, "u_nom"):
        raise ValueError("The parameter file must specify the u_nom")
    if not producer_config.has_option(section, "q_min"):
        raise ValueError("The parameter file must specify the q_min")
    if not producer_config.has_option(section, "q_max"):
        raise ValueError("The parameter file must specify the q_max")
    if not producer_config.has_option(section, "p_max_injection"):
        raise ValueError("The parameter file must specify the p_max_injection")
    if needs_consumption and not producer_config.has_option(section, "p_max_consumption"):
        raise ValueError("The parameter file must specify the p_max_consumption")
    if not producer_config.has_option(section, "topology"):
        raise ValueError("The parameter file must specify the topology")


class Producer:
    """Representation of the Producer model.

    Args
    ----
    producer_model_path: Path
        Directory to the Dynamic Model, if it is given
    producer_curves_path: Path
        Directory to the User Curves, if it is given
    verification_type: int
        0 if it is an electrical performance verification
        1 if it is a model validation
    """

    def __init__(
        self,
        producer_model_path: Path,
        producer_curves_path: Path,
        reference_curves_path: Path,
        verification_type: int,
    ):
        self._s_nref = config.get_float("GridCode", "s_nref", 100.0)
        self._producer_model_path = producer_model_path
        self._producer_curves_path = producer_curves_path
        self._reference_curves_path = reference_curves_path
        self._zone = 0

        self._is_dynawo_model = self._producer_model_path is not None
        self._is_user_curves = self._producer_curves_path is not None
        self._has_reference_curves_path = self._reference_curves_path is not None

        self._filename = None
        self._sim_type = None

        if verification_type == ELECTRIC_PERFORMANCE:
            self.__set_electric_performance_type()
        elif verification_type == MODEL_VALIDATION:
            self.__set_model_validation_type()

    def __set_electric_performance_type(self):
        #  Expected input example:
        #  Dynawo
        #  ├─── Producer.dyd
        #  ├─── Producer.par
        #  └─── Producer.ini

        # By default the tool will search for the curve using a compound name:
        #               - DYDfilename.PCS.benchmark.OC
        # As a second option, it will search for the compound name:
        #               - PCS.benchmark.OC
        # This logic is only used if the user does not inform the file name specifically.
        #  Example of expected curve input:
        # ProducerCurves
        # ├── Producer
        # │   ├── CurvesFiles.ini
        # │   ├── PCS_RTE-I2.USetPointStep.AReactance.csv
        # │   ├── PCS_RTE-I2.USetPointStep.AReactance.dict
        #  ...
        # │   ├── PCS_RTE-I10.Islanding.DeltaP10DeltaQ4.csv
        # │   └── PCS_RTE-I10.Islanding.DeltaP10DeltaQ4.dict
        # └── Producer.ini

        sm_models = 0
        ppm_models = 0
        bess_models = 0
        if self.is_dynawo_model():
            file_checks.check_performance_model(self._producer_model_path)
            (
                generators,
                _,
                _,
                _,
                _,
                _,
            ) = model_parameters.get_producer_values(
                self.get_producer_dyd(),
                self.get_producer_par(),
                self._s_nref,
            )
            sm_models, ppm_models, bess_models = file_checks.check_generators(generators)
        else:
            file_checks.check_performance_curves(self._producer_curves_path)
            default_section = "DEFAULT"
            producer_config = self.__read_producer_ini()
            generator_type = producer_config.get(default_section, "generator_type")
            if "SM" == generator_type:
                sm_models = 1
            elif "PPM" == generator_type:
                ppm_models = 1
            elif "BESS" == generator_type:
                bess_models = 1

        if sm_models > 0:
            self._sim_type = ELECTRIC_PERFORMANCE_SM
        elif ppm_models > 0:
            self._sim_type = ELECTRIC_PERFORMANCE_PPM
        elif bess_models > 0:
            self._sim_type = ELECTRIC_PERFORMANCE_BESS
        else:
            raise ValueError(
                "Electric performance verification does not support the modeled generator type"
            )

    def __set_model_validation_type(self):
        #  Expected input example:
        #  Dynawo
        #  ├─── Zone3
        #  │     ├─── Producer.dyd
        #  │     ├─── Producer.par
        #  │     └─── Producer.ini
        #  └─── Zone1
        #        ├─── Producer_G1.dyd
        #        ├─── Producer_G1.par
        #        ├─── Producer_G1.ini
        #        ├─── Producer_G2.dyd
        #        ├─── Producer_G2.par
        #        └─── Producer_G2.ini

        # By default the tool will search for the curve using a compound name:
        #               - DYDfilename.PCS.benchmark.OC
        # As a second option, it will search for the compound name:
        #               - PCS.benchmark.OC
        # This logic is only used if the user does not inform the file name specifically.
        #  Example of expected curve input:
        # ReferenceCurves
        # ├── Producer
        # │   ├── CurvesFiles.ini
        # │   ├── PCS_RTE-I16z3.GridVoltageDip.Qzero.csv
        # │   ├── PCS_RTE-I16z3.GridVoltageDip.Qzero.dict
        #  ...
        # │   ├── PCS_RTE-I16z3.USetPointStep.BReactance.csv
        # │   ├── PCS_RTE-I16z3.USetPointStep.BReactance.dict
        # ├── Producer_G1
        # │   ├── CurvesFiles.ini
        # │   ├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.csv
        # │   ├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.dict
        #  ...
        # │   ├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.csv
        # │   ├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.dict
        # └── Producer_G2
        #     ├── CurvesFiles.ini
        #     ├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.csv
        #     ├── PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms.dict
        #  ...
        #     ├── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.csv
        #     └── PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800.dict

        sm_models = 0
        ppm_models = 0
        bess_models = 0
        if self.is_dynawo_model():
            sm_models, ppm_models, bess_models = self.__set_dynawo_model_validation_type()
        else:
            sm_models, ppm_models, bess_models = self.__set_curves_model_validation_type()
            file_checks.check_validation_curves(
                self._producer_curves_path, self._reference_curves_path
            )

        if sm_models > 0:
            raise ValueError("Synchronous machine models are not allowed for model validation")
        elif ppm_models > 0:
            self._sim_type = MODEL_VALIDATION_PPM
        elif bess_models > 0:
            self._sim_type = MODEL_VALIDATION_BESS
        else:
            raise ValueError("Model validation does not support the modeled generator type")

    def __set_dynawo_model_validation_type(self):
        self._zone = 1
        generators_z1 = list()
        for self._filename in self.get_filenames(self._zone):
            (
                generators,
                _,
                _,
                _,
                _,
                _,
            ) = model_parameters.get_producer_values(
                self.get_producer_dyd(),
                self.get_producer_par(),
                self._s_nref,
            )
            generators_z1 += generators
        self._zone = 3
        generators_z3 = list()
        for self._filename in self.get_filenames(self._zone):
            (
                generators,
                _,
                _,
                _,
                _,
                _,
            ) = model_parameters.get_producer_values(
                self.get_producer_dyd(),
                self.get_producer_par(),
                self._s_nref,
            )
            generators_z3 += generators
        sm_models, ppm_models, bess_models = file_checks.check_generators(
            generators_z1, generators_z3
        )
        self._zone = 0

        file_checks.check_validation_model(
            self._producer_model_path,
            self._reference_curves_path,
            len(generators_z3),
            self.get_filenames(zone=3),
            self.get_filenames(zone=1),
        )
        return sm_models, ppm_models, bess_models

    def __set_curves_model_validation_type(self):
        default_section = "DEFAULT"
        self._zone = 1
        producer_config = self.__read_producer_ini()
        generator_type_z1 = producer_config.get(default_section, "generator_type")
        self._zone = 3
        producer_config = self.__read_producer_ini()
        generator_type_z3 = producer_config.get(default_section, "generator_type")
        sm_models = 0
        ppm_models = 0
        bess_models = 0
        if "SM" == generator_type_z1:
            sm_models += 1
        elif "PPM" == generator_type_z1:
            ppm_models += 1
        elif "BESS" == generator_type_z1:
            bess_models += 1
        if "SM" == generator_type_z3:
            sm_models += 1
        elif "PPM" == generator_type_z3:
            ppm_models += 1
        elif "BESS" == generator_type_z3:
            bess_models += 1

        return sm_models, ppm_models, bess_models

    def __read_producer_ini(self):
        if self._filename is None:
            pattern_ini = re.compile(r".*.Producer.[iI][nN][iI]")
        else:
            pattern_ini = re.compile(rf".*.{self._filename}.[iI][nN][iI]")
        producer_ini = self.__get_file_by_pattern(pattern_ini)

        default_section = "DEFAULT"
        with open(producer_ini, "r") as f:
            producer_ini_txt = "[" + default_section + "]\n" + f.read()

        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read_string(producer_ini_txt)
        return producer_config

    def __init_parameters(self):
        default_section = "DEFAULT"
        producer_config = self.__read_producer_ini()
        _check_parameters_definition(
            producer_config, default_section, self._sim_type == MODEL_VALIDATION_BESS
        )

        self.p_max_injection_pu = (
            float(producer_config.get(default_section, "p_max_injection")) / self._s_nref
        )
        self.p_max_consumption_pu = 0.0
        if producer_config.has_option(default_section, "p_max_consumption"):
            self.p_max_consumption_pu = (
                float(producer_config.get(default_section, "p_max_consumption")) / self._s_nref
            )
        self.q_max_pu = float(producer_config.get(default_section, "q_max")) / self._s_nref
        self.q_min_pu = float(producer_config.get(default_section, "q_min")) / self._s_nref
        self.u_nom = float(producer_config.get(default_section, "u_nom"))
        self.topology = producer_config.get(default_section, "topology")

    def __init_model(self) -> None:
        """Initializes the Producer-dependent model."""
        # Read producer network
        (
            self.generators,
            self.stepup_xfmrs,
            self.aux_load,
            self.auxload_xfmr,
            self.ppm_xfmr,
            self.intline,
        ) = model_parameters.get_producer_values(
            self.get_producer_dyd(),
            self.get_producer_par(),
            self._s_nref,
        )
        self._connected_to_pdr = model_parameters.get_connected_to_pdr(self.get_producer_dyd())
        self.s_nom = sum(gen.SNom for gen in self.generators)

        # Check sanity of the producer network
        file_checks.check_topology(
            self.topology,
            self.generators,
            self.stepup_xfmrs,
            self.aux_load,
            self.auxload_xfmr,
            self.ppm_xfmr,
            self.intline,
        )
        file_checks.check_trafos(self.stepup_xfmrs)
        file_checks.check_auxiliary_load(self.aux_load)
        file_checks.check_trafo(self.auxload_xfmr)
        file_checks.check_trafo(self.ppm_xfmr)
        file_checks.check_internal_line(self.intline)
        file_checks.check_generators(self.generators)

    def __get_file_by_pattern(self, pattern) -> Path:
        if self._producer_model_path is not None:
            producer_path = self._producer_model_path
        elif self._producer_curves_path is not None:
            producer_path = self._producer_curves_path
        else:
            dycov_logging.get_logger("Producer").error("No producer model has been defined")
            return None

        if self._zone == 0:
            path = producer_path
        elif self._zone == 1:
            path = producer_path / "Zone1"
        elif self._zone == 3:
            path = producer_path / "Zone3"
        for file in path.resolve().iterdir():
            if pattern.match(str(file)):
                return path.resolve() / file
        dycov_logging.get_logger("Producer").warning(f"No found pattern: {pattern} in {path}")
        return None

    def get_filenames(self, zone: int = 0) -> list[str]:
        """Get the filenames of the producer model.

        Parameters
        ----------
        zone: int
            Zone to test, only applies to model validation

        Returns
        -------
        list[str]
            List of filenames.
        """
        if self._producer_model_path is not None:
            if zone == 0:
                path = self._producer_model_path
            elif zone == 1:
                path = self._producer_model_path / "Zone1"
            elif zone == 3:
                path = self._producer_model_path / "Zone3"

            pattern = re.compile(r".*.[dD][yY][dD]")
            return sorted(
                [file.stem for file in path.resolve().iterdir() if pattern.match(str(file))]
            )

        elif self._producer_curves_path is not None:
            path = self._producer_curves_path

            exclude_pattern = re.compile(r".*.Zone[13]")
            return sorted(
                [
                    p.stem
                    for p in path.resolve().iterdir()
                    if not exclude_pattern.match(str(p)) and p.is_dir()
                ]
            )

        dycov_logging.get_logger("Producer").error("No producer model has been defined")
        return list()

    def set_consumption(self, consumption: float) -> None:
        """The value of p_max_pu is defined depending on the
        operating mode: injection or consumption.

        Parameters
        ----------
        consumption: float
            If it is True use the Pmax Consumption
            If it is False use the Pmax Injection
        """
        if consumption:
            # The maximum active power consumption value must be
            # sign-flipped to adhere to the tool's adopted sign convention.
            self.p_max_pu = -self.p_max_consumption_pu
        else:
            self.p_max_pu = self.p_max_injection_pu

    def get_element(self, id: str) -> tuple[str, str]:
        """Get element information by id

        Parameters
        ----------
        id: str
            Element Id

        Returns
        -------
        str
            Element id
        str
            Dynamic model library
        """
        for gen in self._generators:
            if id == gen.id:
                return gen.id, gen.lib

        for xmfr in self._stepup_xfmrs:
            if id == xmfr.id:
                return xmfr.id, xmfr.lib

        if self._ppm_xfmr and id == self._ppm_xfmr.id:
            return self._ppm_xfmr.id, self._ppm_xfmr.lib

        return None, None

    def get_producer_path(self) -> Path:
        """Get the Producer directory.

        Returns
        -------
        Path
            Producer directory
        """
        if self.is_dynawo_model():
            return self._producer_model_path
        else:
            return self._producer_curves_path

    def get_reference_path(self) -> Path:
        """Get the Reference directory.

        Returns
        -------
        Path
            Reference directory
        """
        return self._reference_curves_path

    def set_zone(self, zone: int, filename: str) -> None:
        """Set the zone to test.

        Parameters
        ----------
        zone: int
            Zone to test, only applies to model validation
        filename: str
            Name of the file to validate
        """
        dycov_logging.get_logger("Producer").debug(
            f"Setting zone to {zone} and filename to {filename}"
        )
        self._zone = zone
        self._filename = filename
        self.__init_parameters()
        parameter_checks.check_producer_params(
            self.p_max_injection_pu, self.p_max_consumption_pu, self.u_nom
        )

        if self.is_dynawo_model():
            file_checks.check_well_formed_xml(self.get_producer_dyd())
            file_checks.check_well_formed_xml(self.get_producer_par())
            if self.get_sim_type() > MODEL_VALIDATION:
                file_checks.check_curves_files(
                    self._producer_model_path,
                    self._reference_curves_path / filename,
                    self.get_sim_type_str(),
                )
            self.__init_model()

    def get_zone(self) -> int:
        """Get the zone to test.

        Returns
        ----------
        int
            Zone to test, only applies to model validation
        """
        return self._zone

    def is_dynawo_model(self) -> bool:
        """Check if the producer has a dynamic model.

        Returns
        -------
        bool
            True if has a dynamic model, False otherwise
        """
        return self._is_dynawo_model

    def is_user_curves(self) -> bool:
        """Check if the producer has a curves directory.

        Returns
        -------
        bool
            True if has a curves directory, False otherwise
        """
        return self._is_user_curves

    def has_reference_curves_path(self) -> bool:
        """Check if there are reference curves directory.

        Returns
        -------
        bool
            True if has a reference curves directory, False otherwise
        """
        return self._has_reference_curves_path

    def get_sim_type_str(self) -> str:
        """Gets a string according to the type of validation executed.

        Returns
        -------
        str
            'performance/SM' if it is an electrical performance for a Synchronous Machine Model
            'performance/PPM' if it is an electrical performance for a Power Park Module Model
            'performance/BESS' if it is an electrical performance for a Storage Model
            'model/PPM' if it is a model validation for a Power Park Module Model
            'model/BESS' if it is a model validation for a Storage Model
        """
        if self._sim_type == ELECTRIC_PERFORMANCE_SM:
            return "performance/SM"

        elif self._sim_type == ELECTRIC_PERFORMANCE_PPM:
            return "performance/PPM"

        elif self._sim_type == ELECTRIC_PERFORMANCE_BESS:
            return "performance/BESS"

        elif self._sim_type == MODEL_VALIDATION_PPM:
            return "model/PPM"

        elif self._sim_type == MODEL_VALIDATION_BESS:
            return "model/BESS"

        return ""

    def get_sim_type(self) -> int:
        """Gets the type of validation executed.

        Returns
        -------
        int
            0 if it is an electrical performance for Synchronous Machine Model
            1 if it is an electrical performance for Power Park Module Model
            2 if it is an electrical performance for Storage Model
            10 if it is a model validation for Power Park Module Model
            11 if it is a model validation for Storage Model
        """
        return self._sim_type

    def get_producer_dyd(self) -> Path:
        """Gets the Producer DYD file.

        Returns
        -------
        Path
            Path to the Producer DYD file
        """
        if self._filename is None:
            pattern_dyd = re.compile(r".*.[dD][yY][dD]")
        else:
            pattern_dyd = re.compile(rf".*.{self._filename}.[dD][yY][dD]")
        return self.__get_file_by_pattern(pattern_dyd)

    def get_producer_par(self):
        """Gets the Producer PAR file.

        Returns
        -------
        Path
            Path to the Producer PAR file
        """
        if self._filename is None:
            pattern_par = re.compile(r".*.[pP][aA][rR]")
        else:
            pattern_par = re.compile(rf".*.{self._filename}.[pP][aA][rR]")
        return self.__get_file_by_pattern(pattern_par)

    def get_producer_curves_path(self) -> Path:
        """Gets the Producer Curves Directory.

        Returns
        -------
        Path
            Path to the Producer Curves Directory
        """
        return self._producer_curves_path.resolve()

    def get_reference_curves_path(self) -> Path:
        """Gets the Reference Curves Directory.

        Returns
        -------
        Path
            Path to the Reference Curves Directory
        """
        return self._reference_curves_path.resolve()

    def set_generators(self, generators: list) -> None:
        """Gets the Producer model generators.

        Parameters
        ----------
        generators: list
            Generators obtained from producer curves
        """
        self._generators = generators

    def get_generators(self) -> list:
        """Gets the Producer model generators.

        Returns
        -------
        list
            Generators defined in the producer model
        """
        return self._generators

    def get_xfmrs(self) -> list:
        """Gets the Producer model transformers.

        Returns
        -------
        list
            Transformers defined in the producer model
        """
        xfmrs = self._stepup_xfmrs
        if self._auxload_xfmr:
            xfmrs.append(self._auxload_xfmr)
        if self._ppm_xfmr:
            xfmrs.append(self._ppm_xfmr)
        return xfmrs

    def get_connected_to_pdr(self) -> list:
        """Gets the Producer models connected to the bus PDR.

        Returns
        -------
        list
            Equipments connected to the bus PDR
        """
        return self._connected_to_pdr
