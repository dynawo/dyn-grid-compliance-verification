from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_args(command):
    args = MagicMock()
    args.command = command
    args.launcher = "dynawo"
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


def test_dycov_calls_generate_handler(mocker):
    _patch_common(mocker)

    mock_handle = mocker.patch("dycov.launchers.handle_generate_command")
    mock_setup = mocker.patch("dycov.launchers.setup_cli_parsers")

    mock_setup.return_value.parse_args.return_value = _fake_args("generate")

    from dycov.launchers import dycov

    dycov()

    mock_handle.assert_called_once()


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

    mock_handle = mocker.patch("dycov.launchers.handle_compile_command")
    mock_setup = mocker.patch("dycov.launchers.setup_cli_parsers")

    mock_setup.return_value.parse_args.return_value = _fake_args("compile")

    from dycov.launchers import dycov

    dycov()

    mock_handle.assert_called_once()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_dycov_raises_when_dynawo_not_available(mocker):
    mocker.patch(
        "dycov.launchers.check_dynawo_launcher_availability",
        side_effect=RuntimeError("Dynawo launcher not found"),
    )
    mocker.patch("dycov.launchers.setup_cli_parsers").return_value.parse_args.return_value = (
        _fake_args("generate")
    )

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
