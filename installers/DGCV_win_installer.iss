[CustomMessages]
#define PythonVersion "11"
#define DGCVVersion "0.5.2"
#define CMakeVersion "3.31.1"
#define MiktexVersion "24.1"
#define SourceDir "SOURCE DIRECTORY"
; SourceDir directory should contain the following items:
;   * cmake installer (https://cmake.org/download/)
;   * Visual Studio 2019 BuildTools installer (https://learn.microsoft.com/en-us/visualstudio/releases/2019/history#release-dates-and-build-numbers)
;   * MikTeX installer (https://miktex.org/download)
;   * Python installer (https://www.python.org/downloads/windows/)
;   * dgcv_repo: tool directory (https://github.com/dynawo/dyn-grid-compliance-verification)
;   * dynawo: Directory with the installation for Windows systems of Dynawo (https://github.com/dynawo/dynawo/releases)
;       After installing Dynawo applies the following corrections:
;		- Edit the file share\cmake\FindSundials.cmake removing the lines:
;			if(MSVC)
;				set(LIBRARY_DIR bin)
;			endif()
;		- Edit the file dynawo.cmd adding the lines:
;			if /I "%~1"=="dump-model" (
;	            for /f "tokens=1,* delims= " %%a in ("%*") do set DUMP_MODEL_ARGS=%%b
;				%DYNAWO_INSTALL_DIR%"sbin\dumpModel.exe !DUMP_MODEL_ARGS!

[Setup]
AppName=Dynamic Grid Compliance Verification
AppVersion={#DGCVVersion}
DefaultDirName={sd}\DGCV
OutputBaseFilename=DGCV_win_Installer
Compression=lzma
SolidCompression=yes

[Files]
; Add project files
Source: "{#SourceDir}\dgcv_repo\*"; Excludes: ".git"; DestDir: "{app}\dyn-grid-compliance-verification\"; Flags: ignoreversion recursesubdirs createallsubdirs
; Add Dynawo files in the root directory
Source: "{#SourceDir}\dynawo\*"; DestDir: "{app}\dynawo\"; Flags: ignoreversion recursesubdirs createallsubdirs
; Add Python installer
Source: "{#SourceDir}\python-3.{#PythonVersion}.6-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
; Add MiKTeX, VS2019, and CMake installers
Source: "{#SourceDir}\basic-miktex-{#MiktexVersion}-x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#SourceDir}\cmake-{#CMakeVersion}-windows-x86_64.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#SourceDir}\vs_BuildTools.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
; Install Python if not found
StatusMsg: "Installing Python..."; Filename: "{tmp}\python-3.{#PythonVersion}.6-amd64.exe"; Parameters: "InstallAllUsers=1 PrependPath=1"; Check: not IsPythonInstalled

; Install MiKTeX if not found
StatusMsg: "Installing MiKTeX..."; Filename: "{tmp}\basic-miktex-{#MiktexVersion}-x64.exe"; Check: not IsMikTeXInstalled

; Install CMake if not found
StatusMsg: "Installing CMake..."; Filename: "msiexec"; Parameters: "/i {tmp}\cmake-{#CMakeVersion}-windows-x86_64.msi /norestart"; Check: not IsCMakeInstalled

; Install VS2019 if not found
StatusMsg: "Installing Visual Studio 2019..."; Filename: "{tmp}\vs_BuildTools.exe"; Parameters: "--wait --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.TestTools.BuildTools --add Microsoft.VisualStudio.Component.VC.ASAN --add Microsoft.VisualStudio.Component.VC.CMake.Project --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows10SDK.19041"; Check: not IsVSInstalled

; Install build module for Python
StatusMsg: "Installing Python build module..."; Filename: "python.exe"; Parameters: "-m pip install build"; Flags: runhidden; Check: IsPythonInPath

; Install build module for Python
StatusMsg: "Installing Python build module..."; Filename: "{code:GetPythonPath}"; Parameters: "-m pip install build"; Flags: runhidden; Check: not IsPythonInPath

; Compile the project using build
StatusMsg: "Compiling the project..."; Filename: "python.exe"; Parameters: "-m build --wheel"; WorkingDir: "{app}\dyn-grid-compliance-verification\"; Flags: runhidden; Check: IsPythonInPath

; Compile the project using build
StatusMsg: "Compiling the project..."; Filename: "{code:GetPythonPath}"; Parameters: "-m build --wheel"; WorkingDir: "{app}\dyn-grid-compliance-verification\"; Flags: runhidden; Check: not IsPythonInPath

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Filename: "python.exe"; Parameters: "-m venv dgcv_venv"; WorkingDir: "{app}"; Flags: runhidden; Check: IsPythonInPath

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Filename: "{code:GetPythonPath}"; Parameters: "-m venv dgcv_venv"; WorkingDir: "{app}"; Flags: runhidden; Check: not IsPythonInPath

; Install the built package in the virtual environment
StatusMsg: "Installing project package in virtual environment..."; Filename: "{app}\dgcv_venv\Scripts\python.exe"; Parameters: "-m pip install dyn-grid-compliance-verification\dist\dgcv-{#DGCVVersion}-py3-none-any.whl";  WorkingDir: "{app}"; Flags: runhidden;

[Code]
function GetPythonPath(Param: String): String;
begin
  if DirExists('C:\Python3{#PythonVersion}') then
    Result := 'C:\Python3{#PythonVersion}'
  else if DirExists('C:\Program Files\Python3{#PythonVersion}') then
    Result := 'C:\Program Files\Python3{#PythonVersion}'
  else if DirExists('C:\Program Files (x86)\Python3{#PythonVersion}') then
    Result := 'C:\Program Files (x86)\Python3{#PythonVersion}'
  else if DirExists('C:\Users\' + ExpandConstant('{username}') + '\AppData\Local\Programs\Python\Python3{#PythonVersion}') then
    Result := 'C:\Users\' + ExpandConstant('{username}') + '\AppData\Local\Programs\Python\Python3{#PythonVersion}'
  else
    Result := ''; 

  if Result <> '' then
    Result := AddBackslash(Result) + 'python.exe';
end;

function IsPythonInPath: Boolean;
var
  ExitCode: Integer;
begin
  Result := Exec('cmd.exe', '/C python.exe --version', '', SW_HIDE, ewWaitUntilTerminated, ExitCode);
  
  if ExitCode = 0 then
    Result := True
  else
    Result := False;
        
end;

function IsPythonInstalled: Boolean;
var
  ExitCode: Integer;
begin
  Result := Exec('cmd.exe', '/C python.exe --version', '', SW_HIDE, ewWaitUntilTerminated, ExitCode);
  
  if ExitCode = 0 then
    Result := True
  else
    Result := False;
    
  if Result = True then
    MsgBox('Avoiding the installation of Python, it is already installed on the system.', mbInformation, MB_OK);
    
end;

function IsMikTeXInstalled: Boolean;
begin
  Result := DirExists('C:\Program Files\MiKTeX') or 
             DirExists('C:\Program Files (x86)\MiKTeX');
    
  if Result = True then 
    MsgBox('Avoiding the installation of MiKTeX, it is already installed on the system.', mbInformation, MB_OK);
    
end;

function IsCMakeInstalled: Boolean;
begin
  Result := DirExists('C:\Program Files\CMake') 
  or DirExists('C:\Program Files (x86)\CMake');
  
  if Result = True then
    MsgBox('Avoiding the installation of CMake, it is already installed on the system.', mbInformation, MB_OK);
    
end;

function IsVSInstalled: Boolean;
begin
  Result := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\VisualStudio\16.0') 
  or RegKeyExists(HKCU, 'SOFTWARE\Microsoft\VisualStudio\16.0'); // VS 2019 key
    
  if Result = True then
    MsgBox('Avoiding the installation of VisualStudio2019, it is already installed on the system.', mbInformation, MB_OK);
    
end;