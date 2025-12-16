# Developer Guide: Exporting Dycov as a Standalone WSL Bundle

This guide explains how to package the complete WSL environment (Dycov tool + Internal Docker Engine) into a single `.tar` file. This allows end users to run the tool **without installing Docker Desktop**.

## Phase 1: Prepare the Environment (WSL Side)

You must create a "clean" WSL distribution where Docker runs natively inside Linux, rather than relying on Docker Desktop integration.

### 1. Install Docker Native Engine
Open your WSL terminal (e.g., Ubuntu). Run the following to remove conflicts and install the official Docker Engine:

```bash
# 1. Uninstall conflicting packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done

# 2. Add Docker's official GPG key
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
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
Since WSL does not always start `systemd` services automatically, ensure the service works:

```bash
sudo service docker start
sudo usermod -aG docker $USER
```

*Note: You may need to log out and log back in for the group change to take effect.*

### 3. Build/Load the Dycov Image
Ensure the `dycov:latest` image exists inside this local Docker engine.

```bash
# Verify if the image is present
docker images

# If not, build it using the standard build script
./build.sh <TAG> <DYNAWO_HOST_PATH>
```

### 4. Setup Launch Scripts
Copy the `run_dycov_docker.sh` and `start_dycov.sh` scripts into a standard location within this Linux environment (e.g., `/opt/dycov/scripts` or the home directory) so the user finds them easily.

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
    wsl --export Ubuntu DycovBundle.tar
    ```

**Result:** You now have `DycovBundle.tar`. This is the file you will distribute to users who cannot use Docker Desktop.