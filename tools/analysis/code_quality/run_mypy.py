import subprocess


def run_mypy():
    """
    Run mypy and return its stdout as a list of lines.
    Only invocation is handled here; parsing is done elsewhere.
    """
    cmd = [
        "uv",
        "run",
        "mypy",
        "src",
        "--disallow-untyped-defs",
        "--ignore-missing-imports",
        "--python-version",
        "3.10",
        "--show-error-codes",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.splitlines()
