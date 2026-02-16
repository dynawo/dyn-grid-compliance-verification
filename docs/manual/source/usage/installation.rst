===============================================
Installing Dynamic grid Compliance Verification
===============================================

Overview
--------

Dynamic grid Compliance Verification is written in `Python`__ and supports **Python
3.9+**. It builds upon the shoulders of many third-party libraries such as `lxml`__ and
`Jinja`__, which are installed when Dynamic grid Compliance Verification is installed

__ https://docs.python-guide.org/
__ https://lxml.de/
__ https://jinja.palletsprojects.com/

System requirements
-------------------

Linux
^^^^^

The requirements at the OS-level are rather minimal: one just needs a recent Linux
distribution in which you should install a few packages, **LaTeX**, and **Python**. If
you do not have any strong preference, we would recommend Debian 12 or higher, as well
as Ubuntu 22.04 LTS or higher.

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

* Install a basic Python installation (version 3.9 or higher), containing at least `pip` and the `venv` module.:
    .. code-block:: console

       apt install python3.9-minimal python3-pip python3.9-venv

Note that the tool itself is also a Python package. However, this package and
all of its dependencies (NumPy, etc.) will get installed at the user-level, i.e.,
inside the user's `$HOME` directory, under a *Python virtual environment*.


Windows
^^^^^^^

.. note::
    The windows installer (described in the next section) will install all of these
    system requirements, so you may skip this section. It is only here for your information.

The requirements at the OS-level are rather minimal: one just needs a recent Windows
distribution in which you should install a few packages, **LaTeX**, and **Python**. If
you do not have any strong preference, we would recommend Windows 10 or higher. 

To be more specific, we explicitly list here the packages to be installed:

* Install Dynawo (v1.7.0 or later) and its required packages:
   Dynawo is a simulation platform required by this tool. Follow the steps outlined in the official Dynawo installation guide at `Dynawo Installation Guide <https://dynawo.github.io/install/>`_.
   - **Nightly Version**: Download the **Nightly version** of Dynawo from the repository to ensure you have the latest features and updates.
   - During installation, you will also need the following tools:
     - **CMake**: CMake is used to configure the build process for Dynawo. Download it from `cmake.org <https://cmake.org/download/>`_.
     - **Visual Studio 2019**: Visual Studio is required to compile the code. You can download the free **Community Edition** from `here <https://visualstudio.microsoft.com/vs/older-downloads/>`. During the installation, select the "Desktop development with C++" workload.

* Install these LaTeX packages:
   LaTeX is used for document processing. You can choose between two LaTeX distributions:
   - **MiKTeX**: Download it from `MiKTeX Download <https://miktex.org/download>`.
   - **TeX Live**: Download it from `TeX Live Download <https://www.tug.org/texlive/>`.

* Install a basic Python installation (version 3.9 or higher), containing at least `pip` and the `venv` module:
   - Go to the `official Python website <https://www.python.org/downloads/>`_.
   - Download the latest version of Python 3 (ensure that you select the option to add Python to the system PATH during installation).
   - To verify the installation, open a terminal and run:

Note that the tool itself is also a Python package. However, this package and
all of its dependencies (NumPy, etc.) will get installed under a 
*Python virtual environment*.



User Installation
-----------------

Linux
^^^^^

#. Choose a base directory of your choice and run the following command:

    .. code-block:: console

       curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/linux_install.sh | bash

   This script will install the DyCoV tool, together with a matching version of Dynawo,
   under your current directory in $PWD/dycov.  It will do so by cloning the latest
   stable release and building & installing the application (and all of its
   dependencies, such as NumPy, etc.) under a Python virtual environment.

#. Next, you must activate the virtual environment that has just been created:

    .. code-block:: console

       source $PWD/dycov/activate_dycov

#. The tool is used via a single command dycov having several subcommands. Quickly check that your installation is working by running the help option, which will show you all available subcommands:

    .. code-block:: console

       dycov -h

#. Upon the first use, the tool will automatically compile the Modelica models internally defined by the tool. You can also run this command explicitly, as follows:

    .. code-block:: console

	dycov compile

 
.. note::
    The tool has a sanity check implemented to verify that all system requirements
    have been installed, notifying the user if any of them are missing.


Windows
^^^^^^^

#. Download the `DyCoV's Windows Installer`__.

__ https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v0.9.2/DyCoV_win_Installer.exe

   In order to install the application, it is essential that the user has administrator rights. 
   If the user is an administrator, there are no problems in unblocking the executable:
   
    .. image:: figs_installation/admin.png
    :width: 70%
    :alt: Unblocking Executable
    :align: center


#. Next, execute the downloaded installer:

   This executable will install the DyCoV tool, together with a matching version of Dynawo,
   under the selected directory (default installation path: `c:/dycov`).  It will do this 
   by copying the latest stable version and compiling and installing the application (and 
   all its dependencies, such as NumPy, etc.) into a Python virtual environment. The 
   installer will also install any third-party applications required for the proper 
   functioning of the tool.

.. note::
    The MikTex installer allows you to select the configuration that you want to apply. 
    For the tool to work correctly, you must select the "Yes" or "Ask me first" option on the 
    following screen:
    .. image:: figs_installation/miktex_settings.png
    :width: 70%
    :alt: MikTex Installer Settings
    :align: center


#. Next, you must activate the virtual environment that has just been created by double-clicking on the DyCoV.bat file that has been created on the desktop.

    This action will open a new Command Prompt with the virtual environment activated where the tool can be used.
    To finish using the tool, you only need to close the Command Prompt.

#. The tool is used via a single command dycov having several subcommands. Quickly check that your installation is working by running the help option, which will show you all available subcommands:

    .. code-block:: console

       dycov -h

#. Upon the first use, the tool will automatically compile the Modelica models internally defined by the tool. You can also run this command explicitly, as follows:

    .. code-block:: console

	dycov compile

.. note::
    The installer will perform a basic installation of the **MiKTeX** distribution. The 
    first time you use the tool, **MiKTeX** will install any additional packages it needs 
    to generate the report, so it may take a few minutes for the report to be generated.
 
.. note::
    The tool has a sanity check implemented to verify that all system requirements
    have been installed, notifying the user if any of them are missing.
