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
import shutil

import pytest

from dycov.core.initialization import DycovInitializer  # Import the class

# No need to import cfg directly if patching via string path


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
        (tmp_path / "user_config" / "user_models" / "dictionary").mkdir(
            parents=True, exist_ok=True
        )
        (tmp_path / "user_config" / "log").mkdir(parents=True, exist_ok=True)

        # Mock the logger for initialization tests
        self._mock_logger = mocker.MagicMock()
        mocker.patch(
            "dycov.logging.logging.dycov_logging.get_logger", return_value=self._mock_logger
        )
        # We'll assert this directly in initialize_logger tests, no need to patch globally here
        # mocker.patch("dycov.logging.logging.dycov_logging.init_handlers")

        # Mock Validation.get_project_path
        self._mock_get_project_path = mocker.patch(
            "dycov.core.validation.Validation.get_project_path",
            return_value=tmp_path / "project_root",
        )
        # Create dummy project root config files
        (tmp_path / "project_root" / "configuration").mkdir(parents=True, exist_ok=True)
        (tmp_path / "project_root" / "configuration" / "config.ini").write_text(
            "[dycov]\nversion = 1.0.0.RC\n"
        )
        (tmp_path / "project_root" / "configuration" / "defaultConfig.ini").write_text(
            "[dycov]\nversion = 1.0.0.RC\n"
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
                    dummy_sample_dir.mkdir(
                        parents=True, exist_ok=True
                    )  # <-- This creates the directory
                    (dummy_sample_dir / "dummy.txt").write_text(
                        f"dummy sample for {template}/{category}/{model}"
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
        for model in ["BESS", "PPM", "SM"]:
            expected_dirs.append(base_template_dir / template_name / "model" / model)
            expected_dirs.append(base_template_dir / template_name / "performance" / model)

        for d in expected_dirs:
            assert d.is_dir()

    def test_configure_templates_copies_files(
        self, dycov_initializer, tmp_path, tool_path_fixture, mocker
    ):
        """
        Tests that _configure_templates correctly sets up the template directories and
        copies necessary files.
        """
        mock_copy_path = mocker.patch("dycov.files.manage_files.copy_path")
        mock_copy_files = mocker.patch("dycov.files.manage_files.copy_files")

        dycov_initializer._configure_templates(tool_path_fixture)

        user_config_dir = self.mock_config.get_config_dir.return_value
        config_templates_dir = user_config_dir / "templates"

        # Assert copy_files calls
        mock_copy_files.assert_any_call(
            tool_path_fixture / "templates" / "README.md", config_templates_dir
        )
        mock_copy_files.assert_any_call(
            tool_path_fixture / "templates" / "PCS" / "README.md", config_templates_dir / "PCS"
        )
        mock_copy_files.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "README.md",
            config_templates_dir / "reports",
        )
        mock_copy_files.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "TSO_logo.pdf",
            config_templates_dir / "reports",
        )
        mock_copy_files.assert_any_call(
            tool_path_fixture / "templates" / "reports" / "fig_placeholder.pdf",
            config_templates_dir / "reports",
        )

        assert mock_copy_files.call_count == 5  # Total copy_files calls

        # Assert copy_path calls for dummy samples
        # There are 2 templates ("PCS", "reports"), 2 categories, 3 models = 12 copy_path calls
        assert mock_copy_path.call_count == 12
        for template in ["PCS", "reports"]:
            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    src = (
                        tool_path_fixture
                        / "templates"
                        / template
                        / category
                        / model
                        / ".DummySample"
                    )
                    dest = config_templates_dir / template / category / model / ".DummySample"
                    mock_copy_path.assert_any_call(src, dest, dirs_exist_ok=True)

    def test_configure_user_models_creates_files(self, dycov_initializer, tmp_path):
        """
        Verifies that _configure_user_models creates the expected user model dictionary and files.
        """
        user_models_dict_path = (
            self.mock_config.get_config_dir.return_value / "user_models" / "dictionary"
        )
        # Ensure the directory is clean before the test
        if user_models_dict_path.exists():
            shutil.rmtree(user_models_dict_path)

        dycov_initializer._configure_user_models()

        assert user_models_dict_path.is_dir()
        expected_files = [
            "Bus.ini",
            "Line.ini",
            "Load.ini",
            "Power_Park.ini",
            "Storage.ini",
            "Synch_Gen.ini",
            "Transformer.ini",
        ]
        for fname in expected_files:
            assert (user_models_dict_path / fname).is_file()

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

    def test_log_deprecated_parameters(self, dycov_initializer):
        """
        Tests _log_deprecated_parameters correctly logs warnings.
        """
        deprecated_params = [
            {"section": "Global", "key": "old_setting", "value": "true"},
            {"section": "Logging", "key": "format", "value": "%(message)s"},
        ]
        file_name = "user_config.ini"

        dycov_initializer._log_deprecated_parameters(deprecated_params, file_name)

        self._mock_logger.warning.assert_any_call(
            "Deprecated in user_config.ini: section Global key old_setting value true"
        )
        self._mock_logger.warning.assert_any_call(
            "Deprecated in user_config.ini: section Logging key format value %(message)s"
        )
        assert self._mock_logger.warning.call_count == len(deprecated_params)

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

    def test_setup_templates_and_models(
        self, dycov_initializer, tmp_path, tool_path_fixture, mocker
    ):
        """
        Tests that _setup_templates_and_models orchestrates the setup of templates and user models.
        """
        mock_configure_templates = mocker.patch.object(dycov_initializer, "_configure_templates")
        mock_configure_user_models = mocker.patch.object(
            dycov_initializer, "_configure_user_models"
        )

        dycov_initializer._setup_templates_and_models(tool_path_fixture)

        mock_configure_templates.assert_called_once_with(tool_path_fixture)
        mock_configure_user_models.assert_called_once()

    def test_initialize_logger_debug_mode(self, dycov_initializer, tmp_path, mocker):
        """
        Tests that _initialize_logger sets log levels to DEBUG when debug is True.
        """
        # Ensure init_handlers is mocked correctly
        mock_init_handlers = mocker.patch("dycov.logging.logging.dycov_logging.init_handlers")

        dycov_initializer._initialize_logger(debug=True)

        mock_init_handlers.assert_called_once_with(
            "DEBUG",  # file_log_level
            self.mock_config.get_value.side_effect(
                "Global", "file_formatter"
            ),  # file_formatter from mock_config
            self.mock_config.get_int.return_value,  # file_max_bytes
            "DEBUG",  # console_log_level
            self.mock_config.get_value.side_effect(
                "Global", "console_formatter"
            ),  # console_formatter from mock_config
            self.mock_config.get_config_dir.return_value / "log",  # log_dir
        )

    def test_initialize_logger_no_debug(self, dycov_initializer, tmp_path, mocker):
        """
        Tests that _initialize_logger uses configured log levels when debug is False.
        """
        # Ensure init_handlers is mocked correctly
        mock_init_handlers = mocker.patch("dycov.logging.logging.dycov_logging.init_handlers")

        # Override default mock config behavior for this specific test
        self.mock_config.get_value.side_effect = lambda section, key: {
            ("Global", "file_log_level"): "WARNING",
            ("Global", "file_formatter"): "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            ("Global", "console_log_level"): "ERROR",
            ("Global", "console_formatter"): "%(levelname)s - %(name)s - %(message)s",
        }.get((section, key), None)
        self.mock_config.get_int.return_value = 50 * 1024 * 1024

        dycov_initializer._initialize_logger(debug=False)

        mock_init_handlers.assert_called_once_with(
            "WARNING",  # file_log_level
            self.mock_config.get_value.side_effect("Global", "file_formatter"),  # file_formatter
            self.mock_config.get_int.return_value,  # file_max_bytes
            "ERROR",  # console_log_level
            self.mock_config.get_value.side_effect(
                "Global", "console_formatter"
            ),  # console_formatter
            self.mock_config.get_config_dir.return_value / "log",  # log_dir
        )

    def test_init_full_flow_no_launcher_precompile_skipped(
        self, dycov_initializer, tmp_path, tool_path_fixture, mocker
    ):
        """
        Tests the complete `init` method flow when no Dynawo launcher is provided (None).
        Precompilation should be skipped.
        """
        launcher_dwo = None
        debug_mode = False

        # Mock internal methods called by init
        mock_setup_user_config = mocker.patch.object(dycov_initializer, "_setup_user_config")
        mock_setup_templates_and_models = mocker.patch.object(
            dycov_initializer, "_setup_templates_and_models"
        )
        mock_initialize_logger = mocker.patch.object(dycov_initializer, "_initialize_logger")
        mock_prepare_dynawo_models = mocker.patch(
            "dycov.dynawo.prepare_tool.precompile", return_value=False
        )  # Even if it's not called, define it
        mocker.patch("dycov.core.initialization.version", return_value="test_version")

        dycov_initializer.init(launcher_dwo, debug_mode)

        mock_setup_user_config.assert_called_once_with(mocker.ANY)
        mock_setup_templates_and_models.assert_called_once_with(mocker.ANY)
        mock_initialize_logger.assert_called_once_with(debug_mode)
        self._mock_logger.info.assert_called_once_with("Starting DyCoV - version test_version")
        mock_prepare_dynawo_models.assert_not_called()  # Crucially, this should not be called
