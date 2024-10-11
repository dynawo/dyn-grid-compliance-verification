#! /usr/bin/pwsh

$WORK_DIR = Resolve-Path $args[0]
$DOCKER_IMAGE = "dgcv:latest"

$MAPPED_DIR = Join-Path -Path "$WORK_DIR" -ChildPath "dgcv_docker"
If (Test-Path -Path "$MAPPED_DIR" ) {
	# Folder exists, nothing to do
} else {
	$MAPPED_DIR = New-Item -Path "$WORK_DIR" -Name "dgcv_docker" -ItemType "directory"
}

$DGCV_UID= 1001
$DGCV_GID = 1001
$DGCV_USER = $env:UserName
$DGCV_GROUP = $env:UserName

docker run --rm -it `
     -v ${MAPPED_DIR}:/home/"$DGCV_USER" `
     -e DGCV_USER="$DGCV_USER" -e DGCV_GROUP="$DGCV_GROUP" -e DGCV_UID="$DGCV_UID" -e DGCV_GID="$DGCV_GID" `
     --entrypoint /start_dgcv.sh `
     --name dgcv --hostname dgcv "$DOCKER_IMAGE"
