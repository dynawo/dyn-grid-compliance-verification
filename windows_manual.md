
# dyn-grid-compliance-verification

## Overview
`dyn-grid-compliance-verification` is a tool designed to perform compliance verification using the Dynawo simulation platform. This guide provides detailed installation steps for setting up the tool on a Windows environment.

## Installation Guide

### Step 1: Install Required Tools

Before installing the `dyn-grid-compliance-verification` package, you need to ensure that your system has the required dependencies. Follow the instructions below to install them.

1. **Install Python 3**  
   Python 3 is required to run the tool. To install Python on your Windows machine:
   - Go to the [official Python website](https://www.python.org/downloads/).
   - Download the latest version of Python 3 (ensure that you select the option to add Python to the system PATH during installation).
   - To verify the installation, open a terminal and run:
     ```cmd
     python --version
     ```
     This should return the version of Python that you installed.

2. **Install Dynawo**  
   Dynawo is a simulation platform required by this tool. Follow the steps outlined in the official Dynawo installation guide at [Dynawo Installation Guide](https://dynawo.github.io/install/).
   - **Nightly Version**: Download the **Nightly version** of Dynawo from the repository to ensure you have the latest features and updates.
   - During installation, you will also need the following tools:
     - **CMake**: CMake is used to configure the build process for Dynawo. Download it from [cmake.org](https://cmake.org/download/).
     - **Visual Studio 2019**: Visual Studio is required to compile the code. You can download the free **Community Edition** from [here](https://visualstudio.microsoft.com/vs/older-downloads/). During the installation, select the "Desktop development with C++" workload.

3. **Install GitHub Desktop**  
   GitHub Desktop provides an easy way to clone repositories directly to your machine. To install it:
   - Go to [GitHub Desktop](https://desktop.github.com/).
   - Download and install it following the instructions on the website.
   - After installation, sign in to GitHub and proceed to clone the repository.

4. **Install LaTeX**  
   LaTeX is used for document processing. You can choose between two LaTeX distributions:
   - **MiKTeX**: Download it from [MiKTeX Download](https://miktex.org/download).
   - **TeX Live**: Download it from [TeX Live Download](https://www.tug.org/texlive/).
   
   > **Note**: You may need only the minimum set of LaTeX packages for this tool. (TODO: Define requirements). Be sure to select "Minimal installation" to avoid unnecessary packages.

### Step 2: Install the dyn-grid-compliance-verification Package

Once all required tools are installed, follow the steps below to install the `dyn-grid-compliance-verification` package.

1. **Clone the Repository**  
   The first step is to clone the repository to your local machine. Using GitHub Desktop:
   - Open GitHub Desktop and click **File** > **Clone repository**.
   - Enter the following URL to clone the repository:
     ```
     https://github.com/dynawo/dyn-grid-compliance-verification
     ```
   - Choose a local directory where you want to save the repository and click **Clone**.

2. **Set Up Virtual Environment**  
   A virtual environment is recommended to manage dependencies for the project. This ensures that the package uses the correct Python version and dependencies without affecting other projects on your system.
   - Open a **CMD terminal** (Command Prompt) as administrator.
   - Navigate to the root folder of the cloned repository using the `cd` command:
     ```cmd
     cd path	o\dyn-grid-compliance-verification
     ```
   - Create a new virtual environment with:
     ```cmd
     python3 -m venv dgcv_venv
     ```
   - This will create a directory `dgcv_venv` in your repository folder.

3. **Activate the Virtual Environment**  
   Now that the virtual environment is created, activate it to use the isolated environment:
   ```cmd
   dgcv_venv\Scripts\activate
   ```
   - Once activated, your terminal prompt should change to indicate that the virtual environment is active (e.g., `(dgcv_venv)` at the beginning of the prompt).
   
4. **Build the Package**  
   The next step is to compile the package into a distributable format:
   ```cmd
   python3 -m build
   ```
   - This command will create the necessary build files in the `dist` folder of the repository. The build process might take a few minutes to complete.

5. **Install the Package**  
   Once the package is built, you can install it using pip. Use the following command to install the `.whl` (Wheel) file generated during the build:
   ```cmd
   python3 -m pip install dist\dgcv....whl
   ```
   - This will install the package into your active virtual environment.

6. **Verify Installation**  
   After installation, verify that the tool was installed correctly by running the following command:
   ```cmd
   dgcv -h
   ```
   - This should display the help message for the `dyn-grid-compliance-verification` tool, confirming that the installation was successful.

7. **Pre-Execution Compilation**  
   Before running the tool for the first time, it's recommended to compile the tool's resources:
   ```cmd
   dgcv compile
   ```
   - This step ensures that all necessary files are generated and compiled for optimal performance.

### Ready to Use
Your installation is now complete, and you can start using the `dyn-grid-compliance-verification` tool. To begin, you can run again the following command to check the available commands:
```cmd
dgcv -h
```

---

For additional information, please refer to the project's [manual documentation](https://github.com/dynawo/dyn-grid-compliance-verification/tree/master/docs/manual).
