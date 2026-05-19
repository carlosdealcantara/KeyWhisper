[Setup]
AppName=KeyWhisper
AppVersion=1.0.0
AppPublisher=Carlos de Alcantara
DefaultDirName={autopf}\KeyWhisper
DefaultGroupName=KeyWhisper
OutputBaseFilename=KeyWhisper_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
; Pegando todos os arquivos da pasta do Disco D que sabemos que funciona!
Source: "D:\KeyWhisper_dist\KeyWhisper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"
Name: "{autodesktop}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\KeyWhisper.exe"; Description: "Iniciar KeyWhisper"; Flags: nowait postinstall skipifsilent
