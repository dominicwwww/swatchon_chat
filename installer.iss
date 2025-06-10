[Setup]
AppName=SwatchOn Partner Hub
AppVersion=1.0.0
DefaultDirName={pf}\SwatchOnPartnerHub
DefaultGroupName=SwatchOn Partner Hub
OutputDir=installer
OutputBaseFilename=SwatchOnPartnerHubSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\SwatchonChat.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "components\\*"; DestDir: "{app}\\components"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\SwatchOn Partner Hub"; Filename: "{app}\\SwatchonChat.exe"
Name: "{commondesktop}\\SwatchOn Partner Hub"; Filename: "{app}\\SwatchonChat.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 아이콘:" 