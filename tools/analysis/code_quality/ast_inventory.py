import ast
from pathlib import Path

SRC_ROOT = Path("src")


def collect_public_methods():
    """
    Collect all public functions and public class methods from the src/ tree.

    Returns
    -------
    list of dict
        Each dict contains:
        - file: path to file
        - name: function or Class.method name
        - start: start line number
        - end: end line number
    """
    methods = []

    for pyfile in SRC_ROOT.rglob("*.py"):
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))

        for node in tree.body:
            # Public functions
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                methods.append(
                    {
                        "file": pyfile.as_posix(),
                        "name": node.name,
                        "start": node.lineno,
                        "end": node.end_lineno,
                    }
                )

            # Public methods in public classes
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                        methods.append(
                            {
                                "file": pyfile.as_posix(),
                                "name": f"{node.name}.{item.name}",
                                "start": item.lineno,
                                "end": item.end_lineno,
                            }
                        )

    return methods
