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

The requirements at the OS-level are rather minimal: one just needs a recent Linux or Windows
distribution in which you should install a few packages, **LaTeX**, and **Python**. If
you do not have any strong preference, we would recommend Debian 12 or higher, as well
as Ubuntu 22.04 LTS or higher. In the case of Windows, we recommend using Windows 10.

Installation for Linux
------------------------

To be more specific, we explicitly list here the packages to be installed, assuming a
Debian/Ubuntu system:

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


	
Installation for Linux developers
---------------------------

#. Clone the repository via:

    .. code-block:: console

       git clone https://github.com/dynawo/dyn-grid-compliance-verification dgcv_repo
       
   (You may of course use any name for the top-level directory, here "dgcv_repo")
   
#. Get into the repository and run the shell script named build_and_install.sh. This builds the Python package, creates a Python virtual environment under the subdirectory dgcv_venv, and installs the package into it (together with all the necessary library dependencies, such as NumPy, etc.).

#. Next, you must activate the virtual environment that has just been created:

    .. code-block:: console
    
    	source dgcv_venv/bin/activate

#. The tool is used via a single command dgcv having several subcommands. Quickly check that your installation is working by running the help option, which will show you all available subcommands:

    .. code-block:: console

       dgcv -h

#. Upon the first use, the tool will automatically compile the Modelica models internally defined by the tool. You can also run this command explicitly, as follows:

    .. code-block:: console

	dgcv compile
 
.. note::
    The tool has a sanity check implemented to verify that all system requirements
    have been installed, notifying the user if any of them are missing.



Installation for Windows
------------------------


**Step 1: Install Required Tools**


Before installing the `dyn-grid-compliance-verification` package, you need to ensure that your system has the required dependencies. Follow the instructions below to install them.

1. **Install Python 3**  
   Python 3 is required to run the tool. To install Python on your Windows machine:
   - Go to the `official Python website <https://www.python.org/downloads/>`_.
   - Download the latest version of Python 3 (ensure that you select the option to add Python to the system PATH during installation).
   - To verify the installation, open a terminal and run:
    
   .. code-block:: console

	python.exe --version
      


   This should return the version of Python that you installed.

2. **Install Dynawo**  
   Dynawo is a simulation platform required by this tool. Follow the steps outlined in the official Dynawo installation guide at `Dynawo Installation Guide <https://dynawo.github.io/install/>`_.
   - **Nightly Version**: Download the **Nightly version** of Dynawo from the repository to ensure you have the latest features and updates.
   - During installation, you will also need the following tools:
     - **CMake**: CMake is used to configure the build process for Dynawo. Download it from `cmake.org <https://cmake.org/download/>`_.
     - **Visual Studio 2019**: Visual Studio is required to compile the code. You can download the free **Community Edition** from `here <https://visualstudio.microsoft.com/vs/older-downloads/>`. During the installation, select the "Desktop development with C++" workload.

3. **Install GitHub Desktop**  
   GitHub Desktop provides an easy way to clone repositories directly to your machine. To install it:
   - Go to `GitHub Desktop <https://desktop.github.com/>`.
   - Download and install it following the instructions on the website.
   - After installation, sign in to GitHub and proceed to clone the repository.

4. **Install LaTeX**  
   LaTeX is used for document processing. You can choose between two LaTeX distributions:
   - **MiKTeX**: Download it from `MiKTeX Download <https://miktex.org/download>`.
   - **TeX Live**: Download it from `TeX Live Download <https://www.tug.org/texlive/>`.
   
   > **Note**: You may need only the minimum set of LaTeX packages for this tool. (TODO: Define requirements). Be sure to select "Minimal installation" to avoid unnecessary packages.


**Step 2: Install the dyn-grid-compliance-verification Package**


Once all required tools are installed, follow the steps below to install the `dyn-grid-compliance-verification` package.

1. **Clone the Repository**  
   The first step is to clone the repository to your local machine. Using GitHub Desktop:
   - Open GitHub Desktop and click **File** > **Clone repository**.
   - Enter the following URL to clone the repository:
         
   .. code-block:: console

     git clone https://github.com/dynawo/dyn-grid-compliance-verification
     
   - Choose a local directory where you want to save the repository and click **Clone**.

2. **Set Up Virtual Environment**  
   A virtual environment is recommended to manage dependencies for the project. This ensures that the package uses the correct Python version and dependencies without affecting other projects on your system.
   - Open a **CMD terminal** (Command Prompt) as administrator.
   - Navigate to the root folder of the cloned repository using the `cd` command:
         
   .. code-block:: console

     cd path-to-repo\dyn-grid-compliance-verification

   - Create a new virtual environment with:
         
   .. code-block:: console

     python.exe -m venv dgcv_venv
     
   - This will create a directory `dgcv_venv` in your repository folder.
   
3. **Build the Package**  
   The next step is to compile the package into a distributable format:
       
   .. code-block:: console

   	python.exe -m build
   
   - This command will create the necessary build files in the `dist` folder of the repository. The build process might take a few minutes to complete.

4. **Activate the Virtual Environment**  
   Now that the virtual environment is created, activate it to use the isolated environment:
       
   .. code-block:: console

   	dgcv_venv\Scripts\activate
   
   - Once activated, your terminal prompt should change to indicate that the virtual environment is active (e.g., `(dgcv_venv)` at the beginning of the prompt).

5. **Install the Package**  
   Once the package is built, you can install it using pip. Use the following command to install the `.whl` (Wheel) file generated during the build:
       
   .. code-block:: console

   	python.exe -m pip install dist\dgcv....whl
   
   - This will install the package into your active virtual environment.

6. **Verify Installation**  
   After installation, verify that the tool was installed correctly by running the following command:
       
   .. code-block:: console

   	dgcv -h
   
   - This should display the help message for the `dyn-grid-compliance-verification` tool, confirming that the installation was successful.

7. **Pre-Execution Compilation**  
   Before running the tool for the first time, it's recommended to compile the tool's resources:
       
   .. code-block:: console

   	dgcv compile
   
   - This step ensures that all necessary files are generated and compiled for optimal performance.

Ready to Use
------------
Your installation is now complete, and you can start using the `dyn-grid-compliance-verification` tool. To begin, you can run again the following command to check the available commands:
    
   .. code-block:: console

	dgcv -h


---

For additional information, please refer to the project's `manual documentation <https://github.com/dynawo/dyn-grid-compliance-verification/tree/master/docs/manual>`.
