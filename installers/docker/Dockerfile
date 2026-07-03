# Dockerfile for containerizing the Dycov tool.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

FROM python:3.13-slim-bookworm

ARG dycov_PKG=dycov-0.8.1-py3-none-any.whl
ARG dycov_EXAMPLES=examples
ARG dycov_TOOLS=tools
ARG dycov_TUTORIALS=tutorials
ARG DYNAWO_DIR_NAME=dynawo_build

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

# Copy the standalone Dynawo PAR generation utility (tools/dynawo_par).
# It is a dependency-free helper, not part of the dycov package.
COPY ./$dycov_TOOLS /opt/dycov/tools

# Copy the user-facing tutorials (Markdown). Kept as-is so their relative
# cross-links work. docs/installation is intentionally not shipped: it is a
# pre-install guide with no value inside an already-installed image.
COPY ./$dycov_TUTORIALS /opt/dycov/tutorials

# Third layer:
#   - Install Dynawo from the host path provided at build time.
COPY ./$DYNAWO_DIR_NAME /opt/dynawo_install

RUN \
    echo "Checking for Boost compatibility patch..." && \
    if command -v g++ >/dev/null; then \
        GNU_MAJOR=$(g++ -dumpversion | cut -d"." -f1); \
        echo "Detected GCC major version: $GNU_MAJOR"; \
        if [ "$GNU_MAJOR" -gt 11 ]; then \
            BOOST_HEADER=/opt/dynawo_install/dynawo/include/boost/thread/pthread/thread_data.hpp; \
            if [ -f "$BOOST_HEADER" ] && grep -q '#if PTHREAD_STACK_MIN > 0$' "$BOOST_HEADER"; then \
                echo "Applying compatibility patch for Boost and GCC > 11 to $BOOST_HEADER..."; \
                sed --in-place=.ORIG -E 's/^#if PTHREAD_STACK_MIN > 0$/#ifdef PTHREAD_STACK_MIN/' "$BOOST_HEADER"; \
            else \
                echo "Boost header not found or already patched."; \
            fi; \
        else \
            echo "GCC version is 11 or less, no patch needed."; \
        fi; \
    else \
        echo "WARNING: g++ not found, skipping Boost patch."; \
    fi

RUN echo 'export PATH="/opt/dynawo_install/dynawo:${PATH}"' > /etc/profile.d/dycov.sh

# Fourth layer:
#   - Copy the pre-compiled manual (built by prepare_release.sh) into the image.
ARG MANUAL_BUILD=manual_build
COPY ./$MANUAL_BUILD /opt/dycov/manual

# Copy the entrypoint shell script.
# Set the exec bit explicitly: COPY preserves the source file mode, so if the
# checkout lost +x (Windows/WSL, git archive, core.fileMode=false, ...) the
# ENTRYPOINT would fail at runtime with "permission denied".
COPY start_dycov.sh /
RUN chmod 0755 /start_dycov.sh

ENTRYPOINT ["/start_dycov.sh"]