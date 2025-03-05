#! /usr/bin/pwsh

$WORK_DIR = Resolve-Path $args[0]
$DOCKER_IMAGE = "dycov:latest"

$MAPPED_DIR = Join-Path -Path "$WORK_DIR" -ChildPath "dycov_docker"
If (Test-Path -Path "$MAPPED_DIR" ) {
	# Folder exists, nothing to do
} else {
	$MAPPED_DIR = New-Item -Path "$WORK_DIR" -Name "dycov_docker" -ItemType "directory"
}

$dycov_UID= 1001
$dycov_GID = 1001
$dycov_USER = $env:UserName
$dycov_GROUP = $env:UserName

docker run --rm -it `
     -v ${MAPPED_DIR}:/home/"$dycov_USER" `
     -e dycov_USER="$dycov_USER" -e dycov_GROUP="$dycov_GROUP" -e dycov_UID="$dycov_UID" -e dycov_GID="$dycov_GID" `
     --entrypoint /start_dycov.sh `
     --name dycov --hostname dycov "$DOCKER_IMAGE"
