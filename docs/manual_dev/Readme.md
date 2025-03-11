# Generate manual

Dynamic-grid-compliance-verification developer manual.

## Installation steps

1. Clone the repository via: 
   ```bash
   git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
   ```
   (you may of course use any name for the top-level directory, here `"dycov_repo"`.)

2. Cd into the repository and run the shell script named `build_and_install.sh` in developer
   mode. This builds the Python package, creates a Python virtual environment under the 
   subdirectory `dycov_venv`, and installs the package into it (together with all the necessary 
   library dependencies, such as NumPy, etc. and the developer library dependencies, such as 
   Sphinx, etc.).
    ```bash
        build_and_install.sh -d
    ```

3. Next, you must activate the virtual environment that has just been created: 
   ```bash
   source dycov_venv/bin/activate
   ```

## Compile the manual

Using Sphinx it is possible to compile the manual to obtain a PDF document and/or an HTML 
version of it. Steps to compile the developer manual:

1. Cd into the manual directory (`docs/manual_dev`).

2. Run the `Makefile` script to compile the developer manual.
   * Run **make latexpdf** to obtain a PDF file of the developer manual 
   * Run **make html** to obtain a HTML version of the developer manual 

3. Sphinx creates a subdirectory xxx, within which we find the HTML version of the manual 
   in the `build/html/` directory and/or the `dycov-dev.pdf` file in the 
   `build/latex/` directory.
   ```bash
   build
   ├── doctrees
   ├── html
   └── latex
   ```
