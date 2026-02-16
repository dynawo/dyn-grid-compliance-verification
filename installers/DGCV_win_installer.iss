[CustomMessages]
#define PythonVersion "11"
#define PythonSubVersion "6"
#define DyCoVVersion "0.9.2"
#define MiktexVersion "24.1"
#define SourceDir "..\.."
; SourceDir directory should contain the following items:
;   * dycov_repo: tool directory (https://github.com/dynawo/dyn-grid-compliance-verification)
;   * manual: compiled user manual of the tool (PDF & HTML)
; 
; Before share Dynawo applies the following corrections:
;		- Edit the file share\cmake\FindSundials.cmake removing the lines:
;			if(MSVC)
;				set(LIBRARY_DIR bin)
;			endif()

[Setup]
AppName=Dynamic grid Compliance Verification
AppVersion={#DyCoVVersion}
DefaultDirName={sd}\DyCoV
OutputBaseFilename=DyCoV_win_Installer
Compression=lzma
SolidCompression=yes
AlwaysRestart=yes
SetupLogging=yes

[Types]
Name: "full"; Description: "Full installation (Dycov + Dynawo + MiKTeX)"
Name: "compact"; Description: "Compact installation (Dycov)"

[Components]
Name: "python"; Description: "Python installation"; Types: full compact
Name: "miktex"; Description: "MiKTeX installation"; Types: full
Name: "dynawo"; Description: "Dynawo installation"; Types: full
Name: "examples"; Description: "Examples installation"; Types: full compact
Name: "dycov"; Description: "Dycov installation"; Types: full compact

[Files]
; Add project files
Source: "{#SourceDir}\dycov_repo\*"; Excludes: ".git,.github,.pytest_cache,.vscode,attic,dycov_venv,docker,docs,examples,installers,tests,tools"; DestDir: "{tmp}\dyn-grid-compliance-verification\"; Permissions: users-readexec; Flags: ignoreversion recursesubdirs createallsubdirs; Components: dycov
; Add Manuals in the root directory
Source: "{#SourceDir}\manual\*"; DestDir: "{app}\manual\"; Permissions: users-readexec; Flags: ignoreversion recursesubdirs createallsubdirs; Components: dycov

[Run]
; Install Python if not found
StatusMsg: "Installing Python..."; Components: python; Filename: "{tmp}\python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe"; Parameters: "InstallAllUsers=1 PrependPath=1"; Check: not IsPythonInstalled

; Install MiKTeX if not found
StatusMsg: "Installing MiKTeX..."; Components: miktex; Filename: "{tmp}\basic-miktex-{#MiktexVersion}-x64.exe"; Check: not IsMikTeXInstalled

; Install Dynawo 
StatusMsg: "Installing Dynawo..."; Components: dynawo; Filename: "tar.exe"; Parameters: "xzvf {tmp}\Dynawo_omc_v1.8.0_win.tgz -C {app}"; Flags: runhidden

; Install the project examples
StatusMsg: "Installing the project examples..."; Components: examples; Filename: "tar.exe"; Parameters: "xzvf {tmp}\examples.tgz -C {app}"; Flags: runhidden

; Create a virtual environment
StatusMsg: "Creating virtual environment..."; Components: dycov; Filename: "{code:GetPythonPath}"; Parameters: "-m venv dycov_venv"; WorkingDir: "{app}"; Flags: runhidden

; Install build module for Python
StatusMsg: "Installing Python build module..."; Components: dycov; Filename: "{app}\dycov_venv\Scripts\python.exe"; Parameters: "-m pip install --upgrade pip build"; Flags: runhidden

; Compile the project using build
StatusMsg: "Compiling the project..."; Components: dycov; Filename: "{app}\dycov_venv\Scripts\python.exe"; Parameters: "-m build --wheel"; WorkingDir: "{tmp}\dyn-grid-compliance-verification\"; Flags: runhidden

; Install the built package in the virtual environment
StatusMsg: "Installing project package in virtual environment..."; Components: dycov; Filename: "{app}\dycov_venv\Scripts\python.exe"; Parameters: "-m pip install {tmp}\dyn-grid-compliance-verification\dist\dycov-{#DyCoVVersion}-py3-none-any.whl";  WorkingDir: "{app}"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: files; Name: "{commondesktop}\DyCoV.bat"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app};{app}\dynawo"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
const
  PYTHON_REGISTRY = 'SOFTWARE\Python\PythonCore';
  MIKTEK_REGISTRY = 'SOFTWARE\MiKTeX.org\MiKTeX';

var
  DownloadPage: TDownloadWizardPage;
  
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
begin
  Result := RegKeyExists(HKLM32, PYTHON_REGISTRY) 
  or RegKeyExists(HKLM64, PYTHON_REGISTRY)
  or RegKeyExists(HKCU32, PYTHON_REGISTRY)
  or RegKeyExists(HKCU64, PYTHON_REGISTRY); // Python
    
end;

function IsMikTeXInstalled: Boolean;
begin
  Result := RegKeyExists(HKLM32, MIKTEK_REGISTRY) 
  or RegKeyExists(HKLM64, MIKTEK_REGISTRY)
  or RegKeyExists(HKCU32, MIKTEK_REGISTRY)
  or RegKeyExists(HKCU64, MIKTEK_REGISTRY);
   
end;

function CreateBatch: boolean;
var
  fileName : string;
  lines : TArrayOfString;
begin
  fileName := ExpandConstant('{commondesktop}\DyCoV.bat');
  if not FileExists(fileName) then begin
    SetArrayLength(lines, 1);
    lines[0] := ExpandConstant('start cmd /k "{app}\dycov_venv\Scripts\activate && cd /d {app}"');
    Result := SaveStringsToFile(filename,lines,true);
  end;
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Successfully downloaded file to {tmp}: %s', [FileName]));
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpReady then begin
    DownloadPage.Clear;
    // Use AddEx to specify a username and password
    DownloadPage.Add('https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v{#DyCoVVersion}/examples.tgz', 'examples.tgz', '');
    if WizardIsComponentSelected('python') and not IsPythonInstalled then 
      DownloadPage.Add('https://www.python.org/ftp/python/3.{#PythonVersion}.{#PythonSubVersion}/python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe', 'python-3.{#PythonVersion}.{#PythonSubVersion}-amd64.exe', '');
    if WizardIsComponentSelected('miktex') and not IsMikTeXInstalled then 
      DownloadPage.Add('https://miktex.org/download/ctan/systems/win32/miktex/setup/windows-x64/basic-miktex-{#MiktexVersion}-x64.exe', 'basic-miktex-{#MiktexVersion}-x64.exe', '');
    if WizardIsComponentSelected('dynawo') then
      DownloadPage.Add('https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/v{#DyCoVVersion}/Dynawo_omc_v1.8.0_win.tgz', 'Dynawo_omc_v1.8.0_win.tgz', '');
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

function NeedsAddPath(Param: string): boolean;
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
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @OnDownloadProgress);
  DownloadPage.ShowBaseNameInsteadOfUrl := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if  CurStep=ssPostInstall then
    begin
      CreateBatch;
    end
end;
