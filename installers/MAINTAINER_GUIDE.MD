# Maintainer Guide: Building and Publishing a Release

This guide explains how to generate all distribution artifacts for a Dycov GitHub release
and what to upload once they are ready.

---

## Repository Structure

The installer-related files are organized as follows:

```
installers/
├── linux_install.sh          # Linux native installer (end-user artifact)
├── README.MD                 # End-user installation guide
├── MAINTAINER_GUIDE.MD       # This file
├── docker/
│   ├── Dockerfile            # Image definition
│   ├── build.sh              # Builds the Docker image
│   ├── export_image.sh       # Exports the image as a flat tarball (WSL-compatible)
│   ├── import_image.sh       # End-user artifact: imports the image on Linux/Docker
│   ├── run_dycov_docker.sh   # End-user artifact: launches the container on Linux
│   └── start_dycov.sh        # Entrypoint script embedded in the image
└── wsl/
    ├── import_wsl.bat        # End-user artifact: double-click installer for Windows WSL
    ├── import_wsl.ps1        # Installation logic called by import_wsl.bat
    └── run_dycov_wsl.ps1     # End-user artifact: launcher called by the desktop shortcut
```

---

## The Release Strategy

The distribution is built around a single artifact: `dycov_rawimage.tar.gz`.

This file is generated via `docker export` (not `docker save`), which produces a flat
filesystem tarball compatible with both `wsl --import` (Windows Standalone) and
`docker import` (Linux/Windows Docker). The downside is that Docker metadata
(ENV, ENTRYPOINT) is stripped — `import_image.sh` restores it for Docker users,
while `run_dycov_wsl.ps1` calls the entrypoint explicitly for WSL users.

---

## Generating a Release

All steps are automated by a single script at the root of the repository:

```bash
./prepare_release.sh VERSION DYNAWO_DIR
```

**Example:**
```bash
./prepare_release.sh v0.9.3 /path/to/dynawo
```

**What the script does, step by step:**

| Step | Action |
| :--- | :--- |
| 1 | Zips `DYNAWO_DIR` into `Dynawo_omc_v1.8.0.zip` and places it in the output directory. |
| 2 | Updates `version` in `pyproject.toml` to match `VERSION`. |
| 3 | Copies `linux_install.sh` to the output directory, updating `TARGET_BRANCH` and `DYNAWO_SHA256SUM`. |
| 4 | Builds the Docker image (`dycov:latest` and `dycov:VERSION`) via `docker/build.sh`. |
| 5 | Exports the image to `dycov_rawimage.tar.gz` via `docker/export_image.sh`. |
| 6 | Collects all end-user artifacts into the output directory. |
| 7 | Removes the Docker images `dycov:latest` and `dycov:VERSION` from the local registry. |

**Output directory:** `./release_VERSION/`

---

## Release Artifacts

After running `prepare_release.sh`, the output directory contains all files to upload
to the GitHub release:

| File | Used by |
| :--- | :--- |
| `dycov_rawimage.tar.gz` | Methods 1, 2, 4 (WSL and Docker) |
| `import_wsl.bat` | Method 1 (Windows WSL) |
| `import_wsl.ps1` | Method 1 (Windows WSL) |
| `run_dycov_wsl.ps1` | Method 1 (Windows WSL) |
| `import_image.sh` | Method 4 (Linux Docker) |
| `run_dycov_docker.sh` | Method 4 (Linux Docker) |
| `linux_install.sh` | Method 3 (Linux Native) |
| `Dynawo_omc_v1.8.0.zip` | Method 3 (Linux Native, downloaded automatically by `linux_install.sh`) |
| `dycov_par_tool.zip` | Standalone Dynawo PAR utility (also bundled inside every install method) |

The standalone Dynawo PAR utility (`tools/dynawo_par`) is shipped to end users by
every install method — it is copied into `~/tools/dynawo_par` in the Docker/WSL
image (via `start_dycov.sh`) and into `<install_dir>/tools/dynawo_par` by
`linux_install.sh`. `dycov_par_tool.zip` is additionally provided as a direct
download for users who only want the script. Being dependency-free (standard
library only), it runs with any Python 3 — e.g.
`python tools/dynawo_par/generate_par.py --excel <file.xlsx>`.

---

## Post-Release Checklist

1. **Commit and push** the `pyproject.toml` change before creating the GitHub release
   (the script reminds you of this at the end).
2. **Create the Git tag** matching `VERSION` (e.g., `v0.9.3`) and push it.
3. **Create the GitHub release** from that tag and upload all files from `release_VERSION/`.
4. Verify that `linux_install.sh` can download `Dynawo_omc_v1.8.0.zip` from the new
   release URL before announcing the release publicly.