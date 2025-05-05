#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
import configparser
from pathlib import Path

import pytest


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
