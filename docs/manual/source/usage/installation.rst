===============================================
Installing Dynamic Grid Compliance Verification
===============================================

Overview
--------

Dynamic Grid Compliance Verification is written in `Python`__ and supports **Python
3.9+**. It builds upon the shoulders of many third-party libraries such as `lxml`__ and
`Jinja`__, which are installed when Dynamic Grid Compliance Verification is installed

__ https://docs.python-guide.org/
__ https://lxml.de/
__ https://jinja.palletsprojects.com/

System requirements
-------------------

The requirements at the OS-level are rather minimal: one just needs a recent Linux
distribution in which you should install a few packages, **LaTeX**, and **Python**. If
you do not have any strong preference, we would recommend Debian 12 or higher, as well
as Ubuntu 22.04 LTS or higher. The release of a Windows version is pending before the
end of 2024.

To be more specific, we explicitly list here the packages to be installed,
assuming a Debian/Ubuntu system:

* Install xdg-utils package, containing `xdg-open`, if the OS does not install it by default:
    .. code-block:: console

        apt install xdg-utils

* Install Dynawo (v1.7.0 or later) and its required packages:
    .. code-block:: console

        apt install curl unzip gcc g++ cmake

* Install these LaTeX packages:
    .. code-block:: console

       apt install texlive-base texlive-latex-base texlive-latex-extra \
               texlive-latex-recommended texlive-science texlive-lang-french \
               make latexmk

* Install a basic Python installation (version 3.9 or higher), containing at least `pip` and the `venv` module:
    .. code-block:: console

       apt install python3.9-minimal python3-pip python3.9-venv

Note that the tool itself is also a Python package. However, this package and
all of its dependencies (NumPy, etc.) will get installed at the user-level, i.e.,
inside the user's `$HOME` directory, under a *Python virtual environment*.



User Installation
-----------------

#. Choose a base directory of your choice and run the following command:

    .. code-block:: console

       curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.0.9/linux_install.sh | bash

   This script will install the DGCV tool, together with a matching version of Dynawo,
   under your current directory in $PWD/dgcv.  It will do so by cloning the latest
   stable release and building & installing the application (and all of its
   dependencies, such as NumPy, etc.) under a Python virtual environment.

#. Next, you must activate the virtual environment that has just been created:

    .. code-block:: console

       source $PWD/dgcv/activate_dgcv

#. The tool is used via a single command dgcv having several subcommands. Quickly check that your installation is working by running the help option, which will show you all available subcommands:

    .. code-block:: console

       dgcv -h

#. Upon the first use, the tool will automatically compile the Modelica models internally defined by the tool. You can also run this command explicitly, as follows:

    .. code-block:: console

	dgcv compile

 
.. note::
    The tool has a sanity check implemented to verify that all system requirements
    have been installed, notifying the user if any of them are missing.
