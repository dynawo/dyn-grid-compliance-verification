# Dockerfile for containerizing the Dycov tool (GFM-only version).
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

FROM python:3.11-slim-bookworm

ARG dycov_PKG=dycov-0.8.1-py3-none-any.whl
ARG dycov_EXAMPLES=examples

ENV DEBIAN_FRONTEND=noninteractive
# Add uv's install directory to the PATH
ENV PATH="/root/.local/bin:${PATH}"

# First layer:
#   - Update the base debian dist.
#   - Install required deb dependencies.
#   - Install uv.
RUN apt-get update && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl unzip rsync \
     texlive-base texlive-latex-base texlive-latex-extra texlive-latex-recommended \
     texlive-science texlive-lang-french texlive-bibtex-extra biber make \
     g++ \
     cmake \
  && curl -LsSf https://astral.sh/uv/install.sh | sh

# Second layer:
#   - Install the dycov tool itself using uv.
#   - COPY THE EXAMPLES into a global location accessible to users
COPY ./$dycov_PKG /tmp/
RUN uv pip install --system /tmp/$dycov_PKG && rm /tmp/$dycov_PKG

# Create directory and copy examples
COPY ./$dycov_EXAMPLES /opt/dycov/examples

# Copy the entrypoint shell script
COPY start_dycov.sh /

ENTRYPOINT ["/start_dycov.sh"]