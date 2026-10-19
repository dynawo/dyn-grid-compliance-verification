import re
import subprocess
import warnings
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CURVES_RELEASE = EXAMPLES / ".curves-release"
HOW_TO_GET_THEM = (
    "    tools/scripts/fetch_example_curves.sh   (from the asset of a release)\n"
    "    tools/scripts/regenerate_curves.sh      (from the tool itself, with Dynawo)"
)


def _find_latest_dynawo(base_dir="/opt"):
    base = Path(base_dir)
    if not base.is_dir():
        return None

    # Look for directories matching the pattern Dynawo_vX.Y.Z_YYYYMMDD
    pattern = re.compile(r"Dynawo_v[\d\.]+_(\d{8})")

    candidates = []
    for d in base.iterdir():
        if d.is_dir():
            m = pattern.match(d.name)
            if m:
                date_str = m.group(1)  # YYYYMMDD
                candidates.append((date_str, d))

    if not candidates:
        return None

    # Select the most recent one using lexicographic order on YYYYMMDD
    candidates.sort(key=lambda x: x[0], reverse=True)

    latest_dir = candidates[0][1]
    dynawo_bin = latest_dir / "dynawo" / "dynawo.sh"

    if not dynawo_bin.exists():
        return None

    # Return the directory containing dynawo.sh
    return dynawo_bin.parent


@pytest.fixture(autouse=True)
def dynawo_latest(monkeypatch):
    """Set DYNAWOPATH to the latest Dynawo installation, when there is one. The tests that
    simulate skip themselves without it, and the ones that only compare curves do not need it."""
    latest_path = _find_latest_dynawo()
    if latest_path:
        monkeypatch.setenv("DYNAWOPATH", str(latest_path))
    return latest_path


def _directories_without_curves() -> list[Path]:
    """The curve directories of the examples that hold no curve. A directory that ships
    dictionaries is a directory whose curves should be there."""
    return sorted(
        {
            dictionary.parent
            for dictionary in EXAMPLES.rglob("*.dict")
            if not any(dictionary.parent.glob("*.csv"))
        }
    )


def _release_of_the_checkout() -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
            cwd=EXAMPLES.parent,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


@pytest.fixture(scope="session", autouse=True)
def example_curves():
    """The curves of the examples are not in the repository: they arrive with the asset of a
    release or with a regeneration. A test that needs them has to say so, and say which ones it
    is running on, because a verdict is a statement about a particular set of curves."""
    missing = _directories_without_curves()
    if missing:
        pytest.fail(
            "The examples have no curves in:\n"
            + "\n".join(f"    {directory}" for directory in missing)
            + "\nThey are not versioned. To get them:\n"
            + HOW_TO_GET_THEM,
            pytrace=False,
        )

    curves = CURVES_RELEASE.read_text(encoding="utf-8").strip() if CURVES_RELEASE.is_file() else ""
    release = _release_of_the_checkout()
    if curves and release and curves != release:
        warnings.warn(
            f"The curves are those of {curves} and this checkout descends from {release}: "
            "the verdicts asserted here are those of the curves the checkout expects.",
            stacklevel=1,
        )
    return curves
