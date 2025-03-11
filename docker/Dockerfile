# Dockerfile for containerizing the Dynamic grid compliance validation tool.
#
# To rebuild the Docker image:
#   docker build -t dycov:latest -t dycov:X.Y . > build.log 2>&1 &
# (if the name of the pip package changes, add: --build-arg dycov_PKG=whatever )
#
# To launch the container (adapt your local volume path!), use the
# provided script "run_dycov_docker.sh".  This script will launch the
# container with the adequate mapping of local volume and UID/GID
# mappings.  Heres's an example, in case you want to run it by hand:
#
#  docker run --rm -it \
#     -v /some/host/dir:/home/myuser \
#     -e dycov_USER=myuser -e dycov_GROUP=mygroup -e dycov_UID=1000 -e dycov_GID=1000 \
#     --entrypoint /start_dycov.sh \
#     --name dycov --hostname dycov "dycov:latest
#
#
# (c) 2022 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     demiguel@aia.es
#     omsg@aia.es
#

FROM debian:bullseye-slim

ARG dycov_PKG=dycov_RTE_AIA-0.0.1-py3-none-any.whl
ARG DWO_ZIP=Dynawo_omc_V1.4.0.zip
ARG dycov_EXAMPLES=examples

ENV DEBIAN_FRONTEND=noninteractive

# First layer:
#   - Update the base debian dist, and install all required debs (python, texlive).
#   - Install Dynawo (at this moment, using the public nighly))
RUN apt-get update && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl unzip rsync python3 python3-pip \
     texlive-base texlive-latex-base texlive-latex-extra texlive-latex-recommended \
     texlive-science texlive-lang-french texlive-bibtex-extra biber make \
  && curl -sSOL https://github.com/dynawo/dynawo/releases/download/nightly/"$DWO_ZIP" \
  && unzip -q "$DWO_ZIP" -d /opt \
  && rm "$DWO_ZIP" \
  && /bin/echo -e '\n\nexport PATH=/opt/dynawo:$PATH' >> /etc/profile


# Second layer:
#   - The pip package for the dycov tool itself, and all its dependencies (Note:
#     the COPY and the "rm" can be removed once the package is published (either
#     on PyPI or as a public download from Github)
COPY ./$dycov_PKG $dycov_EXAMPLES /tmp/
RUN pip install --upgrade pip && \  
    pip install /tmp/$dycov_PKG && rm /tmp/$dycov_PKG


# Copy the entrypoint shell script
COPY start_dycov.sh /

ENTRYPOINT ["/start_dycov.sh"]

