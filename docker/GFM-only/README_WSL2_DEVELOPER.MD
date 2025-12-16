# Developer Guide: Exporting Dycov (GFM-only) as a Standalone Bundle

This guide explains how to package the **GFM-only** WSL environment (Dycov GFM + Internal Docker Engine) into a single `.tar` file. This allows end users to run the tool **without installing Docker Desktop** and without the heavy Dynawo dependencies.

## Phase 1: Prepare the Environment (WSL Side)

You must create a "clean" WSL distribution where Docker runs natively inside Linux.

### 1. Install Docker Native Engine
Open your WSL terminal (e.g., Ubuntu). Run the following to remove conflicts and install the official Docker Engine:

```bash
# 1. Uninstall conflicting packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done

# 2. Add Docker's official GPG key
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Install Docker
echo \
  "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. Configure Docker to Start
Ensure the service works inside WSL:

```bash
sudo service docker start
sudo usermod -aG docker $USER
```

*Note: You may need to log out and log back in for the group change to take effect.*

### 3. Build/Load the GFM-only Image
Ensure the `dycov-GFM-only:latest` image exists inside this local Docker engine.

```bash
# Navigate to the GFM-only directory
cd /path/to/repo/GFM-only

# Build the image using the provided script
./build.sh v0.8.1

# Verify presence
docker images
# You should see 'dycov-GFM-only' in the list
```

### 4. Setup Launch Scripts
Copy `run_dycov_docker.sh`, `start_dycov.sh`, and `import_image.sh` into a standard location (e.g., the home directory `~`) so the user finds them easily.

### 5. Sanitize the Environment
Before exporting, clean up temporary files to keep the bundle size small.

```bash
# Clean apt cache
sudo apt-get clean

# Clear command history
history -c
rm ~/.bash_history
```

## Phase 2: Export the Bundle (Windows Side)

1.  Open **PowerShell**.
2.  Determine your distribution name:
    ```powershell
    wsl --list --verbose
    ```
3.  Shutdown WSL to ensure data consistency:
    ```powershell
    wsl --shutdown
    ```
4.  Export the distribution to a file:
    ```powershell
    # Syntax: wsl --export <DistroName> <OutputFileName>
    wsl --export Ubuntu DycovGFMBundle.tar
    ```

**Result:** You now have `DycovGFMBundle.tar`. This is the file you will distribute.