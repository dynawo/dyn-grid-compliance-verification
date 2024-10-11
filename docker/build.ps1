#! /usr/bin/pwsh

$TAG=$args[0]

$PKG = get-childitem "..\dist" -recurse | where {$_.extension -eq ".whl"} | Sort LastWriteTime -Descending | Select-Object -First 1   # newest wheel
If (Test-Path -Path "$PKG" ) {
	Remove-Item "$PKG"
}
Copy-Item "..\dist\$PKG" -Destination "."

$EXAMPLES = "examples"
If (Test-Path -Path "$EXAMPLES" ) {
	Remove-Item "$EXAMPLES" -Recurse
}
Copy-Item "..\$EXAMPLES" -Destination "." -Recurse

$ZIP = "Dynawo_omc_V1.4.0.zip"

# Launch the build
If (Test-Path -Path "build.log" ) {
	Remove-Item "build.log"
}
docker build -t dgcv:latest -t dgcv:"$TAG" `
	--build-arg DGCV_PKG="$PKG" `
	--build-arg DGCV_EXAMPLES="$EXAMPLES" `
	--build-arg DWO_ZIP="$ZIP" .

# Clean up
Remove-Item "$PKG"
Remove-Item "$EXAMPLES" -Recurse
