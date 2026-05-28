import re


def cross_check(methods, mypy_lines, pydoc_lines):
    """
    Cross-check AST inventory with mypy and pydocstyle outputs.

    Parameters
    ----------
    methods : list of dict
        Output of collect_public_methods()
    mypy_lines : list[str]
        mypy stdout lines
    pydoc_lines : list[str]
        pydocstyle stdout lines

    Returns
    -------
    list of dict
        Methods requiring action, enriched with:
        - typing_lines
        - docstring_lines
    """
    indexed = {}

    for m in methods:
        key = (m["file"], m["name"])
        indexed[key] = {
            **m,
            "typing_lines": [],
            "docstring_lines": [],
        }

    # mypy → missing typing (line-based)
    for line in mypy_lines:
        if "[no-untyped-def]" not in line:
            continue

        match = re.match(r"(.*\.py):(\d+):", line)
        if not match:
            continue

        file_, lineno = match.group(1), int(match.group(2))

        for data in indexed.values():
            if data["file"] == file_ and data["start"] <= lineno <= data["end"]:
                data["typing_lines"].append(lineno)

    # pydocstyle → missing docstring (name-based)
    for line in pydoc_lines:
        match = re.match(r"(.*\.py):(\d+) in public .* `([^`]+)`", line)
        if not match:
            continue

        file_, lineno, name = match.group(1), int(match.group(2)), match.group(3)
        key = (file_, name)

        if key in indexed:
            indexed[key]["docstring_lines"].append(lineno)

    return [m for m in indexed.values() if m["typing_lines"] or m["docstring_lines"]]
