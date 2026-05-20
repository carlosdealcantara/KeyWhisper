[Setup]
AppName=KeyWhisper
AppVersion=2.0.0
AppPublisher=Carlos de Alcantara
DefaultDirName={autopf}\KeyWhisper
DefaultGroupName=KeyWhisper
OutputBaseFilename=KeyWhisper_Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AppMutex=Global\KeyWhisper_SingleInstance_Mutex
SetupIconFile=C:\Users\sorla\Projetos\KeyWhisper\icon.ico

[Files]
Source: "C:\Users\sorla\Projetos\KeyWhisper\dist\KeyWhisper.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"
Name: "{autodesktop}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\KeyWhisper.exe"; Description: "Iniciar KeyWhisper"; Flags: nowait postinstall skipifsilent
