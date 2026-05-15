===============================================
Installing Dynamic grid Compliance Verification
===============================================

DyCoV is distributed as a self-contained package that bundles everything you
need: the tool itself, a compatible version of Dynawo, and the reference
manuals. The installation method depends on your platform and preferences.

All methods end up in the same place: a working ``dycov`` command, a copy of
the bundled examples ready to run, and the reference manuals available locally.


.. _install_linux_native:

Linux
-----

Native installation
^^^^^^^^^^^^^^^^^^^

This is the recommended method for Linux users. A single shell script handles
everything: it downloads Dynawo, clones the latest DyCoV release, and sets up
a Python virtual environment so that your system Python is left untouched.

Before running the installer, make sure the following system packages are
present. They are needed to compile and run Dynawo, generate PDF reports, and
manage the Python environment.

Build tools:

.. code-block:: console

   sudo apt install curl unzip gcc g++ cmake

LaTeX (for PDF report generation):

.. code-block:: console

   sudo apt install \
     texlive-base texlive-latex-base texlive-latex-extra \
     texlive-latex-recommended texlive-science texlive-lang-french \
     texlive-bibtex-extra biber latexmk

Python 3.13 and uv:

.. code-block:: console

   sudo apt install python3.13 python3.13-venv git
   curl -LsSf https://astral.sh/uv/install.sh | sh

Once the prerequisites are in place, choose a working directory and run:

.. code-block:: console

   curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/linux_install.sh | bash

The script will ask whether you want to download Dynawo (required for
simulation-based workflows), then proceed to install everything under
``$PWD/dycov``. It also builds the reference manuals so they are available
offline from the start.

When it finishes, activate the environment:

.. code-block:: console

   source $PWD/dycov/activate_dycov

You will need to run this activation command each time you open a new terminal
before using DyCoV. A quick way to check that everything is working:

.. code-block:: console

   dycov -h

After installation the reference manuals are at ``~/dycov/manual/``:

* ``manual/html/index.html`` — browse it in any web browser
* ``manual/dycov.pdf`` — the same content as a single PDF


.. _install_linux_docker:

Docker installation
^^^^^^^^^^^^^^^^^^^

If you prefer to keep DyCoV completely isolated from your system, the Docker
image is a good alternative. You will need Docker installed and running.

Download these three files and place them in the same directory:

* ``dycov_rawimage.tar.gz``
* ``import_image.sh``
* ``run_dycov_docker.sh``

Make them executable and import the image:

.. code-block:: console

   chmod +x import_image.sh run_dycov_docker.sh
   ./import_image.sh dycov_rawimage.tar.gz

From now on, create a directory for your work and launch DyCoV by mapping it
into the container. The ``-u`` and ``-g`` flags ensure that files written
inside the container are owned by your user:

.. code-block:: console

   mkdir my_project
   ./run_dycov_docker.sh -u $(id -u) -g $(id -g) my_project/

Once inside the session, the reference manuals are at ``~/manual/``.


.. _install_windows:

Windows
-------

WSL installation (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DyCoV on Windows runs inside WSL (Windows Subsystem for Linux), which gives
you a full Linux environment without a virtual machine. If WSL is not already
enabled on your system, open PowerShell as Administrator and run:

.. code-block:: console

   wsl --install

Or follow the `official Microsoft instructions <https://learn.microsoft.com/en-us/windows/wsl/install>`_.

Once WSL is available, download the following four files from the latest
release page and put them all in the same folder:

+-------------------------+--------------------------------------------------------------+
| File                    | Purpose                                                      |
+=========================+==============================================================+
| ``dycov_rawimage.tar.gz`` | The DyCoV distribution image. Do not unzip it manually.   |
+-------------------------+--------------------------------------------------------------+
| ``import_wsl.bat``      | The installer — double-click this to get started.            |
+-------------------------+--------------------------------------------------------------+
| ``import_wsl.ps1``      | The installation logic, called automatically by the .bat.    |
+-------------------------+--------------------------------------------------------------+
| ``run_dycov_wsl.ps1``   | The launcher, called automatically by the desktop shortcut.  |
+-------------------------+--------------------------------------------------------------+

Double-click ``import_wsl.bat``. The installer imports the DyCoV distribution
as a standalone WSL instance and creates a Desktop shortcut and a Start Menu
entry. From that point on, launching DyCoV is as simple as clicking the
shortcut.

Inside the DyCoV session your Windows drives are accessible as ``/mnt/c/``,
``/mnt/d/``, and so on. We recommend keeping your work files on a Windows
drive so they remain accessible outside the session.

Once inside the session, the reference manuals are at ``~/manual/``.

Restricted environments
"""""""""""""""""""""""

If your organization's security policy prevents running ``.bat`` or ``.ps1``
scripts, you can import the distribution manually. Open PowerShell or CMD
in the folder containing ``dycov_rawimage.tar.gz`` and run:

.. code-block:: console

   wsl --import DycovApp C:\DycovApp .\dycov_rawimage.tar.gz

Then start DyCoV with:

.. code-block:: console

   wsl -d DycovApp -- bash /start_dycov.sh

Updating to a new version
"""""""""""""""""""""""""

Each DyCoV release is a complete, self-contained distribution. Updating means
replacing the existing one entirely — there is no incremental update.

.. warning::
   Updating permanently deletes the existing ``DycovApp`` WSL distribution,
   including any files stored inside it. Files on your Windows drives are
   not affected.

Before updating, move anything you want to keep to a Windows drive:

.. code-block:: console

   mv ~/my_results /mnt/c/Users/MyUser/Documents/

Then place the new release files in a folder and double-click
``import_wsl.bat`` again. The installer will detect the existing distribution
and ask for confirmation before replacing it.


.. _install_windows_docker:

Docker Desktop installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For users already comfortable with Docker on Windows, the Docker image is
also available. Open PowerShell in the folder containing
``dycov_rawimage.tar.gz`` and define the metadata that was stripped during
the image export:

.. code-block:: console

   $DycovPath  = 'ENV PATH=\"/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"'
   $DycovEntry = 'ENTRYPOINT [\"/start_dycov.sh\"]'

Import the image:

.. code-block:: console

   docker import --change $DycovPath --change $DycovEntry .\dycov_rawimage.tar.gz dycov:latest

Launch a session mapped to your current directory:

.. code-block:: console

   docker run --rm -it -v "${PWD}:/home/dycov_user" -w /home/dycov_user dycov:latest

Verify the installation inside the container:

.. code-block:: console

   dycov -h