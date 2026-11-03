#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import configparser
from pathlib import Path

import pytest

import dycov
from dycov.core.initialization import DycovInitializer
from dycov.files import manage_files


class TestDycovInitializer:
    """
    Tests for the DycovInitializer class, covering various initialization
    and configuration setup functionalities.
    """

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker, tmp_path):
        """
        Fixture to set up common mocks for all tests in this class.
        It mocks `dycov.core.initialization.config` to point to a temporary
        directory and creates necessary initial directories, preventing issues
        with frozen dataclasses.
        """
        # Patch the 'config' object as it is imported into the initialization module.
        # This allows mocking its methods without trying to modify a potentially frozen object.
        self.mock_config = mocker.patch("dycov.core.initialization.config")
        self.mock_config.get_config_dir.return_value = tmp_path / "user_config"

        # Set default side_effects/return_values for methods used by _initialize_logger
        # These can be overridden in specific tests if needed.
        self.mock_config.get_value.side_effect = lambda section, key: {
            ("Global", "file_log_level"): "INFO",
            ("Global", "file_formatter"): "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            ("Global", "console_log_level"): "INFO",
            ("Global", "console_formatter"): "%(levelname)s - %(name)s - %(message)s",
        }.get((section, key), None)
        self.mock_config.get_int.return_value = 50 * 1024 * 1024

        # Ensure the mocked config directory exists for tests that need it
        (tmp_path / "user_config").mkdir(parents=True, exist_ok=True)
        (tmp_path / "user_config" / "templates").mkdir(parents=True, exist_ok=True)
        (tmp_path / "user_config" / "log").mkdir(parents=True, exist_ok=True)

        # Mock the logger for initialization tests
        self._mock_logger = mocker.MagicMock()
        mocker.patch("dycov.logging.dycov_logging.get_logger", return_value=self._mock_logger)

        self._mock_get_project_path = mocker.patch(
            "dycov.validate.validation.Validation.get_project_path",
            return_value=tmp_path / "project_root",
        )
        (tmp_path / "project_root" / "configuration").mkdir(parents=True, exist_ok=True)
        (tmp_path / "project_root" / "configuration" / "config.ini").write_text(
            "[dycov]\nversion = 1.1.0\n"
        )
        (tmp_path / "project_root" / "configuration" / "defaultConfig.ini").write_text(
            "[dycov]\nversion = 1.1.0\n"
        )

    @pytest.fixture
    def dycov_initializer(self):
        """
        Provides an instance of DycovInitializer for tests.
        """
        return DycovInitializer()

    @pytest.fixture
    def tool_path_fixture(self, tmp_path):
        """
        Sets up a dummy tool_path with necessary template structure for testing.
        """
        tool_path = tmp_path / "tool"
        templates_dir = tool_path / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "README.md").write_text("README for templates")

        for template in ["PCS", "reports"]:
            template_dir = templates_dir / template
            template_dir.mkdir()
            (template_dir / "README.md").write_text(f"README for {template}")
            if template == "reports":
                (template_dir / "TSO_logo.pdf").write_bytes(b"PDF content")
                (template_dir / "fig_placeholder.pdf").write_bytes(b"PDF content")

            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    dummy_sample_dir = template_dir / category / model / ".DummySample"
                    dummy_sample_dir.mkdir(parents=True, exist_ok=True)
                    (dummy_sample_dir / "dummy.txt").write_text(
                        f"dummy sample for {template}/{category}/{model}"
                    )
        to_declare = templates_dir / "PCS" / "model" / "PPM" / "PCS_RTE-F16z3"
        to_declare.mkdir(parents=True)
        (to_declare / "PCSDescription.ini").write_text(
            "[PCS_RTE-F16z3]\nzone = 3\n[PCS-Benchmarks]\nPCS_RTE-F16z3 =\n"
        )
        (to_declare / "F16Description.ini").write_text(
            "[PCS-Benchmarks]\nPCS_RTE-F16z3 = RecordedTest\n"
        )
        fixed = templates_dir / "PCS" / "model" / "PPM" / "PCS_RTE-I16z1"
        fixed.mkdir(parents=True)
        (fixed / "PCSDescription.ini").write_text(
            "[PCS_RTE-I16z1]\nzone = 3\n[PCS-Benchmarks]\nPCS_RTE-I16z1 = SetPointStep\n"
        )
        return tool_path

    # Test cases for _configure_template_category
    @pytest.mark.parametrize("template_name", ["PCS", "reports"])
    def test_configure_template_category_creates_directories(
        self, dycov_initializer, tmp_path, template_name
    ):
        """
        Verifies that _configure_template_category correctly creates the expected directory
        structure.
        """
        base_template_dir = self.mock_config.get_config_dir.return_value / "templates"
        base_template_dir.mkdir(parents=True, exist_ok=True)

        dycov_initializer._configure_template_category(base_template_dir, template_name)

        expected_dirs = [
            base_template_dir / template_name,
            base_template_dir / template_name / "model",
            base_template_dir / template_name / "performance",
        ]
        for model in ["BESS", "PPM"]:
            expected_dirs.append(base_template_dir / template_name / "model" / model)
        for model in ["BESS", "PPM", "SM"]:
            expected_dirs.append(base_template_dir / template_name / "performance" / model)

        for d in expected_dirs:
            assert d.is_dir()
        assert not (base_template_dir / template_name / "model" / "SM").exists()

    def test_configure_template_category_keeps_a_directory_another_run_just_created(
        self, dycov_initializer, monkeypatch
    ):
        """Several runs initialising one fresh home must not wipe each other's templates."""
        base_template_dir = self.mock_config.get_config_dir.return_value / "templates"
        ppm_dir = base_template_dir / "PCS" / "model" / "PPM"
        ppm_dir.mkdir(parents=True)
        (ppm_dir / "PCSDescription.ini").write_text("[PCS-Benchmarks]\n")
        real_is_dir = Path.is_dir
        monkeypatch.setattr(Path, "is_dir", lambda path: path != ppm_dir and real_is_dir(path))

        dycov_initializer._configure_template_category(base_template_dir, "PCS")

        assert (ppm_dir / "PCSDescription.ini").exists()

    def test_configure_templates_copies_files(
        self, dycov_initializer, tmp_path, tool_path_fixture, mocker
    ):
        """
        Tests that _configure_templates correctly sets up the template directories and
        copies necessary files.
        """
        mock_copy_directory = mocker.patch("dycov.files.manage_files.copy_directory")
        mock_copy_from_path = mocker.patch("dycov.files.manage_files.copy_from_path")

        dycov_initializer._configure_templates(tool_path_fixture)

        user_config_dir = self.mock_config.get_config_dir.return_value
        config_templates_dir = user_config_dir / "templates"

        mock_copy_from_path.assert_any_call(
            tool_path_fixture / "templates" / "README.md", config_templates_dir
        )
        mock_copy_from_path.assert_any_call(
            tool_path_fixture / "templates" / "PCS" / "README.md", config_templates_dir / "PCS"
        )
        mock_copy_from_path.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "README.md",
            config_templates_dir / "reports",
        )
        mock_copy_from_path.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "TSO_logo.pdf",
            config_templates_dir / "reports",
        )
        mock_copy_from_path.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "fig_placeholder.pdf",
            config_templates_dir / "reports",
        )

        mock_copy_from_path.assert_any_call(
            tool_path_fixture
            / "templates"
            / "PCS"
            / "model"
            / "PPM"
            / "PCS_RTE-F16z3"
            / "F16Description.ini",
            config_templates_dir / "PCS" / "model" / "PPM" / "PCS_RTE-F16z3",
        )
        assert mock_copy_from_path.call_count == 6  # Total copy_from_path calls

        # There are 2 templates ("PCS", "reports"), 2 model technologies and
        # 3 performance technologies = 10 copy_directory calls
        assert mock_copy_directory.call_count == 10
        for template in ["PCS", "reports"]:
            for category, models in (
                ("performance", ["SM", "PPM", "BESS"]),
                ("model", ["PPM", "BESS"]),
            ):
                for model in models:
                    src = (
                        tool_path_fixture
                        / "templates"
                        / template
                        / category
                        / model
                        / ".DummySample"
                    )
                    dest = config_templates_dir / template / category / model / ".DummySample"
                    mock_copy_directory.assert_any_call(src, dest, dirs_exist_ok=True)

    def test_configure_templates_leaves_a_copy_of_the_pcs_to_declare(
        self, dycov_initializer, tool_path_fixture, mocker
    ):
        mocker.patch("dycov.files.manage_files.copy_directory")
        user_pcs = self.mock_config.get_config_dir.return_value / "templates" / "PCS" / "model"

        dycov_initializer._configure_templates(tool_path_fixture)

        copied = user_pcs / "PPM" / "PCS_RTE-F16z3" / "F16Description.ini"
        assert copied.read_text() == "[PCS-Benchmarks]\nPCS_RTE-F16z3 = RecordedTest\n"
        assert not (user_pcs / "PPM" / "PCS_RTE-F16z3" / "PCSDescription.ini").exists()
        assert not (user_pcs / "PPM" / "PCS_RTE-I16z1").exists()

    def test_configure_templates_keeps_the_pcs_the_user_already_declared(
        self, dycov_initializer, tool_path_fixture, mocker
    ):
        mocker.patch("dycov.files.manage_files.copy_directory")
        declared = (
            self.mock_config.get_config_dir.return_value
            / "templates"
            / "PCS"
            / "model"
            / "PPM"
            / "PCS_RTE-F16z3"
            / "F16Description.ini"
        )
        declared.parent.mkdir(parents=True)
        declared.write_text("[PCS-Benchmarks]\nPCS_RTE-F16z3 = Recorded\n")

        dycov_initializer._configure_templates(tool_path_fixture)

        assert declared.read_text() == "[PCS-Benchmarks]\nPCS_RTE-F16z3 = Recorded\n"

    def test_a_template_that_cannot_be_copied_is_reported_with_its_traceback(
        self, dycov_initializer, tool_path_fixture, mocker
    ):
        mocker.patch(
            "dycov.files.manage_files.copy_directory",
            side_effect=PermissionError("read-only file system"),
        )
        mocker.patch("dycov.files.manage_files.copy_from_path")

        dycov_initializer._configure_templates(tool_path_fixture)

        assert self._mock_logger.exception.called
        assert not self._mock_logger.error.called

    def test_is_valid_config_file_with_correct_version(self, dycov_initializer, tmp_path):
        """
        Tests _is_valid_config_file with a configuration file having the correct version.
        """
        config_file = tmp_path / "valid_config.ini"
        parser = configparser.ConfigParser()
        parser.add_section("dycov")
        parser.set("dycov", "version", dycov_initializer._DYCOV_TOOL_VERSION)
        with open(config_file, "w") as f:
            parser.write(f)
        assert dycov_initializer._is_valid_config_file(config_file) is True

    def test_is_valid_config_file_with_incorrect_version(self, dycov_initializer, tmp_path):
        """
        Tests _is_valid_config_file with a configuration file having an incorrect version.
        """
        config_file = tmp_path / "invalid_version_config.ini"
        parser = configparser.ConfigParser()
        parser.add_section("dycov")
        parser.set("dycov", "version", "0.9.9")
        with open(config_file, "w") as f:
            parser.write(f)
        assert dycov_initializer._is_valid_config_file(config_file) is False

    def test_is_valid_config_file_without_version_key(self, dycov_initializer, tmp_path):
        """
        Tests _is_valid_config_file with a configuration file missing the version key.
        """
        config_file = tmp_path / "no_version_config.ini"
        parser = configparser.ConfigParser()
        parser.add_section("dycov")
        # No version key set
        with open(config_file, "w") as f:
            parser.write(f)
        assert dycov_initializer._is_valid_config_file(config_file) is False

    def test_is_valid_config_file_non_existent(self, dycov_initializer, tmp_path):
        """
        Tests _is_valid_config_file with a non-existent configuration file.
        """
        config_file = tmp_path / "non_existent.ini"
        assert dycov_initializer._is_valid_config_file(config_file) is False

    def test_find_deprecated_parameters(self, dycov_initializer, tmp_path):
        """
        Tests _find_deprecated_parameters correctly identifies deprecated entries.
        """
        tool_config = configparser.ConfigParser()
        tool_config.read_string("[SectionA]\nkey1 = value1\n[SectionB]\nkey2 = value2\n")

        user_config = configparser.ConfigParser()
        user_config.read_string(
            "[SectionA]\nkey1 = new_value1\nkey_deprecated = old_value_deprecated\n"
            "[SectionC]\nnew_section_key = new_value\n"
        )

        deprecated = dycov_initializer._find_deprecated_parameters(tool_config, user_config)

        expected_deprecated = [
            {"section": "SectionA", "key": "key_deprecated", "value": "old_value_deprecated"},
            {"section": "SectionC", "key": "new_section_key", "value": "new_value"},
        ]
        assert sorted(deprecated, key=lambda x: (x["section"], x["key"])) == sorted(
            expected_deprecated, key=lambda x: (x["section"], x["key"])
        )

    def test_backup_config_file(self, dycov_initializer, tmp_path):
        """
        Tests _backup_config_file correctly renames the user config file.
        """
        user_config_file = self.mock_config.get_config_dir.return_value / "config.ini"
        user_config_file.write_text("initial content")

        # Create a dummy old backup to ensure ID increment
        (self.mock_config.get_config_dir.return_value / "config.ini.OLD.0").write_text(
            "old backup"
        )

        dycov_initializer._backup_config_file(user_config_file)

        assert not user_config_file.exists()
        assert (self.mock_config.get_config_dir.return_value / "config.ini.OLD.1").is_file()

    def test_write_updated_config_no_duplicates(self, dycov_initializer):
        """Updating the config must not duplicate options (regression).

        The [dycov] metadata takes the template value (version advances), while a
        user override in any other section is preserved, each written exactly once.
        """
        config_dir = self.mock_config.get_config_dir.return_value
        (config_dir / "config.ini_BASIC").write_text(
            "[dycov]\nversion = 1.1.0\ntype = basic\n\n[Global]\nfile_log_level = 20\n"
        )
        user_config = configparser.ConfigParser(inline_comment_prefixes=("#",), strict=False)
        user_config.read_string(
            "[dycov]\nversion = 1.0.0.RC\ntype = basic\n[Global]\nfile_log_level = 40\n"
        )

        dycov_initializer._write_updated_config(config_dir / "config.ini", user_config)

        # A strict parse would raise on any duplicated option.
        written = configparser.ConfigParser(inline_comment_prefixes=("#",))
        written.read(config_dir / "config.ini")
        assert written.get("dycov", "version") == "1.1.0"
        assert written.get("Global", "file_log_level") == "40"

    def _update(self, dycov_initializer, user_text: str) -> configparser.ConfigParser:
        """Updates a user configuration the way a run does when the tool carries a newer version:
        from the profiles the tool writes, every option commented out."""
        config_dir = self.mock_config.get_config_dir.return_value
        shipped = Path(dycov.__file__).parent / "configuration"
        manage_files.create_config_file(shipped / "config.ini", config_dir / "config.ini_BASIC")
        manage_files.create_config_file(
            shipped / "defaultConfig.ini", config_dir / "config.ini_ADVANCED"
        )
        (config_dir / "config.ini").write_text(user_text)

        dycov_initializer._check_config_file(
            shipped / "defaultConfig.ini", config_dir / "config.ini"
        )

        written = configparser.ConfigParser(inline_comment_prefixes=("#",), interpolation=None)
        written.optionxform = str
        written.read(config_dir / "config.ini")
        return written

    _USER_SETTINGS = (
        "[DTR]\ncurrent = 20240215\n\n"
        "[Global]\nconsole_log_level = 30\nretired_option = 1\n\n"
        "[Dynawo]\nsimulation_limit = 50\nsim_hMax = 1e-4\n\n"
        "[PCS_RTE-I16z1.GridVoltageStep.Drop.Event]\nsetpoint_step_value = 1e20\n"
    )

    def _assert_keeps_the_user_settings(self, written: configparser.ConfigParser) -> None:
        assert written.get("DTR", "current") == "20240215"
        assert written.get("Global", "console_log_level") == "30"
        assert written.get("Global", "retired_option") == "1"
        assert written.get("Dynawo", "simulation_limit") == "50"
        assert written.get("Dynawo", "sim_hMax") == "1e-4"
        assert written.get("PCS_RTE-I16z1.GridVoltageStep.Drop.Event", "setpoint_step_value") == (
            "1e20"
        )

    @pytest.mark.parametrize("profile", ["basic", "advanced"])
    def test_an_update_keeps_every_setting_of_the_user(self, dycov_initializer, profile):
        """#665: the profiles carry every option commented out, and a section the basic one
        does not have at all; none of it costs the user a setting."""
        written = self._update(
            dycov_initializer,
            f"[dycov]\nversion = 1.0.0\ntype = {profile}\n\n" + self._USER_SETTINGS,
        )

        self._assert_keeps_the_user_settings(written)
        assert written.get("dycov", "version") == DycovInitializer._DYCOV_TOOL_VERSION
        assert written.get("dycov", "type") == profile

    def test_an_updated_configuration_is_valid_and_keeps_the_template_text(
        self, dycov_initializer
    ):
        config_dir = self.mock_config.get_config_dir.return_value
        self._update(
            dycov_initializer, "[dycov]\nversion = 1.0.0\ntype = basic\n\n" + self._USER_SETTINGS
        )

        text = (config_dir / "config.ini").read_text()
        assert dycov_initializer._is_valid_config_file(config_dir / "config.ini") is True
        assert "# # Revision of the DTR a run validates against" in text
        assert text.count("[Dynawo]") == 1
        assert text.count("current =") == 1

    def test_a_configuration_without_version_keeps_its_settings(self, dycov_initializer):
        """#665: a config.ini written by hand, without its [dycov] section, is updated too."""
        written = self._update(dycov_initializer, self._USER_SETTINGS)

        self._assert_keeps_the_user_settings(written)
        assert written.get("dycov", "version") == DycovInitializer._DYCOV_TOOL_VERSION

    def test_an_update_keeps_a_value_as_it_is_written(self, dycov_initializer):
        written = self._update(
            dycov_initializer,
            "[dycov]\nversion = 1.0.0\ntype = basic\n\n"
            "[Global]\nconsole_formatter = %(levelname)s|%(message)s\n"
            "[PCS-Benchmarks]\nPCS_RTE-I16z1 = SetPointStep,\n    GridVoltageStep\n",
        )

        assert written.get("Global", "console_formatter") == "%(levelname)s|%(message)s"
        assert written.get("PCS-Benchmarks", "PCS_RTE-I16z1") == "SetPointStep,\nGridVoltageStep"

    def test_an_update_says_where_the_previous_configuration_is(self, dycov_initializer):
        config_dir = self.mock_config.get_config_dir.return_value
        previous = "[dycov]\nversion = 1.0.0\ntype = basic\n\n" + self._USER_SETTINGS

        self._update(dycov_initializer, previous)

        assert (config_dir / "config.ini.OLD.0").read_text() == previous
        warnings = " ".join(str(call) for call in self._mock_logger.warning.call_args_list)
        assert "config.ini.OLD.0" in warnings
        assert "retired_option" in warnings

    def test_keys_that_differ_only_in_case_are_updated_once(self, dycov_initializer):
        """The tool reads the case of a key, so two of them are two settings, and the file that
        holds them is valid once updated."""
        config_dir = self.mock_config.get_config_dir.return_value
        written = self._update(
            dycov_initializer,
            "[dycov]\nversion = 1.0.0\ntype = basic\n\n"
            "[Dynawo]\nsim_hMax = 1e-4\nsim_hmax = 2e-4\n",
        )

        assert written.get("Dynawo", "sim_hMax") == "1e-4"
        assert written.get("Dynawo", "sim_hmax") == "2e-4"
        assert dycov_initializer._is_valid_config_file(config_dir / "config.ini") is True

    def test_a_section_keeps_the_value_it_gives_a_key_of_default(self, dycov_initializer):
        written = self._update(
            dycov_initializer,
            "[dycov]\nversion = 1.0.0\n\n[DEFAULT]\nsimulation_limit = 100\n\n"
            "[Dynawo]\nsimulation_limit = 600\n",
        )

        assert written.get("Dynawo", "simulation_limit") == "600"
        assert written.get("DTR", "simulation_limit") == "100"

    def test_a_setting_takes_the_place_of_its_line_or_closes_its_section(self, dycov_initializer):
        """The template carries some options commented out already, so the profile comments
        them twice; an option without a line goes after the last lines of its section, before
        the comments of the next one."""
        config_dir = self.mock_config.get_config_dir.return_value
        self._update(
            dycov_initializer,
            "[dycov]\nversion = 1.0.0\ntype = basic\n\n[Dynawo]\nsim_hMax = 1e-4\n\n"
            "[GridCode]\nUdim_400kV = 380\nthr_custom = 0.5\n\n"
            "[PCS-Benchmarks]\nPCS_RTE-I16z1 = SetPointStep\nPCS_RTE-I2 = USetPointStep\n",
        )

        text = (config_dir / "config.ini").read_text()
        assert "Udim_400kV = 405" not in text
        assert (
            text.index("[GridCode]")
            < text.index("Udim_400kV = 380")
            < text.index("## # List of Benchmarks")
        )
        assert text.index("[PCS-Benchmarks]") < text.index("PCS_RTE-I16z1 = SetPointStep")
        assert text.index("PCS_RTE-I16z1 = SetPointStep") < text.index(
            "## # List of Operating conditions"
        )
        for option in ("sim_hMax = 1e-4", "thr_custom = 0.5", "PCS_RTE-I2 = USetPointStep"):
            following = text.split(f"\n{option}\n", 1)[1].split("\n[", 1)[0]
            assert all(
                not line.strip() or line.startswith("# ## #") for line in following.splitlines()
            ), option

    def test_is_valid_config_file_malformed_returns_false(self, dycov_initializer, tmp_path):
        """A malformed config (duplicated option) is treated as invalid, not a crash."""
        config_file = tmp_path / "dup_config.ini"
        config_file.write_text("[dycov]\nversion = 1.1.0\nversion = 1.0.0.RC\n")

        assert dycov_initializer._is_valid_config_file(config_file) is False

    def test_setup_templates(self, dycov_initializer, tool_path_fixture, mocker):
        """
        Tests that _setup_templates orchestrates the setup of templates.
        """
        mock_configure_templates = mocker.patch.object(dycov_initializer, "_configure_templates")

        dycov_initializer._setup_templates_and_models(tool_path_fixture)

        mock_configure_templates.assert_called_once_with(tool_path_fixture)

    def test_initialize_logger_debug_mode(self, dycov_initializer, tmp_path, mocker):
        """
        Tests that _initialize_logger sets log levels to DEBUG when debug is True.
        """
        mock_init_handlers = mocker.patch("dycov.logging.dycov_logging.init_handlers")

        dycov_initializer._initialize_logger(debug=True)

        mock_init_handlers.assert_called_once_with(
            10,  # file_log_level
            self.mock_config.get_value.side_effect(
                "Global", "file_formatter"
            ),  # file_formatter from mock_config
            self.mock_config.get_int.return_value,  # file_max_bytes
            10,  # console_log_level
            self.mock_config.get_value.side_effect(
                "Global", "console_formatter"
            ),  # console_formatter from mock_config
            self.mock_config.get_config_dir.return_value / "log",  # log_dir
        )
