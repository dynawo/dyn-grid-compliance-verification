# Native Linux installation of DyCoV (advanced)

**DyCoV version:** 1.1.0  
**Scope:** Native installation of DyCoV on Linux systems without using the
prebuilt distribution image.

> ⚠️ **Important**
>
> This installation method is intended for **advanced users only**.
>
> For most users, the **recommended installation method** is to use the
> **prebuilt distribution image**, which provides a fully self‑contained
> execution environment.

---

## 1. Overview

DyCoV can be installed directly on a native Linux system without using the
prebuilt distribution image.

In this mode:
- DyCoV is installed as a **Python application** inside a user‑level virtual
  environment.
- A compatible version of **Dynawo is automatically downloaded and installed**
  by the DyCoV installer.
- The user is responsible for installing all **system‑level prerequisites**
  required by the installation process.

This approach offers greater flexibility but requires manual system preparation
and maintenance by the user.

---

## 2. Supported systems

A recent Linux distribution is required.

Recommended distributions:
- Debian 12 or newer
- Ubuntu 22.04 LTS or newer

Other distributions may work but are not explicitly supported.

---

## 3. System requirements

The following system packages are required to run the **DyCoV native installer**.

They are needed by the installation process, which automatically downloads and
installs a compatible version of Dynawo.  
Users are **not expected to install Dynawo manually**.

The instructions below assume a Debian‑based system (Debian or Ubuntu).

---

### 3.1 System build tools

These packages are required during the Dynawo installation step performed by
the DyCoV installer.

```bash
sudo apt install curl unzip gcc g++ cmake
````

***

### 3.2 LaTeX packages

DyCoV generates PDF reports and therefore requires LaTeX to be installed on the
system.

```bash
sudo apt install \
  texlive-base \
  texlive-latex-base \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-science \
  texlive-lang-french \
  latexmk
```

***

### 3.3 Python (≥ 3.13) and uv

DyCoV **requires Python version 3.13 or newer**.

Install a minimal Python environment and Git:

```bash
sudo apt install python3.13 python3.13-venv git
```

Ensure that Python 3.13 is the default `python3` interpreter or explicitly
available in your environment:

```bash
python3.13 --version
```

Install **uv**, which is used to manage the Python virtual environment and
dependencies:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **Note**
>
> `pip` and `venv` are not required directly.
> All Python package management is handled by `uv`.

***

## 4. Installation procedure

### 4.1 Choose an installation directory

Choose a base directory where DyCoV will be installed:

```bash
mkdir dycov_install
cd dycov_install
```

***

### 4.2 Run the native installer

Run the official native Linux installer:

```bash
curl -L https://github.com/dynawo/dyn-grid-compliance-verification/releases/latest/download/linux_install.sh | bash
```

This installer will:

*   download and install a compatible version of Dynawo (after user confirmation),
*   clone the latest stable DyCoV release,
*   create a Python virtual environment using **Python 3.13** via `uv`,
*   install DyCoV and all its Python dependencies inside that environment.

The installation is performed under:

```text
$PWD/dycov
```

***

## 5. Environment activation

After installation, the generated environment **must be activated** before
using DyCoV.

Activate the environment using the wrapper script:

```bash
source dycov/activate_dycov
```

This step ensures that:

*   the Python 3.13 virtual environment is active,
*   Dynawo binaries installed by the installer are available in the system `PATH`.

***

## 6. Sanity check

Verify that DyCoV is correctly installed:

```bash
dycov -h
```

If the help message is displayed, the installation is complete.

***

## 7. Using DyCoV

Once the environment is activated, DyCoV is available through the command:

```bash
dycov
```

You can now follow:

*   the **Quick start** tutorial,
*   and the workflow‑specific tutorials:
    *   Preparing inputs
    *   RMS model validation
    *   Electrical performance verification
    *   Grid‑Forming analysis

***

## 8. Maintenance and updates

In native installation mode:

*   updates require re‑running the installer,
*   all system dependencies (including Python 3.13) remain the user’s responsibility,
*   multiple DyCoV installations may coexist in different directories.

For easier upgrades and a fully controlled runtime environment, the
**prebuilt distribution image** remains the recommended approach.

***

## 9. When to use this method

Native Linux installation may be appropriate if you:

*   work exclusively on Linux,
*   are comfortable managing system packages and Python versions,
*   specifically require Python 3.13 on the host system,
*   need full control over the execution environment,
*   or are performing advanced debugging or development tasks.

Otherwise, prefer the installation using the **prebuilt distribution image**.

