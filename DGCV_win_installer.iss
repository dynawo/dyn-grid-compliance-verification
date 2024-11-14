[CustomMessages]
#define PythonVersion "11"
#define DGCVVersion "0.5.2"
#define CMakeVersion "3.31.0"
#define MiktexVersion "24.1"
#define SourceDir "C:\Users\path\to\src"

[Setup]
AppName=Dynamic Grid Compliance Verification
AppVersion={#DGCVVersion}
DefaultDirName={pf}\DGCV
OutputBaseFilename=DGCV_win_Installer
Compression=lzma
SolidCompression=yes

[Files]
; Add project files
Source: "{#SourceDir}\dyn-grid-compliance-verification\*"; DestDir: "{app}\dyn-grid-compliance-verification\"; Flags: ignoreversion recursesubdirs createallsubdirs
; Add Dynawo files in the root directory
Source: "{#SourceDir}\dynawo\*"; DestDir: "{app}\dynawo\"; Flags: ignoreversion recursesubdirs createallsubdirs
; Add Python installer
Source: "{#SourceDir}\python-3.{#PythonVersion}.0-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
; Add MiKTeX, VS2019, and CMake installers
Source: "{#SourceDir}\basic-miktex-{#MiktexVersion}-x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#SourceDir}\cmake-{#CMakeVersion}-windows-x86_64.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#SourceDir}\vs_Community2019.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
; Install Python if not found
StatusMsg: "Installing Python..."; Filename: "{tmp}\python-3.{#PythonVersion}.0-amd64.exe"; Parameters: "InstallAllUsers=1 PrependPath=1"; Check: not IsPythonInstalled

; Install MiKTeX if not found
StatusMsg: "Installing MiKTeX..."; Filename: "{tmp}\basic-miktex-{#MiktexVersion}-x64.exe"; Check: not IsMikTeXInstalled

; Install CMake if not found
StatusMsg: "Installing CMake..."; Filename: "msiexec"; Parameters: "/i {tmp}\cmake-{#CMakeVersion}-windows-x86_64.msi /norestart"; Check: not IsCMakeInstalled

; Install VS2019 if not found
StatusMsg: "Installing Visual Studio 2019..."; Filename: "{tmp}\vs_Community2019.exe"; Parameters: "--wait"; Check: not IsVSInstalled

; Install build module for Python
StatusMsg: "Installing Python build module..."; Filename: "python.exe"; Parameters: "-m pip install build"; Flags: runhidden; Check: IsPythonInPath

; Install build module for Python
StatusMsg: "Installing Python build module..."; Filename: "{code:GetPythonPath}"; Parameters: "-m pip install build"; Flags: runhidden; Check: not IsPythonInPath

; Compile the project using build
StatusMsg: "Compiling the project..."; Filename: "python.exe"; Parameters: "-m build --wheel"; WorkingDir: "{app}\dyn-grid-compliance-verification\"; Flags: runhidden; Check: IsPythonInPath

; Compile the project using build
StatusMsg: "Compiling the project..."; Filename: "{code:GetPythonPath}"; Parameters: "-m build --wheel"; WorkingDir: "{app}\dyn-grid-compliance-verification\"; Flags: runhidden; Check: not IsPythonInPath

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Filename: "python.exe"; Parameters: "-m venv {app}\dgcv_venv"; Flags: runhidden; Check: IsPythonInPath

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Filename: "{code:GetPythonPath}"; Parameters: "-m venv {app}\dgcv_venv"; Flags: runhidden; Check: not IsPythonInPath

; Install the built package in the virtual environment
StatusMsg: "Installing project package in virtual environment..."; Filename: "{app}\dgcv_venv\Scripts\python.exe"; Parameters: "-m pip install {app}\dyn-grid-compliance-verification\dist\dgcv-{#DGCVVersion}-py3-none-any.whl"; Flags: runhidden;

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
