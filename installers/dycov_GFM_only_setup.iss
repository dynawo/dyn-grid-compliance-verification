; ===================================================================
;  Inno Setup Script for Dycov (User-level installation)
; ===================================================================

[Setup]
; --- Basic App Information ---
AppName=Dycov CLI Tool
AppVersion=1.0  ; Change this to your app's version
DefaultDirName={userappdata}\Dycov
DefaultGroupName=Dycov
UninstallDisplayIcon={app}\python.exe
SolidCompression=yes
OutputBaseFilename=dycov-setup

; --- Permissions Configuration (User Level) ---
; 'lowest' means it will NOT ask for admin elevation.
PrivilegesRequired=lowest 
; 'Always' ensures the installer knows it's in non-admin mode
PrivilegesRequiredOverridesAllowed=dialog


[Tasks]
; Optional task for the user to decide whether to modify the PATH
Name: "modpath"; Description: "Add the application to the PATH (recommended)"; GroupDescription: "Configuration:"; Flags: checkedonce


[Files]
; --- Application Files ---
; IMPORTANT!! Change the 'Source' path to your folder's path.
; Copies all content from your prepared folder to the installation directory.
Source: "D:\Escritorio\DyCoV_GFM\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs


[Registry]
; --- PATH Modification (Only if the task is checked) ---
; Adds {app} (for python.exe) and {app}\Scripts (for dycov.exe) to the USER's PATH (HKCU)
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app};{app}\Scripts"; \
    Tasks: modpath; Check: NeedsAddPath('{app}\Scripts')


[Code]
// --- Helper Function for PATH ---
// This prevents adding the path to the PATH if it already exists (e.g., on reinstall)

function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  // Check if the path (Param) is already in the variable (OrigPath)
  Result := Pos(AnsiLowerCase(Param), AnsiLowerCase(OrigPath)) = 0;
end;