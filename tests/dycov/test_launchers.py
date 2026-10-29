from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_args(command):
    args = MagicMock()
    args.command = command
    args.launcher = "dynawo"
    args.dtr = None
    return args


# ---------------------------------------------------------------------------
# Common patches helper
# ---------------------------------------------------------------------------


def _patch_common(mocker):
    mocker.patch("dycov.launchers.get_dynawo_launcher_name", return_value="dynawo")
    mocker.patch("dycov.launchers.shutil.which", return_value="/usr/bin/dynawo")
    mocker.patch("dycov.launchers.DycovInitializer")
    mocker.patch("dycov.launchers.check_dynawo_launcher_availability")


# ---------------------------------------------------------------------------
# Command dispatch tests
# ---------------------------------------------------------------------------


def test_dycov_calls_validate_handler(mocker):
    _patch_common(mocker)

    mock_handle = mocker.patch("dycov.launchers.handle_validate_command")
    mock_setup = mocker.patch("dycov.launchers.setup_cli_parsers")

    mock_setup.return_value.parse_args.return_value = _fake_args("validate")

    from dycov.launchers import dycov

    dycov()

    mock_handle.assert_called_once()


def test_dycov_calls_compile_handler(mocker):
    _patch_common(mocker)
    mock_setup = mocker.patch("dycov.launchers.setup_cli_parsers")

    mock_setup.return_value.parse_args.return_value = _fake_args("compile")

    from dycov.launchers import dycov

    dycov()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_dycov_raises_when_dynawo_not_available(mocker):
    mocker.patch(
        "dycov.launchers.check_dynawo_launcher_availability",
        side_effect=RuntimeError("Dynawo launcher not found"),
    )
    mocker.patch(
        "dycov.launchers.setup_cli_parsers"
    ).return_value.parse_args.return_value = _fake_args("validate")

    from dycov.launchers import dycov

    with pytest.raises(RuntimeError, match="Dynawo launcher not found"):
        dycov()


def test_dycov_unknown_command_logs_error(mocker, caplog):
    _patch_common(mocker)

    mock_setup = mocker.patch("dycov.launchers.setup_cli_parsers")
    mock_setup.return_value.parse_args.return_value = _fake_args("unknown")

    from dycov.launchers import dycov

    result = dycov()

    assert result == 1
    assert "Unknown" in caplog.text or "command" in caplog.text


def test_dycov_empty_command_logs_error(mocker, caplog):
    _patch_common(mocker)

    args = MagicMock()
    args.command = None
    args.launcher = "dynawo"

    mocker.patch("dycov.launchers.setup_cli_parsers").return_value.parse_args.return_value = args

    from dycov.launchers import dycov

    result = dycov()

    assert result == 1
    assert "Please provide a command" in caplog.text


# ---------------------------------------------------------------------------
# Selection of the DTR revision
# ---------------------------------------------------------------------------


def _config(mocker, current, available):
    config = mocker.patch("dycov.configuration.cfg.config")
    config.get_value.return_value = current
    config.get_list.return_value = available
    return config


def test_the_run_keeps_the_revision_of_the_configuration(mocker):
    _config(mocker, "20240215", ["20240215"])
    parser = MagicMock()
    args = _fake_args("performance")
    args.dtr = None

    from dycov.launchers import DycovCLI

    DycovCLI()._select_dtr_revision(parser, args)

    parser.error.assert_not_called()


def test_the_dtr_option_overrides_the_configuration(mocker):
    config = _config(mocker, "20250801", ["20240215", "20250801"])
    parser = MagicMock()
    args = _fake_args("performance")
    args.dtr = "20250801"

    from dycov.launchers import DycovCLI

    DycovCLI()._select_dtr_revision(parser, args)

    config.set_value.assert_called_once_with("DTR", "current", "20250801")
    parser.error.assert_not_called()


def test_a_revision_the_tool_does_not_implement_stops_the_run(mocker):
    _config(mocker, "19991231", ["20240215"])
    parser = MagicMock()
    args = _fake_args("performance")
    args.dtr = "19991231"

    from dycov.launchers import DycovCLI

    DycovCLI()._select_dtr_revision(parser, args)

    parser.error.assert_called_once()
    assert "19991231" in parser.error.call_args[0][0]
