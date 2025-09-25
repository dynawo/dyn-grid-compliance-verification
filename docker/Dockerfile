# Dockerfile for containerizing the Dynamic grid compliance validation tool.
# This version is optimized to use 'uv' for faster builds.
#
# To build the Docker image:
#   docker build -t dycov:latest .
#
# (c) 2022 RTE
# Developed by Grupo AIA

FROM debian:bullseye-slim

ARG DWO_ZIP=Dynawo_omc_V1.4.0.zip

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/dycov_venv/bin:/opt/dynawo:${PATH}"

# First layer: Install system dependencies and Dynawo
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    texlive-base \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-science \
    texlive-lang-french \
    biber \
    make \
 && curl -sSOL https://github.com/dynawo/dynawo/releases/download/nightly/"$DWO_ZIP" \
 && unzip -q "$DWO_ZIP" -d /opt \
 && rm "$DWO_ZIP" \
 && apt-get-purge -y curl unzip \
 && rm -rf /var/lib/apt/lists/*

# Second layer: Set up Python environment with uv
RUN python3 -m venv /opt/dycov_venv
RUN /opt/dycov_venv/bin/pip install --no-cache-dir --upgrade uv

# Third layer: Copy only necessary files and install dependencies
# This leverages Docker's layer caching.
COPY pyproject.toml README.md /app/
WORKDIR /app
RUN uv pip install --no-cache-dir --system .

# Fourth layer: Copy the rest of the source code
COPY src/ /app/src/

# Entrypoint and default command can be set here if needed,
# or handled by the run script.
CMD ["dycov", "--help"]