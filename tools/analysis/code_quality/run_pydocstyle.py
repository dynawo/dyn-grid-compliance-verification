import subprocess


def run_pydocstyle():
    """
    Run pydocstyle and return its stdout as a list of lines.
    Only missing public docstrings (D102, D103) are checked.
    """
    cmd = [
        "uv",
        "run",
        "pydocstyle",
        "src",
        "--select=D102,D103",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.splitlines()
