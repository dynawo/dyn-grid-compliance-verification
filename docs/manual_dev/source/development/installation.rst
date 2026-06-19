.. _dev-setup:

===============================================
Setting up a development environment
===============================================

Working on DyCoV requires a few more steps than simply installing it as an
end user, but the process is straightforward. This section walks you through
everything you need: system dependencies, the Python environment, Dynawo, and
a first run of the test suite to confirm that everything is working.

The workflow described here is **native Linux only**. The Docker and WSL
installation methods are designed for end users and are not suitable for
development — you would not be able to iterate on the code effectively from
inside a container.


System requirements
-------------------

A recent Linux distribution is required. Debian 12 or Ubuntu 22.04 LTS (or
newer) are the recommended choices, though other distributions may work.

Before anything else, make sure the following packages are installed. They are
needed to build and run Dynawo, generate PDF reports, and manage the Python
environment.

Build tools:

.. code-block:: console

   sudo apt install git curl unzip gcc g++ cmake

LaTeX — DyCoV generates PDF compliance reports, so LaTeX must be available
even during development if you want to inspect the full output:

.. code-block:: console

   sudo apt install \
     texlive-base texlive-latex-base texlive-latex-extra \
     texlive-latex-recommended texlive-science texlive-lang-french \
     texlive-bibtex-extra biber latexmk

Python 3.13 — DyCoV requires Python 3.13 or newer:

.. code-block:: console

   sudo apt install python3.13 python3.13-venv git
   python3.13 --version

And finally, ``uv``, which handles the virtual environment and all dependency
management. DyCoV does not use ``pip`` or ``venv`` directly:

.. code-block:: console

   curl -LsSf https://astral.sh/uv/install.sh | sh


Dynawo
------

DyCoV relies on Dynawo to run RMS simulations, but in a development context
the tool does not install or manage Dynawo for you — that is your
responsibility as a developer. The most practical approach is to download a
precompiled **Dynawo nightly distribution**, which is the reference version
used for ongoing development and the one most likely to be compatible with the
current codebase.

If you prefer, you can also build Dynawo from source — refer to the
`Dynawo documentation <https://dynawo.github.io/>`_ for instructions on
either approach.

You do not need to add Dynawo to your system ``PATH``. If the Dynawo launcher
(``dynawo.sh``) is not on the path, simply tell DyCoV where to find it each
time using the ``-l`` flag:

.. code-block:: console

   dycov validate -l /path/to/dynawo/dynawo.sh ...


Getting the code
-----------------

Clone the repository into a local directory of your choice:

.. code-block:: console

   git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
   cd dycov_repo


Setting up the Python environment
-----------------------------------

Create a virtual environment using Python 3.13:

.. code-block:: console

   uv venv dycov_venv --python 3.13

Activate it:

.. code-block:: console

   source dycov_venv/bin/activate

Now install DyCoV in **editable mode** together with all development and test
dependencies:

.. code-block:: console

   uv pip install -e ".[dev,test]"

Editable mode means that any change you make to the source files under
``src/dycov/`` is reflected immediately the next time you run ``dycov`` —
no reinstallation needed.

The ``[dev,test]`` extras pull in everything you need to work on the codebase:

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Extra
     - Package
     - Purpose
   * - ``dev``
     - ``ruff``
     - Linting and code style enforcement
   * - ``dev``
     - ``sphinx``
     - Building the reference manuals locally
   * - ``test``
     - ``pytest``
     - Test runner
   * - ``test``
     - ``pytest-cov``
     - Coverage reporting
   * - ``test``
     - ``pytest-mock``
     - Mocking utilities

Check that everything installed correctly:

.. code-block:: console

   dycov --version


Running the tests
-----------------

DyCoV's test suite lives under ``tests/``. To run it:

.. code-block:: console

   uv run pytest -q

Or, with the virtual environment already activated:

.. code-block:: console

   pytest

Some tests require Dynawo to be correctly configured. If Dynawo is not
available in ``PATH``, those tests will fail or be skipped depending on the
test configuration. This is expected behavior and not an indication that
something is wrong with your setup.

CI also collects coverage data on every pull request:

.. code-block:: console

   uv run pytest --cov=src --cov-report=xml

There is no coverage gate yet — the coverage report is informational and
will not cause a build failure.


Building the manuals
--------------------

Both the user and developer manuals are built with Sphinx. With the virtual
environment active, get into the relevant directory and run ``make``:

.. code-block:: console

   # User manual
   cd docs/manual
   make latexpdf   # -> build/latex/dycov.pdf
   make html       # -> build/html/index.html

   # Developer manual
   cd docs/manual_dev
   make latexpdf   # -> build/latex/dycov-dev.pdf
   make html       # -> build/html/index.html

Both ``Makefile`` targets automatically run ``helps.py`` before invoking
Sphinx, so the CLI reference pages are always regenerated from the current
version of the tool before the manual is compiled.


Day-to-day workflow
--------------------

Once the environment is set up, a typical development loop looks like this:

1. Activate the environment if it is not already active:

   .. code-block:: console

      source dycov_venv/bin/activate

2. Make your changes under ``src/dycov/``.
3. Make sure Dynawo is reachable (either in ``PATH`` or via ``-l``).
4. Run DyCoV against one of the bundled examples to see the effect of your
   changes:

   .. code-block:: console

      dycov validate examples/Model/Wind/WECC4B/ReferenceCurves/ \
                     -m examples/Model/Wind/WECC4B/Dynawo/

5. Run the test suite and check for regressions:

   .. code-block:: console

      pytest -q

6. Check linting before committing:

   .. code-block:: console

      ruff check src

7. Iterate.