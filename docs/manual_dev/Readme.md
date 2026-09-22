# Generating the developer manual

The developer manual is written using [Sphinx](https://www.sphinx-doc.org).
It can be compiled into PDF and HTML once a developer environment is set up.

## Prerequisites

A developer environment must be set up following
[docs/developer/setup.md](../developer/setup.md).
In particular, the virtual environment must be activated and the `dev` extra
must be installed:

```bash
uv pip install -e ".[dev,test]"
source dycov_venv/bin/activate
```

## Building the manual

From the repository root, get into the developer manual directory and run the
desired targets:

```bash
cd docs/manual_dev
make latexpdf   # PDF version
make html       # HTML version
```

Sphinx creates a `build/` subdirectory with the following structure:

```text
build/
├── doctrees/
├── html/           # HTML version (open html/index.html in a browser)
└── latex/
    └── dycov-dev.pdf   # PDF version
```