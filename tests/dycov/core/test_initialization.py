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
from pathlib import Path

import pytest

from dycov.core import initialization


class Test_TemplateCmdConfig:

    # Creates template directory when none of the required directories exist
    def test_creates_template_directory_when_none_exist(self, mocker):
        # Arrange
        mock_config = mocker.patch("dycov.core.initialization.config")
        mock_config_dir = Path("/fake/config/dir")
        mock_config.get_config_dir.return_value = mock_config_dir

        # Mock is_dir to return False for all directory checks
        mocker.patch.object(Path, "is_dir", return_value=False)

        # Mock create_dir function
        mock_create_dir = mocker.patch("dycov.core.initialization.manage_files.create_dir")

        template = "my_template"
        cmd = "my_cmd"
        expected_template_dir = mock_config_dir / "templates" / template / cmd

        # Act
        from dycov.core.initialization import _template_cmd_config

        _template_cmd_config(template, cmd)

        # Assert
        mock_create_dir.assert_called_once_with(expected_template_dir)

    # Creates template directories for each subdir (model, performance)
    def test_creates_template_directories_for_subdirs(self, mocker):
        # Arrange
        mock_template_cmd_config = mocker.patch("dycov.core.initialization._template_cmd_config")
        template_name = "test_template"

        # Act
        from dycov.core.initialization import _template_config

        _template_config(template_name)

        # Assert
        # Check that _template_cmd_config was called for each subdir
        mock_template_cmd_config.assert_any_call(template_name, "model")
        mock_template_cmd_config.assert_any_call(template_name, "performance")

        # Check that _template_cmd_config was called for each model in each subdir
        mock_template_cmd_config.assert_any_call(f"{template_name}/model", "BESS")
        mock_template_cmd_config.assert_any_call(f"{template_name}/model", "PPM")
        mock_template_cmd_config.assert_any_call(f"{template_name}/model", "SM")
        mock_template_cmd_config.assert_any_call(f"{template_name}/performance", "BESS")
        mock_template_cmd_config.assert_any_call(f"{template_name}/performance", "PPM")
        mock_template_cmd_config.assert_any_call(f"{template_name}/performance", "SM")

        # Verify total number of calls (2 subdirs + 2*3 models = 8 calls)
        assert mock_template_cmd_config.call_count == 8

    # Function correctly creates template directories for PCS and reports
    def test_templates_config_creates_directories(self, mocker):
        # Arrange
        mock_template_config = mocker.patch("dycov.core.initialization._template_config")
        mock_dummysamples_config = mocker.patch("dycov.core.initialization._dummysamples_config")
        mock_shutil_copy = mocker.patch("shutil.copy")
        mock_config = mocker.patch("dycov.core.initialization.config")
        mock_config.get_config_dir.return_value = Path("/mock/config/dir")

        tool_path = Path("/mock/tool/path")

        # Act
        from dycov.core.initialization import _templates_config

        _templates_config(tool_path)

        # Assert
        assert mock_template_config.call_count == 2
        mock_template_config.assert_any_call("PCS")
        mock_template_config.assert_any_call("reports")

        assert mock_dummysamples_config.call_count == 2
        mock_dummysamples_config.assert_any_call(tool_path, "PCS")
        mock_dummysamples_config.assert_any_call(tool_path, "reports")

        assert mock_shutil_copy.call_count == 5
        mock_shutil_copy.assert_any_call(
            tool_path / "templates" / "README.md", mock_config.get_config_dir() / "templates"
        )
        mock_shutil_copy.assert_any_call(
            tool_path / "templates" / "PCS" / "README.md",
            mock_config.get_config_dir() / "templates" / "PCS",
        )
        mock_shutil_copy.assert_any_call(
            tool_path / "templates" / "reports" / "README.md",
            mock_config.get_config_dir() / "templates" / "reports",
        )
        mock_shutil_copy.assert_any_call(
            tool_path / "templates" / "reports" / "TSO_logo.pdf",
            mock_config.get_config_dir() / "templates" / "reports",
        )
        mock_shutil_copy.assert_any_call(
            tool_path / "templates" / "reports" / "fig_placeholder.pdf",
            mock_config.get_config_dir() / "templates" / "reports",
        )

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "templates").mkdir(parents=True)
        (config_dir / "user_models" / "dictionary").mkdir(parents=True)
        (config_dir / "log").mkdir()
        yield config_dir

    @pytest.fixture
    def valid_config_file(self, tmp_path):
        config_file = tmp_path / "config.ini"
        parser = configparser.ConfigParser()
        parser.add_section("dycov")
        parser.set("dycov", "version", "1.0.0.RC")
        with open(config_file, "w") as f:
            parser.write(f)
        return config_file

    def test_is_valid_config_file_with_correct_version(self, valid_config_file):
        from dycov.core.initialization import _is_valid_config_file

        assert _is_valid_config_file(valid_config_file) is True

    def test_exit_on_precompile_abort(self, tmp_path, monkeypatch):
        launcher_dwo = tmp_path / "launcher"
        # Patch precompile to return True (aborted)
        monkeypatch.setattr("dycov.core.initialization.precompile", lambda launcher: True)
        with pytest.raises(SystemExit):
            from dycov.core.initialization import _prepare_dynawo_models

            _prepare_dynawo_models(launcher_dwo)

    @pytest.fixture
    def tool_and_config_dirs(self, tmp_path):
        # Setup tool_path with required template files and directories
        tool_path = tmp_path / "tool"
        templates_dir = tool_path / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "README.md").write_text("README for templates")
        for template in ["PCS", "reports"]:
            template_dir = templates_dir / template
            template_dir.mkdir()
            (template_dir / "README.md").write_text(f"README for {template}")
            for fname in ["TSO_logo.pdf", "fig_placeholder.pdf"]:
                if template == "reports":
                    (template_dir / fname).write_bytes(b"PDF content")
            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    dummy_dir = template_dir / category / model / ".DummySample"
                    dummy_dir.mkdir(parents=True, exist_ok=True)
                    (dummy_dir / "dummy.txt").write_text("dummy sample")

        # Setup config.get_config_dir() to point to user config dir
        config_dir = tmp_path / "user_config"
        (config_dir / "templates").mkdir(parents=True)
        (config_dir / "user_models" / "dictionary").mkdir(parents=True)
        (config_dir / "log").mkdir(parents=True)

        # Patch config.get_config_dir to return config_dir
        import dycov.core.initialization as initialization_mod

        initialization_mod.config.get_config_dir = lambda: config_dir

        yield tool_path, config_dir

    # Initializes dycov tool with valid launcher_dwo path and debug=False
    def test_init_with_valid_launcher_dwo_and_debug_false(self, mocker):
        # Arrange
        launcher_dwo = Path("/path/to/launcher_dwo")
        debug = False

        # Mock dependencies
        mock_setup_user_config = mocker.patch("dycov.core.initialization._setup_user_config")
        mock_setup_templates_and_models = mocker.patch(
            "dycov.core.initialization._setup_templates_and_models"
        )
        mock_initialize_logger = mocker.patch("dycov.core.initialization._initialize_logger")
        mock_prepare_dynawo_models = mocker.patch(
            "dycov.core.initialization._prepare_dynawo_models"
        )
        mock_logger = mocker.MagicMock()
        mocker.patch(
            "dycov.core.initialization.dycov_logging.get_logger", return_value=mock_logger
        )
        mocker.patch("dycov.core.initialization.version", return_value="1.0.0")

        # Act
        from dycov.core.initialization import init

        init(launcher_dwo, debug)

        # Assert
        mock_setup_user_config.assert_called_once()
        mock_setup_templates_and_models.assert_called_once()
        mock_initialize_logger.assert_called_once_with(debug)
        mock_prepare_dynawo_models.assert_called_once_with(launcher_dwo)
        mock_logger.info.assert_called_once_with("Starting DyCoV - version 1.0.0")

    def test_initialize_logger_with_debug_true(self, tmp_path, mocker):
        # Setup config dir and log dir
        log_dir = tmp_path / "log"
        log_dir.mkdir(parents=True)
        config_dir = tmp_path

        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir
        # Patch config.get_value and get_int to return known values
        mock_config.get_value.return_value = lambda section, key: "INFO"
        mock_config.get_int.return_value = lambda section, key, default: 123456

        # Patch dycov_logging.init_handlers to capture arguments
        called = {}

        def fake_init_handlers(
            file_log_level,
            file_formatter,
            file_max_bytes,
            console_log_level,
            console_formatter,
            log_dir_arg,
            *args,
            **kwargs,
        ):
            called.update(
                {
                    "file_log_level": file_log_level,
                    "file_formatter": file_formatter,
                    "file_max_bytes": file_max_bytes,
                    "console_log_level": console_log_level,
                    "console_formatter": console_formatter,
                    "log_dir": log_dir_arg,
                }
            )

        initialization.dycov_logging.init_handlers = fake_init_handlers
        # Run
        initialization._initialize_logger(debug=True)
        # Assert
        assert called["file_log_level"] == "DEBUG"
        assert called["console_log_level"] == "DEBUG"
        assert called["log_dir"] == log_dir

    def test_user_models_creates_dictionary_and_ini_files(self, tmp_path, mocker):
        config_dir = tmp_path
        user_models_dir = config_dir / "user_models" / "dictionary"
        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir
        # Remove user_models dir if exists
        if user_models_dir.exists():
            shutil.rmtree(user_models_dir.parent)
        # Run
        initialization._user_models()
        # Assert
        assert user_models_dir.is_dir()
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
            assert (user_models_dir / fname).is_file()

    def test_dummysamples_config_copies_existing_directories(self, tmp_path, mocker):
        tool_path = tmp_path / "tool"
        config_dir = tmp_path / "config"
        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir
        categories = ["performance", "model"]
        models = ["SM", "PPM", "BESS"]
        source = "PCS"
        # Create dummy sample source dirs and files
        for category in categories:
            for model in models:
                src = tool_path / "templates" / source / category / model / ".DummySample"
                src.mkdir(parents=True, exist_ok=True)
                (src / "dummy.txt").write_text("dummy")
        # Create destination parent dirs
        for category in categories:
            for model in models:
                dest = config_dir / "templates" / source / category / model
                dest.mkdir(parents=True, exist_ok=True)
        # Run
        initialization._dummysamples_config(tool_path, source)
        # Assert
        for category in categories:
            for model in models:
                dest = config_dir / "templates" / source / category / model / ".DummySample"
                assert dest.is_dir()
                assert (dest / "dummy.txt").is_file()

    def test_setup_user_config_creates_missing_config_file(self, tmp_path, mocker):
        config_dir = tmp_path
        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir
        # Prepare required config.ini_BASIC and config.ini_ADVANCED
        basic = config_dir / "config.ini_BASIC"
        advanced = config_dir / "config.ini_ADVANCED"
        basic.write_text("[dycov]\nversion = 1.0.0.RC\n")
        advanced.write_text("[dycov]\nversion = 1.0.0.RC\n")
        # Remove config.ini if exists
        config_ini = config_dir / "config.ini"
        if config_ini.exists():
            config_ini.unlink()

        # Patch Validation.get_project_path to return a dummy path with configuration files
        class DummyValidation:
            @staticmethod
            def get_project_path():
                return tmp_path

        initialization.Validation = DummyValidation
        # Create configuration/config.ini and configuration/defaultConfig.ini
        conf_dir = tmp_path / "configuration"
        conf_dir.mkdir(exist_ok=True)
        (conf_dir / "config.ini").write_text("[dycov]\nversion = 1.0.0.RC\n")
        (conf_dir / "defaultConfig.ini").write_text("[dycov]\nversion = 1.0.0.RC\n")
        # Run
        initialization._setup_user_config()
        # Assert
        assert (config_dir / "config.ini").is_file()

    def test_is_valid_config_file_with_incorrect_version(self, tmp_path):
        config_file = tmp_path / "config.ini"
        parser = configparser.ConfigParser()
        parser.add_section("dycov")
        parser.set("dycov", "version", "0.9.9")
        with open(config_file, "w") as f:
            parser.write(f)
        assert initialization._is_valid_config_file(config_file) is False

    def test_setup_templates_and_models_creates_directories_and_files(self, tmp_path, mocker):
        tool_path = tmp_path / "tool"
        config_dir = tmp_path / "config"
        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir
        # Prepare tool_path/templates/PCS/model/SM/.DummySample etc.
        for template in ["PCS", "reports"]:
            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    dummy = tool_path / "templates" / template / category / model / ".DummySample"
                    dummy.mkdir(parents=True, exist_ok=True)
                    (dummy / "dummy.txt").write_text("dummy")
            # Add README.md and PDFs for reports
            tdir = tool_path / "templates" / template
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / "README.md").write_text("README")
            if template == "reports":
                (tdir / "TSO_logo.pdf").write_bytes(b"pdf")
                (tdir / "fig_placeholder.pdf").write_bytes(b"pdf")
        (tool_path / "templates" / "README.md").write_text("README")
        # Create config_dir/templates and user_models/dictionary
        (config_dir / "templates").mkdir(parents=True, exist_ok=True)
        (config_dir / "user_models" / "dictionary").mkdir(parents=True, exist_ok=True)
        # Run
        initialization._setup_templates_and_models(tool_path)
        # Assert: check that dummy samples and PDFs are copied
        for template in ["PCS", "reports"]:
            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    dest = config_dir / "templates" / template / category / model / ".DummySample"
                    assert dest.is_dir()
                    assert (dest / "dummy.txt").is_file()
        assert (config_dir / "templates" / "README.md").is_file()
        assert (config_dir / "templates" / "PCS" / "README.md").is_file()
        assert (config_dir / "templates" / "reports" / "README.md").is_file()
        assert (config_dir / "templates" / "reports" / "TSO_logo.pdf").is_file()
        assert (config_dir / "templates" / "reports" / "fig_placeholder.pdf").is_file()
        # User models .ini files
        for fname in [
            "Bus.ini",
            "Line.ini",
            "Load.ini",
            "Power_Park.ini",
            "Storage.ini",
            "Synch_Gen.ini",
            "Transformer.ini",
        ]:
            assert (config_dir / "user_models" / "dictionary" / fname).is_file()

    def test_init_exits_on_precompile_abort(self, tmp_path, mocker, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        mock_config = mocker.patch("dycov.core.initialization.config")

        # Patch config.get_config_dir to return our tmp_path
        mock_config.get_config_dir.return_value = config_dir

        # Patch Validation.get_project_path to return a dummy path
        class DummyValidation:
            @staticmethod
            def get_project_path():
                return tmp_path

        initialization.Validation = DummyValidation
        # Create configuration/config.ini and configuration/defaultConfig.ini
        conf_dir = tmp_path / "configuration"
        conf_dir.mkdir(exist_ok=True)
        (conf_dir / "config.ini").write_text("[dycov]\nversion = 1.0.0.RC\n")
        (conf_dir / "defaultConfig.ini").write_text("[dycov]\nversion = 1.0.0.RC\n")
        # Prepare tool_path/templates/PCS/model/SM/.DummySample etc.
        tool_path = tmp_path
        for template in ["PCS", "reports"]:
            for category in ["performance", "model"]:
                for model in ["SM", "PPM", "BESS"]:
                    dummy = tool_path / "templates" / template / category / model / ".DummySample"
                    dummy.mkdir(parents=True, exist_ok=True)
                    (dummy / "dummy.txt").write_text("dummy")
            tdir = tool_path / "templates" / template
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / "README.md").write_text("README")
            if template == "reports":
                (tdir / "TSO_logo.pdf").write_bytes(b"pdf")
                (tdir / "fig_placeholder.pdf").write_bytes(b"pdf")
        (tool_path / "templates" / "README.md").write_text("README")

        # Patch dycov_logging.get_logger to a dummy logger
        class DummyLogger:
            def info(self, msg):
                pass

        dummy_logger = DummyLogger()
        monkeypatch.setattr("dycov.dynawo.dynawo.dycov_logging", dummy_logger)

        # Patch version to return a string
        initialization.version = lambda name: "1.0.0"
        # Patch precompile to abort
        initialization.precompile = lambda launcher: True
        launcher_dwo = tmp_path / "launcher"
        # Expect SystemExit
        with pytest.raises(SystemExit):
            initialization.init(launcher_dwo, debug=False)
