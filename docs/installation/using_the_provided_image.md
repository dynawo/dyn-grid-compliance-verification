# Installing DyCoV using the provided distribution image

**DyCoV version:** 1.1.0  
**Scope:** End‑user installation and execution of DyCoV using the prebuilt
distribution image (recommended installation method).

---

## 1. Overview

DyCoV is distributed as a **prebuilt Linux image** intended for end‑users.
This image provides a complete, self‑contained execution environment and
includes:

- DyCoV
- Dynawo
- Python
- uv
- LaTeX
- all required system dependencies

Using this image avoids any manual dependency installation and ensures
a controlled and reproducible environment.

The image is distributed as a single file:

- `dycov_rawimage.tar.gz`  
  *(Do not unzip this file manually.)*

Depending on your platform, the image can be used through different supported
methods, all described in this tutorial.

---

## 2. Supported usage modes

### Linux
- Using a container runtime (Docker or compatible)
- Recommended for servers or users who prefer isolated environments

### Windows
Two fully supported modes are available:
- **WSL installation (recommended)**
- **Docker Desktop installation**

Both rely on the same distribution image and provide identical functionality.

---

## 3. Linux — Docker installation

This method is recommended for Linux users who want to keep their system clean
and isolated.

### 3.1 Required files

Place the following files in the same directory:

- `dycov_rawimage.tar.gz`
- `import_image.sh`
- `run_dycov_docker.sh`

### 3.2 Grant execution permissions

```bash
chmod +x import_image.sh run_dycov_docker.sh
````

***

### 3.3 Import the image

```bash
./import_image.sh dycov_rawimage.tar.gz
```

This step restores the required container metadata.

***

### 3.4 Run DyCoV

Create a working directory for your studies and run DyCoV while mapping
your user ID to prevent permission issues on generated files:

```bash
mkdir my_project
./run_dycov_docker.sh -u $(id -u) -g $(id -g) my_project/
```

***

### 3.5 Sanity check

Inside the DyCoV session:

```bash
dycov -h
```

If the help is displayed, DyCoV is ready to use.

***

## 4. Windows — WSL installation (recommended)

In this mode, DyCoV is installed as a standalone WSL distribution.
Docker is **not required**.

### 4.1 Required files

Place all the following files in the same folder:

*   `dycov_rawimage.tar.gz`
*   `import_wsl.bat`
*   `import_wsl.ps1`
*   `run_dycov_wsl.ps1`

***

### 4.2 Standard procedure (recommended)

1.  Double‑click:

        import_wsl.bat

2.  The installer:
    *   imports the DyCoV distribution,
    *   creates a Desktop shortcut,
    *   creates a Start Menu entry.

3.  Launch DyCoV using the created shortcut (Desktop or Start Menu).

Inside the DyCoV session, Windows drives are accessible via:

*   `/mnt/c/`
*   `/mnt/d/`
*   …

***

### 4.3 Updating to a new version (WSL)

Each DyCoV release is a **complete standalone distribution**.
Updating replaces the existing installation entirely.

> **WARNING**
> The update process permanently deletes the existing `DycovApp` distribution,
> including any files stored inside it.
> Files stored on Windows drives (`C:\`, `D:\`, etc.) are **not** affected.

Before updating, move any important data to a Windows drive.
From inside the DyCoV session:

```bash
mv ~/my_results /mnt/c/Users/MyUser/Documents/
```

To update, place the new release files in a folder and run:

```
import_wsl.bat
```

The installer will detect the existing distribution and ask for confirmation
before replacing it.

---

### 4.4 Manual procedure (restricted environments)

If your organization restricts execution of `.bat` or `.ps1` scripts,
you can import the distribution manually.

From PowerShell or CMD, in the folder containing `dycov_rawimage.tar.gz`:

```powershell
wsl --import DycovApp C:\DycovApp .\dycov_rawimage.tar.gz
```

To start DyCoV manually:

```powershell
wsl -d DycovApp -- bash /start_dycov.sh
```

***

## 5. Windows — Docker Desktop installation

This method is intended for users comfortable with Docker tooling.

### 5.1 Import the image

Open PowerShell in the folder containing `dycov_rawimage.tar.gz`.

Define the required metadata:

```powershell
$DycovPath  = 'ENV PATH=\"/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"'
$DycovEntry = 'ENTRYPOINT [\"/start_dycov.sh\"]'
```

Import the image:

```powershell
docker import --change $DycovPath --change $DycovEntry .\dycov_rawimage.tar.gz dycov:latest
```

***

### 5.2 Run DyCoV

Launch the container and map your working directory:

```powershell
docker run --rm -it -v "${PWD}:/home/dycov_user" -w /home/dycov_user dycov:latest
```

***

### 5.3 Sanity check

Inside the container:

```bash
dycov -h
```

***

## 6. Data location and persistence

To ensure your work persists across updates:

*   On Windows: store projects on Windows drives and access them via `/mnt/c/...`
*   On Linux: use host directories mapped into the container

Avoid storing important data only inside the WSL distribution filesystem,
as WSL updates replace the entire distribution.

***

## 7. Alternative installation method

Installing DyCoV natively on Linux without using the distribution image is possible,
but intended for **advanced users only**.

This method requires manual installation of:

*   Python
*   uv
*   LaTeX
*   system dependencies

It is documented separately and is **not the recommended approach** for most users.

***

## 8. Next steps

Once DyCoV is running:

1.  Verify the installation:
    ```bash
    dycov -h
    ```
2.  Follow the **Quick start** tutorial.
3.  Continue with the workflow‑specific tutorials:
    *   Preparing inputs
    *   RMS model validation
    *   Electrical performance verification
    *   Grid‑Forming analysis