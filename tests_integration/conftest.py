import re
from pathlib import Path

import pytest


def _find_latest_dynawo(base_dir="/opt"):
    base = Path(base_dir)

    # Buscar directorios que sigan el patrón Dynawo_vX.Y.Z_YYYYMMDD
    pattern = re.compile(r"Dynawo_v[\d\.]+_(\d{8})")

    candidates = []
    for d in base.iterdir():
        if d.is_dir():
            m = pattern.match(d.name)
            if m:
                date_str = m.group(1)  # YYYYMMDD
                candidates.append((date_str, d))

    if not candidates:
        raise RuntimeError(f"No Dynawo installations found in {base_dir}")

    # Elegir el más reciente por orden lexicográfico YYYYMMDD
    candidates.sort(key=lambda x: x[0], reverse=True)

    latest_dir = candidates[0][1]
    dynawo_bin = latest_dir / "dynawo" / "dynawo.sh"

    if not dynawo_bin.exists():
        raise RuntimeError(f"dynawo.sh not found in: {dynawo_bin}")

    return dynawo_bin.parent  # el directorio donde está dynawo.sh


@pytest.fixture
def dynawo_latest(monkeypatch):
    """Set DYNAWOPATH to the latest Dynawo installation."""
    latest_path = _find_latest_dynawo()
    monkeypatch.setenv("DYNAWOPATH", str(latest_path))
    return latest_path
