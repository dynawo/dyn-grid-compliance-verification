[CustomMessages]
#define PythonVersion "11"
#define DGCVVersion "0.5.2"
#define CMakeVersion "3.31.1"
#define MiktexVersion "24.1"
#define SourceDir "SOURCE DIRECTORY"
; SourceDir directory should contain the following items:
;   * dgcv_repo: tool directory (https://github.com/dynawo/dyn-grid-compliance-verification)
;   * dynawo: Directory with the installation for Windows systems of Dynawo (https://github.com/dynawo/dynawo/releases)
;       After installing Dynawo applies the following corrections:
;		- Edit the file share\cmake\FindSundials.cmake removing the lines:
;			if(MSVC)
;				set(LIBRARY_DIR bin)
;			endif()
;		- Edit the file dynawo.cmd adding the lines:
;			if /I "%~1"=="dump-model" (
;	      for /f "tokens=1,* delims= " %%a in ("%*") do set DUMP_MODEL_ARGS=%%b
;				%DYNAWO_INSTALL_DIR%"sbin\dumpModel.exe !DUMP_MODEL_ARGS!

[Setup]
AppName=Dynamic Grid Compliance Verification
AppVersion={#DGCVVersion}
DefaultDirName={sd}\DGCV
OutputBaseFilename=DGCV_win_Installer
Compression=lzma
SolidCompression=yes

[Dirs]
Name: "{app}\dyn-grid-compliance-verification"; Flags: deleteafterinstall

[Files]
; Add project files
Source: "{#SourceDir}\dgcv_repo\*"; Excludes: ".git"; DestDir: "{app}\dyn-grid-compliance-verification\"; Flags: deleteafterinstall ignoreversion recursesubdirs createallsubdirs
; Add examples files
Source: "{#SourceDir}\dgcv_repo\examples\*"; Excludes: ".git"; DestDir: "{app}\examples\"; Flags: ignoreversion recursesubdirs createallsubdirs
; Add Dynawo files in the root directory
Source: "{#SourceDir}\dynawo\*"; DestDir: "{app}\dynawo\"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
; Install Python if not found
StatusMsg: "Installing Python..."; Filename: "{tmp}\python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe"; Parameters: "InstallAllUsers=1 PrependPath=1"; Check: not IsPythonInstalled

; Install MiKTeX if not found
StatusMsg: "Installing MiKTeX..."; Filename: "{tmp}\basic-miktex-{#MiktexVersion}-x64.exe"; Check: not IsMikTeXInstalled

; Install CMake if not found
StatusMsg: "Installing CMake..."; Filename: "msiexec"; Parameters: "/i {tmp}\cmake-{#CMakeVersion}-windows-x86_64.msi /norestart"; Check: not IsCMakeInstalled

; Install VS2019 if not found
StatusMsg: "Installing Visual Studio 2019..."; Filename: "{tmp}\vs_BuildTools.exe"; Parameters: "--wait --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.TestTools.BuildTools --add Microsoft.VisualStudio.Component.VC.ASAN --add Microsoft.VisualStudio.Component.VC.CMake.Project --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows10SDK.19041"; Check: not IsVSInstalled

; Install build module for Python
StatusMsg: "Installing Python build module..."; Filename: "{code:GetPythonPath}"; Parameters: "-m pip install build"; Flags: runhidden

; Compile the project using build
StatusMsg: "Compiling the project..."; Filename: "{code:GetPythonPath}"; Parameters: "-m build --wheel"; WorkingDir: "{app}\dyn-grid-compliance-verification\"; Flags: runhidden

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Filename: "{code:GetPythonPath}"; Parameters: "-m venv dgcv_venv"; WorkingDir: "{app}"; Flags: runhidden

; Install the built package in the virtual environment
StatusMsg: "Installing project package in virtual environment..."; Filename: "{app}\dgcv_venv\Scripts\python.exe"; Parameters: "-m pip install dyn-grid-compliance-verification\dist\dgcv-{#DGCVVersion}-py3-none-any.whl";  WorkingDir: "{app}"; Flags: runhidden;

[InstallDelete]
Type: filesandordirs; Name: "{app}\dyn-grid-compliance-verification"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: files; Name: "{userdesktop}\DGCV.bat"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app};{app}\dynawo"; Check: NeedsAddPath()

[Code]
const
  SHCONTCH_NOPROGRESSBOX = 4;
  SHCONTCH_RESPONDYESTOALL = 16;

var
  DownloadPage: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Successfully downloaded file to {tmp}: %s', [FileName]));
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @OnDownloadProgress);
  DownloadPage.ShowBaseNameInsteadOfUrl := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpReady then begin
    DownloadPage.Clear;
    // Use AddEx to specify a username and password
    DownloadPage.Add('https://github.com/Kitware/CMake/releases/download/v{#CMakeVersion}/cmake-{#CMakeVersion}-windows-x86_64.msi', 'cmake-{#CMakeVersion}-windows-x86_64.msi', '');
    DownloadPage.Add('https://miktex.org/download/ctan/systems/win32/miktex/setup/windows-x64/basic-miktex-{#MiktexVersion}-x64.exe', 'basic-miktex-{#MiktexVersion}-x64.exe', '');
    DownloadPage.Add('https://www.python.org/ftp/python/3.{#PythonVersion}.{#PythonSubVersion}/python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe', 'python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe', '');
    DownloadPage.Add('https://download.visualstudio.microsoft.com/download/pr/8497e528-d106-4143-95eb-3deb1b2f4851/d247112120128c790c6e2a89fe4c6acbf0f714a7a9f15df223c4722b861090fd/vs_BuildTools.exe', 'vs_BuildTools.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download; // This downloads the files to {tmp}
        Result := True;
      except
        if DownloadPage.AbortedByUser then
          Log('Aborted by user.')
        else
          SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
        Result := False;
      end;
    finally
      DownloadPage.Hide;
    end;
  end else
    Result := True;
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

function GetPythonPath(Param: String): String;
begin
  if IsPythonInPath then begin
    Result := 'python.exe';
    exit;
  end;

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
  Result := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0') 
  or RegKeyExists(HKCU, 'SOFTWARE\Microsoft\VisualStudio\14.0'); // VS 2019 key
    
  if Result = True then
    MsgBox('Avoiding the installation of VisualStudio2019, it is already installed on the system.', mbInformation, MB_OK);
    
end;

function NeedsAddPath: boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  { look for the path with leading and trailing semicolon }
  { Pos() returns 0 if not found }
  Result := Pos(';' + {app} + ';', ';' + OrigPath + ';') = 0;
end;

[Code]
function CreateBatch: boolean;
var
  fileName : string;
  lines : TArrayOfString;
begin
  fileName := ExpandConstant('{userdesktop}\DGCV.bat');
  SetArrayLength(lines, 1);
  lines[0] := ExpandConstant('start cmd /k "{app}\dgcv_venv\Scripts\activate && cd /d {app}"');
  Result := SaveStringsToFile(filename,lines,true);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if  CurStep=ssPostInstall then
    begin
      DelTree('{app}\dyn-grid-compliance-verification', True, True, True);
      CreateBatch;
    end
end;