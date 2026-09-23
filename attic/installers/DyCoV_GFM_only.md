How to Create a Windows Installer for a Python CLI Tool (using Embedded Python & Inno Setup)

## Objective

The goal of this tutorial is to create a single setup.exe file for a Python command-line (CLI) tool (in this case, dycov).

The final installer will:
* Install an isolated, self-contained version of Python 3.11.
* Install your custom .whl package and all its dependencies.
* Not require administrator permissions (it installs at the user level).
* Automatically configure the user's PATH variable so they can open cmd and run the dycov command directly.

## Tools & Prerequisites

Before you begin, make sure you have:

1.  Your Package: Your tool's .whl file (e.g., dycov-1.0.0.whl).
2.  Inno Setup: The installer compiler. [Download it here](https://jrsoftware.org/isinfo.php).
3.  Python 3.11 Embedded: The portable version of Python. [Download it here](https://www.python.org/downloads/windows/) (look for "Windows embeddable package (64-bit)").

---

## Step-by-Step Guide

We'll divide the process into three phases:

1.  Prepare the Python environment that will be distributed.
2.  Write the installer script.
3.  Compile and test the final result.

### Phase 1: Prepare the Self-Contained Python Environment

This is the "raw material" for our installer. We will create a folder that contains Python and your tool, already installed.

#### Step 1.1: Create the Source Folder

Create a folder on your machine that will hold all your application's files. For this tutorial, we'll call it: C:\dycov_source

#### Step 1.2: Add Python

Download the "Windows embeddable package" for Python 3.11. It's a .zip file. Unzip all of its contents directly into your C:\dycov_source folder.

Your folder should now look like this:

C:\dycov_source\
├── python.exe
├── python3.dll
├── python311.dll
├── python311.zip
├── python311._pth
└── ... (and other .dll files)


#### Step 1.3: Enable and Install pip (Crucial!)

By default, the embedded version of Python doesn't have pip and can't see site-packages. Let's fix that.

1.  Enable site-packages:
    Open the python311._pth file (in your folder) with a text editor. Remove the # from the beginning of the import site line.

    *Before:*
    
    python311.zip
    .
    #import site
    
    *After:*
    
    python311.zip
    .
    import site
    
2.  Download get-pip.py:
    Download the official script [from here](https://bootstrap.pypa.io/get-pip.py) and save it inside your C:\dycov_source folder.

3.  Install pip:
    Open a terminal (CMD or PowerShell) inside your C:\dycov_source folder and run:

    .\python.exe get-pip.py
    
    You will see pip install and two new folders appear: Lib and Scripts.

#### Step 1.4: Install Your dycov Tool

1.  Copy your dycov-X.X.X.whl file into the C:\dycov_source folder.
2.  In the same terminal, run pip (using the local python) to install your package:

    .\python.exe -m pip install dycov-1.0.0.whl 
    
    (Replace the .whl filename with yours).

    This will install dycov and any dependencies (like numpy, requests, etc.) into C:\dycov_source\Lib\site-packages. It will also create the dycov.exe executable inside C:\dycov_source\Scripts.

#### Step 1.5: Cleanup (Optional)

To make the installer a bit lighter, you can now delete the files you no longer need from C:\dycov_source:
* get-pip.py
* dycov-1.0.0.whl

Phase 1 complete! Your C:\dycov_source folder is now a fully functional, portable Python environment containing your tool.

---

### Phase 2: Write the Installer Script (Inno Setup)

Now we'll tell Inno Setup to take that folder and turn it into a setup.exe.

1.  Open Inno Setup.
2.  Click File > New and cancel the wizard (Cancel).
3.  Paste the following script into the editor.

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
Source: "C:\dycov_source\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs


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

4.  Save this script as dycov_setup.iss.

#### Key Parts of the Script Explained:

* [Setup]:
    * PrivilegesRequired=lowest: This is the key line that ensures it does not ask for admin permissions.
    * DefaultDirName={userappdata}\Dycov: This tells it to install in the user's folder (e.g., C:\Users\YourName\AppData\Local\Dycov), which doesn't require special permissions.
* [Tasks]:
    * Defines the "Add application to the PATH (recommended)" checkbox that the user will see.
* [Files]:
    * Source: "C:\dycov_source\*": This is the most important line you must edit. Make sure it points to the folder you created in Phase 1.
* [Registry]:
    * Root: HKCU: Modifies the PATH for the HKEY_CURRENT_USER only.
    * ValueData: "{olddata};{app};{app}\Scripts": Appends the path to python.exe ({app}) and the path to dycov.exe ({app}\Scripts) to the user's PATH.

---

### Phase 3: Compile and Test the Installer

This is the final step.

1.  Compile:
    * With your dycov_setup.iss file open in Inno Setup, go to the menu Build > Compile (or press Ctrl+F9).
    * Inno Setup will package your entire C:\dycov_source folder into a single executable.
    * If all goes well, you will find your dycov-setup.exe in a new Output subfolder.

2.  Test (Important):
    * Do not test the installer on your own development machine, as your environment is already set up.
    * Use a clean Virtual Machine (VM) or Windows Sandbox to simulate a real user's experience.
    * Run your dycov-setup.exe on the clean machine.
    * Open a NEW Command Prompt (CMD) (this is important for it to load the updated PATH variable).
    * Type dycov and press Enter.

If everything worked, your tool will run, executing its code from the AppData folder and using the Python you bundled with it!