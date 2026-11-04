import os
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
    args.user_config = None
    return args


# ---------------------------------------------------------------------------
# Common patches helper
# ---------------------------------------------------------------------------


def _patch_common(mocker):
    mocker.patch("dycov.launchers.get_dynawo_launcher_name", return_value="dynawo")
    mocker.patch("dycov.launchers.shutil.which", return_value="/usr/bin/dynawo")
    mocker.patch("dycov.launchers.DycovInitializer")
    mocker.patch("dycov.launchers.check_dynawo_launcher_availability")
    mocker.patch("dycov.launchers.check_report_tools_availability")


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


# ---------------------------------------------------------------------------
# The tools the report needs
# ---------------------------------------------------------------------------


def _run(mocker, command, model=None, curves_only=False):
    _patch_common(mocker)
    mocker.patch(f"dycov.launchers.handle_{command}_command")
    args = _fake_args(command)
    args.model = model
    args.excel = None
    args.curves_only = curves_only
    mocker.patch("dycov.launchers.setup_cli_parsers").return_value.parse_args.return_value = args

    from dycov.launchers import dycov

    dycov()


@pytest.mark.parametrize("command", ["validate", "performance"])
@pytest.mark.parametrize("model", ["Dynawo", None], ids=["model", "curves"])
def test_a_run_that_builds_the_report_checks_its_tools(mocker, command, model):
    _run(mocker, command, model=model)

    from dycov import launchers

    launchers.check_report_tools_availability.assert_called_once()


@pytest.mark.parametrize("command", ["validate", "performance"])
def test_a_curves_only_run_does_not_ask_for_the_report_tools(mocker, command):
    _run(mocker, command, model="Dynawo", curves_only=True)

    from dycov import launchers

    launchers.check_report_tools_availability.assert_not_called()
    launchers.check_dynawo_launcher_availability.assert_called_once()


@pytest.mark.parametrize("command", ["anonymize", "excel2inputs", "migrate_inputs"])
def test_a_command_without_report_does_not_ask_for_its_tools(mocker, command):
    _run(mocker, command)

    from dycov import launchers

    launchers.check_report_tools_availability.assert_not_called()


def test_a_missing_report_tool_stops_the_run_naming_it(mocker, caplog):
    mocker.patch(
        "dycov.cli.utils.system_checks.check_report_tools",
        side_effect=OSError("PdfLatex not found."),
    )

    from dycov.cli.utils import check_report_tools_availability

    with pytest.raises(SystemExit) as exit_info:
        check_report_tools_availability()

    assert exit_info.value.code == 1
    assert "PdfLatex not found." in caplog.text
    assert "Dynawo launcher" not in caplog.text


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


# ---------------------------------------------------------------------------
# The configuration file given with --user-config
# ---------------------------------------------------------------------------


def test_a_readable_user_configuration_lets_the_run_go_on(tmp_path):
    user_file = tmp_path / "user.ini"
    user_file.write_text("[DTR]\ncurrent = 20240215\n")
    parser = MagicMock()
    args = _fake_args("performance")
    args.user_config = user_file

    from dycov.launchers import DycovCLI

    DycovCLI()._check_user_config(parser, args)

    parser.error.assert_not_called()


def test_a_user_configuration_read_from_a_pipe_lets_the_run_go_on(tmp_path):
    """A process substitution or /dev/stdin is no regular file, but it can be read."""
    user_pipe = tmp_path / "user.ini"
    os.mkfifo(user_pipe)
    parser = MagicMock()
    args = _fake_args("performance")
    args.user_config = user_pipe

    from dycov.launchers import DycovCLI

    DycovCLI()._check_user_config(parser, args)

    parser.error.assert_not_called()


def test_without_a_user_configuration_nothing_is_checked():
    parser = MagicMock()

    from dycov.launchers import DycovCLI

    DycovCLI()._check_user_config(parser, _fake_args("performance"))

    parser.error.assert_not_called()


_ROOT_READS_ANY_FILE = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads any file"
)


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "directory",
        "name too long",
        pytest.param("unreadable", marks=_ROOT_READS_ANY_FILE),
        pytest.param("in a directory that cannot be entered", marks=_ROOT_READS_ANY_FILE),
    ],
)
def test_a_user_configuration_that_cannot_be_read_stops_the_run(tmp_path, kind):
    user_file = tmp_path / "user_2042.ini"
    locked = tmp_path / "locked"
    if kind == "directory":
        user_file.mkdir()
    elif kind == "name too long":
        user_file = tmp_path / ("user" * 70 + ".ini")
    elif kind == "unreadable":
        user_file.write_text("[DTR]\ncurrent = 20240215\n")
        user_file.chmod(0)
    elif kind == "in a directory that cannot be entered":
        locked.mkdir()
        user_file = locked / "user_2042.ini"
        user_file.write_text("[DTR]\ncurrent = 20240215\n")
        locked.chmod(0)
    parser = MagicMock()
    args = _fake_args("performance")
    args.user_config = user_file

    from dycov.launchers import DycovCLI

    try:
        DycovCLI()._check_user_config(parser, args)
    finally:
        if locked.exists():
            locked.chmod(0o700)

    parser.error.assert_called_once()
    assert str(user_file) in parser.error.call_args[0][0]


def test_an_unreadable_user_configuration_stops_the_run_before_anything_is_set_up(
    mocker, tmp_path
):
    _patch_common(mocker)
    initializer = mocker.patch("dycov.launchers.DycovInitializer")
    parser = mocker.patch("dycov.launchers.setup_cli_parsers").return_value
    parser.error.side_effect = SystemExit(2)
    args = _fake_args("performance")
    args.user_config = tmp_path / "user_2042.ini"
    parser.parse_args.return_value = args

    from dycov.launchers import dycov

    with pytest.raises(SystemExit):
        dycov()

    initializer.return_value.init.assert_not_called()
