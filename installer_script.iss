[Setup]
AppName=KeyWhisper
AppVersion=1.0
AppPublisher=Antigravity
DefaultDirName={autopf}\KeyWhisper
DefaultGroupName=KeyWhisper
OutputBaseFilename=KeyWhisper_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "C:\Users\sorla\Projetos\KeyWhisper\dist\KeyWhisper.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"
Name: "{autodesktop}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\KeyWhisper.exe"; Description: "Iniciar KeyWhisper"; Flags: nowait postinstall skipifsilent
