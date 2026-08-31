# Maintainer Guide: Building and Publishing a Release

This guide explains how to generate all distribution artifacts for a Dycov GitHub release
and what to upload once they are ready.

---

## Repository Structure

The installer-related files are organized as follows:

```
installers/
├── prepare_release.sh        # Release build script (run from the repo root)
├── linux_install.sh          # Linux native installer (end-user artifact)
├── README.md                 # Directory overview (points to the user docs)
├── RELEASING.md              # This file
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

The package version is derived from the Git tag by `setuptools_scm`; there is no version
number to edit by hand anywhere in the repository. This is why the release script requires
the tag to exist **before** it runs: it builds from the tagged commit and forces the same
version into the artifacts (`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_dycov`) so that installs
performed without the Git history still report the right version.

---

## Generating a Release

### 1. Create and push the tag first

```bash
git tag v0.9.3
git push origin v0.9.3
```

The build script refuses to run unless HEAD is exactly on the tag and the working tree is
clean.

### 2. Run the build script from the repository root

```bash
./installers/prepare_release.sh VERSION DYNAWO_DIR [--dry-run]
```

**Example:**
```bash
./installers/prepare_release.sh v0.9.3 /path/to/dynawo
```

`--dry-run` skips the Git checks (tag, HEAD, clean tree) and is only meant for testing the
script itself; everything else — including the Docker build — still runs.

**Requirements on the build machine:** `docker`, `zip`, and `uv` (used to create the
throw-away virtualenv for the manuals), plus a LaTeX toolchain for `make latexpdf`.

**What the script does, step by step:**

| Step | Action |
| :--- | :--- |
| 0 | Verifies the Git state (tag exists, HEAD on the tag, clean tree) and that every expected installer file is present. |
| 1 | Zips `DYNAWO_DIR` into `Dynawo_omc_v1.8.0.zip` and places it in the output directory. |
| 2 | Updates `version` in `pyproject.toml` (no-op today — the version is dynamic via `setuptools_scm`). |
| 3 | Copies `linux_install.sh` to the output directory, pinning `TARGET_BRANCH` to the tag, injecting the forced package version and setting `DYNAWO_SHA256SUM` to the checksum of the zip from Step 1. |
| 4 | Builds the user manual (`docs/manual`) in a temporary `uv` virtualenv: HTML and PDF. |
| 5 | Builds the Docker image (`dycov:latest` and `dycov:VERSION`) via `docker/build.sh`. |
| 6 | Exports the image to `dycov_rawimage.tar.gz` via `docker/export_image.sh`. |
| 7 | Collects all end-user artifacts into the output directory and zips `tools/dynawo_par` into `dycov_par_tool.zip`. |
| 8 | Removes the Docker images `dycov:latest` and `dycov:VERSION` from the local registry. |

**Output directory:** `./release_VERSION/`

**Manuals:** they are *not* copied into the output directory. They are left under
`docs/manual/build/` (`html/` and `latex/dycov.pdf`) — upload the PDF to the release if the
manual changed for this version.

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

1. **Create the GitHub release** from the tag and upload all files from `release_VERSION/`
   (plus `docs/manual/build/latex/dycov.pdf` if the manual is published with the release).
2. Verify that `linux_install.sh` can download `Dynawo_omc_v1.8.0.zip` from the new
   release URL before announcing the release publicly.
3. Note that the loose `*.sh` artifacts (`import_image.sh`, `run_dycov_docker.sh`,
   `linux_install.sh`) lose their exec bit when downloaded from GitHub; end users must run
   `chmod +x` first. This is documented in
   `docs/installation/using_the_provided_image.md` (section 3.2) and in the manual's
   usage/installation page.
