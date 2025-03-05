
# Docker container

This directory contains the Dockerfile and auxiliary scripts to build
a docker container for running the application.


# To build the image

You can use the provided `build.sh` script to run the build steps automatically
(it works if you run it all from your local git clone repo).

Essentially, what it does is copy (actually hardlink) the pip package of the dycov
tool, the examples, and the Dynawo zip to this directory; and then invoke
`docker build` using tags to label the image.  The image is always tagged using
a second tag "latest", so that you can easily manage several image versions.

In brief (an example):

```
ln  ../dist/dycov_RTE_AIA-0.0.1-py3-none-any.whl .
cp -a ../examples .
wget https://github.com/dynawo/dynawo/releases/download/nightly/Dynawo_omc_V1.4.0.zip
docker build -t dycov:latest -t dycov:1.3 \
             --build-arg dycov_PKG=dycov_RTE_AIA-0.0.1-py3-none-any.whl \
             --build-arg dycov_EXAMPLES=examples \
             --build-arg DWO_ZIP=Dynawo_omc_V1.4.0.zip \
             .
```



## To run a container

To run a container instance from the built image, use the provided script `run_dycov_docker.sh`

