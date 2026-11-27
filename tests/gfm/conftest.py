#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import dycov

RUN_WITHOUT_FIGURES = textwrap.dedent(
    '''
    """The command without the figures, which no test reads. Without the pool, no worker
    imports the module again and draws them anyway."""

    import sys

    from dycov.configuration.cfg import config
    from dycov.gfm.gfm import GridForming
    from dycov.launchers import dycov

    GridForming._plot = lambda *args, **kwargs: None
    config.set_value("Global", "parallel_pcs_validation", "false")
    sys.argv = ["dycov", *sys.argv[1:]]
    sys.exit(dycov())
    '''
)


@pytest.fixture(scope="session")
def matplotlib_cache(tmp_path_factory) -> Path:
    """The one font cache of every run of the session. A run that finds none, as under a new
    home, builds it again first, which on macOS takes longer than the run itself."""
    return tmp_path_factory.mktemp("matplotlib")


@pytest.fixture
def run_dycov(tmp_path, matplotlib_cache):
    """Runs dycov with the given arguments, as a user would, under the given home."""

    def run(*args: str, home: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c", RUN_WITHOUT_FIGURES, *args],
            env={
                **os.environ,
                "HOME": str(home),
                "USERPROFILE": str(home),
                "MPLCONFIGDIR": str(matplotlib_cache),
                "PYTHONPATH": str(Path(dycov.__file__).resolve().parents[1]),
            },
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=300,
        )

    return run
