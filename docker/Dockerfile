# Dockerfile for containerizing the Dycov tool.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

FROM python:3.11-slim-bookworm

ARG dycov_PKG=dycov-0.8.1-py3-none-any.whl
ARG dycov_EXAMPLES=examples
ARG DYNAWO_DIR_NAME=dynawo_build

ENV DEBIAN_FRONTEND=noninteractive
# Add uv's install directory to the PATH
ENV PATH="/root/.local/bin:${PATH}"

# First layer:
#   - Update the base debian dist.
#   - Install required deb dependencies (texlive, etc.). Python is already in the base image.
#   - Install uv (Python package manager).
RUN apt-get update && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl unzip rsync \
     texlive-base texlive-latex-base texlive-latex-extra texlive-latex-recommended \
     texlive-science texlive-lang-french texlive-bibtex-extra biber make \
     g++ \
     cmake \
  && curl -LsSf https://astral.sh/uv/install.sh | sh

# Second layer:
#   - Install the dycov tool itself using uv.
COPY ./$dycov_PKG /tmp/
COPY ./$dycov_EXAMPLES /tmp/examples
RUN uv pip install --system /tmp/$dycov_PKG && rm /tmp/$dycov_PKG

# Third layer:
#   - Install Dynawo from the host path provided at build time.
#   - Add the dynawo executable to the system PATH.
COPY ./$DYNAWO_DIR_NAME /opt/dynawo_install

RUN \
    echo "Checking for Boost compatibility patch..." && \
    if command -v g++ >/dev/null; then \
        # Use -dumpversion for reliable major version extraction (consistent with installer)
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

# Copy the entrypoint shell script
COPY start_dycov.sh /

ENTRYPOINT ["/start_dycov.sh"]