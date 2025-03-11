# Generating the user manual

The user manual, as most of the documentation, is written using
[Sphinx](https://www.sphinx-doc.org).  To compile the manual into PDF and HTML,
essentially you need to set up a developer environment (see `build_and_install.sh -d`)
and run `make latexpdf && make html`. The next section describes the process step by step.


## Step by step

1. Clone the repository via: 
   ```bash
   git clone https://github.com/dynawo/dyn-grid-compliance-verification dycov_repo
   ```
   (you may of course use any name for the top-level directory, here `"dycov_repo"`.)

2. Get into the repository and run the shell script named `build_and_install.sh` in developer
   mode:
    ```bash
    ./build_and_install.sh -d
    ```
   This builds the Python package, creates a Python virtual environment under the
   subdirectory `dycov_venv`, and installs the package into it (together with all the
   necessary library dependencies, such as NumPy, etc., *and* the developer library
   dependencies, such as Sphinx, etc.).

3. Next, you must activate the virtual environment that has just been created: 
   ```bash
   source dycov_venv/bin/activate
   ```

4. Next, get into the manual directory (`docs/manual`) and run:
     * **`make latexpdf`** to obtain a PDF version (single file)
     * **`make html`** to obtain a HTML version (multiple files)


Sphinx creates a subdirectory `build`, in which we will find the HTML version of the manual
in the `build/html/` directory and the PDF version (`dycov.pdf`) in the `build/latex/`
directory.
   ```bash
   build
   ├── doctrees
   ├── html
   └── latex
   ```
