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

### 1. Regenerate the example curves

The reference and producer curves under `examples/Model` are regenerated once per release, and
this is where it belongs: any fix that moves a verdict invalidates the curves shipped with the
previous release, so they are regenerated after the last fix that goes into the release and
before the tag.

```bash
./tools/scripts/regenerate_curves.sh
```

That single command covers the 17 Model examples: it runs each of them in a home directory of
its own, so that no local configuration filters what is verified, anonymizes the results and
replaces every CSV under their `ReferenceCurves` directories and under
`examples/Model/ProducerCurves`. It needs the virtualenv active and a Dynawo launcher
(`-l` selects another one), and it runs every test of every example, so it is the longest step
of a release. See [../tools/scripts/README.md](../tools/scripts/README.md) for its options.

Read its guard before trusting the outcome: the command compares the tests the run executed
against those the PCS of the examples declare, and stops without touching the repository when
they differ, because half a regeneration is worse than none. Commit the curves it replaced
before tagging: the build script refuses to run with a dirty working tree.

### 2. Create and push the tag

```bash
git tag v0.9.3
git push origin v0.9.3
```

The build script refuses to run unless HEAD is exactly on the tag and the working tree is
clean.

### 3. Run the build script from the repository root

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
| 2 | Copies `linux_install.sh` to the output directory, pinning `TARGET_BRANCH` to the tag and setting `DYNAWO_SHA256SUM` to the checksum of the zip from Step 1. |
| 3 | Builds the user manual (`docs/manual`) in a temporary `uv` virtualenv: HTML and PDF. |
| 4 | Builds the Docker image (`dycov:latest` and `dycov:VERSION`) via `docker/build.sh`. |
| 5 | Exports the image to `dycov_rawimage.tar.gz` via `docker/export_image.sh`. |
| 6 | Collects all end-user artifacts into the output directory. |
| 7 | Removes the Docker images `dycov:latest` and `dycov:VERSION` from the local registry. |

**Output directory:** `./release_VERSION/`

**Manuals:** they are *not* release artifacts and are *not* copied into the output directory.
They are built because the image needs them, and they are left under
`docs/manual/build/` (`html/` and `latex/dycov.pdf`), where the Docker build picks them up.
End users get them either inside the image (`~/manual/`) or compiled by `linux_install.sh`
(`<install_dir>/manual/`), so there is nothing to upload.

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

---

## Post-Release Checklist

1. **Create the GitHub release** from the tag and upload all eight files from `release_VERSION/`.
2. Verify that `linux_install.sh` can download `Dynawo_omc_v1.8.0.zip` from the new
   release URL before announcing the release publicly.
3. Note that `import_image.sh` and `run_dycov_docker.sh` lose their exec bit when downloaded
   from GitHub; end users must run `chmod +x` first, as documented in
   `docs/installation/using_the_provided_image.md` (section 3.2). `linux_install.sh` does not
   need it: the installation docs pipe it straight into `bash`.

---

## Why DyCoV is not on PyPI

Publishing to PyPI is deliberately out of scope for now: the package alone is
not usable without Dynawo and a LaTeX toolchain, so the supported distribution
channels are the prebuilt image and the Linux native installer, both attached
to each GitHub release.
