# Maintainer Guide: Building Distribution Artifacts

This guide explains how to generate the **single distribution artifact** (`dycov_rawimage.tar.gz`).

## The Strategy
We use `docker export` to create a generic filesystem tarball.
* **Pros:** Compatible with `wsl --import` (Windows Standalone).
* **Cons:** Strips Docker metadata. We rely on `import_image.sh` to restore metadata for Docker users.

---

## Generation Steps

1.  **Build the Image:**
    ```bash
    ./build.sh v1.0 /path/to/dynawo
    ```

2.  **Export the Filesystem:**
    Run the export script. This creates a temporary container, exports the filesystem, and zips it.
    ```bash
    ./export_image.sh
    ```

    **Output:** `dycov_rawimage.tar.gz`

---

## Release Checklist

Distribute the following files:
1.  **`dycov_rawimage.tar.gz`** (The main artifact).
2.  **`import_image.sh`** (Critical for Linux/Docker Desktop users).
3.  **`run_dycov_docker.sh`** (For Linux users).