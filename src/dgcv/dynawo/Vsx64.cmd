@if not defined _echo echo off

set VSWHERE=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe
echo %VSWHERE%
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -prerelease -latest -property installationPath`) do (
  if exist "%%i\VC\Auxiliary\Build\vcvars64.bat" (
    "%%i\VC\Auxiliary\Build\vcvars64.bat"
    cd %1 
    %2  jobs --generate-preassembled --model-list %3 --non-recursive-modelica-models-dir . --output-dir %4
    exit /b
  )
)

rem Instance or command prompt not found
exit /b 2