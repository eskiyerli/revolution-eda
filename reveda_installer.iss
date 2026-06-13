; Inno Setup script for Revolution EDA
; Metadata mirrors nuitka-project directives in reveda.py.
;
; Build steps (example):
; 1) Run build_windows.ps1 to generate Nuitka standalone output.
; 2) Compile this script with ISCC.
;
; Optional command-line override example:
; iscc /DSourceRoot="C:\Users\eskiy\dist\revolution-eda\windows-amd64-py3.13\reveda" reveda_installer.iss

#define MyAppName "Revolution EDA"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Revolution EDA"
#define MyAppExeName "reveda.exe"
#define MyAppDescription "Electronic Design Automation Software for Professional Custom IC Design Engineers from schematics to GDSII"

; Default source folder matches build_windows.ps1 output convention.
; Override with /DSourceRoot="..." when invoking ISCC if needed.
#ifndef SourceRoot
  #define SourceRoot "C:\Users\eskiy\dist\revolution-eda\windows-amd64-py3.13\reveda"
#endif

[Setup]
AppId={{A1E66BA1-C9D0-4B57-BD23-08F78E6A4F8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppDescription}
AppCopyright=Revolution Semiconductor (C) 2026
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=dist\installer
OutputBaseFilename=revolution-eda-{#MyAppVersion}-windows-x64-setup
SetupIconFile=revedaCoreLogo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

