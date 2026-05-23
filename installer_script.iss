[Setup]
AppName=KeyWhisper
AppVersion=2.0.0
VersionInfoVersion=2.0.0.0
AppPublisher=Carlos de Alcantara
DefaultDirName={autopf}\KeyWhisper
DefaultGroupName=KeyWhisper
OutputBaseFilename=KeyWhisper_Installer_v2.0
OutputDir=C:\Users\sorla\Projetos\KeyWhisper\Output
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AppMutex=Global\KeyWhisper_SingleInstance_Mutex
CloseApplications=force
CloseApplicationsFilter=KeyWhisper.exe,WhisperDesktop.exe
SetupIconFile=C:\Users\sorla\Projetos\KeyWhisper\icon.ico
PrivilegesRequired=lowest
DisableWelcomePage=no
ShowLanguageDialog=yes

[Messages]
SelectLanguageTitle=KeyWhisper Setup
SelectLanguageLabel=%nSelect Setup Language / Selecione o Idioma:

; Otimização do layout via InitializeWizard no [Code]
ReadyLabel2a= 
ReadyLabel2b=

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english";             MessagesFile: "compiler:Default.isl"
Name: "spanish";             MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
brazilianportuguese.TaskShortcut=Criar atalho na Área de Trabalho
english.TaskShortcut=Create desktop shortcut
spanish.TaskShortcut=Crear acceso directo en el Escritorio

brazilianportuguese.TaskGroup=Atalhos adicionais:
english.TaskGroup=Additional shortcuts:
spanish.TaskGroup=Accesos directos adicionales:

brazilianportuguese.StatusMsg=Baixando inteligência artificial — isso pode levar alguns minutos...
english.StatusMsg=Downloading artificial intelligence — this may take a few minutes...
spanish.StatusMsg=Descargando inteligencia artificial — esto puede tomar unos minutos...

brazilianportuguese.RunAppName=Iniciar KeyWhisper agora
english.RunAppName=Launch KeyWhisper now
spanish.RunAppName=Iniciar KeyWhisper ahora



[Files]
Source: "C:\Users\sorla\Projetos\KeyWhisper\dist\KeyWhisper.exe"; DestDir: "{app}"; Flags: ignoreversion; BeforeInstall: HideProgressGauge
Source: "C:\Users\sorla\Projetos\KeyWhisper\download_resources.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KeyWhisper"; Filename: "{app}\KeyWhisper.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KeyWhisper"; ValueData: """{app}\KeyWhisper.exe"" --startup"; Flags: uninsdeletevalue

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\download_resources.ps1"" -ProgressFile {code:GetProgressFile} -SelectedLanguage {language}"; Flags: runhidden waituntilterminated; StatusMsg: "{cm:StatusMsg}"
Filename: "{app}\KeyWhisper.exe"; Description: "{cm:RunAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure HideProgressGauge();
begin
  WizardForm.ProgressGauge.Visible := False;
  WizardForm.ProgressGauge.Left := -1000;
end;

function SetTimer(hWnd, nIDEvent, uElapse, lpTimerFunc: Longword): Longword;
external 'SetTimer@user32.dll stdcall';

function KillTimer(hWnd, nIDEvent: Longword): Bool;
external 'KillTimer@user32.dll stdcall';

var
  ProgressFile: string;
  ProgressTimerID: Longword;
  OrigProgressLeft, OrigProgressTop, OrigProgressWidth, OrigProgressHeight: Integer;
  ProgressActive: Boolean;

procedure UpdateProgressGauge(Arg1, Arg2, Arg3, Arg4: Longword);
var
  AnsiContent: AnsiString;
  Content: string;
  ProgressPos, TotalMBPos, LabelPos, PipePos: Integer;
  ProgressStr, TotalMBStr, LabelStr: string;
  ProgressVal: Integer;
begin
  if not ProgressActive then
  begin
    WizardForm.ProgressGauge.Visible := False;
    WizardForm.ProgressGauge.Left := -1000;
  end;

  if not FileExists(ProgressFile) then Exit;
  if LoadStringFromFile(ProgressFile, AnsiContent) then
  begin
    Content := Utf8Decode(AnsiContent);
    if Pos('CONCLUIDO', Content) > 0 then
    begin
      if not ProgressActive then
      begin
        WizardForm.ProgressGauge.Left := OrigProgressLeft;
        WizardForm.ProgressGauge.Top := OrigProgressTop;
        WizardForm.ProgressGauge.Width := OrigProgressWidth;
        WizardForm.ProgressGauge.Height := OrigProgressHeight;
        ProgressActive := True;
      end;
      WizardForm.ProgressGauge.Position := 100;
      WizardForm.ProgressGauge.Visible := True;
      if ProgressTimerID <> 0 then
      begin
        KillTimer(0, ProgressTimerID);
        ProgressTimerID := 0;
      end;
      Exit;
    end;

    if Pos('ERRO:', Content) > 0 then
    begin
      WizardForm.StatusLabel.Caption := Content;
      if ProgressTimerID <> 0 then
      begin
        KillTimer(0, ProgressTimerID);
        ProgressTimerID := 0;
      end;
      Exit;
    end;

    // Parse Progress=XX
    ProgressPos := Pos('Progress=', Content);
    if ProgressPos > 0 then
    begin
      ProgressStr := Copy(Content, ProgressPos + 9, Length(Content));
      PipePos := Pos('|', ProgressStr);
      if PipePos > 0 then
        ProgressStr := Copy(ProgressStr, 1, PipePos - 1);
      
      ProgressVal := StrToIntDef(ProgressStr, -1);
      if (ProgressVal >= 0) and (ProgressVal <= 100) then
      begin
        if not ProgressActive then
        begin
          WizardForm.ProgressGauge.Left := OrigProgressLeft;
          WizardForm.ProgressGauge.Top := OrigProgressTop;
          WizardForm.ProgressGauge.Width := OrigProgressWidth;
          WizardForm.ProgressGauge.Height := OrigProgressHeight;
          ProgressActive := True;
        end;
        WizardForm.ProgressGauge.Max := 100;
        WizardForm.ProgressGauge.Position := ProgressVal;
        WizardForm.ProgressGauge.Visible := True;
      end;
    end;

    // Parse Label=ZZ and TotalMB=YY to construct nice status message
    LabelPos := Pos('Label=', Content);
    if LabelPos > 0 then
    begin
      LabelStr := Copy(Content, LabelPos + 6, Length(Content));
      PipePos := Pos('|', LabelStr);
      if PipePos > 0 then
        LabelStr := Copy(LabelStr, 1, PipePos - 1);
      
      if LabelStr <> '' then
      begin
        TotalMBPos := Pos('TotalMB=', Content);
        if TotalMBPos > 0 then
        begin
          TotalMBStr := Copy(Content, TotalMBPos + 8, Length(Content));
          PipePos := Pos('|', TotalMBStr);
          if PipePos > 0 then
            TotalMBStr := Copy(TotalMBStr, 1, PipePos - 1);
          
          if (TotalMBStr <> '') and (TotalMBStr <> '0') and (TotalMBStr <> 'Unknown') then
            WizardForm.StatusLabel.Caption := LabelStr + ' (' + TotalMBStr + ' MB)... ' + ProgressStr + '%'
          else
            WizardForm.StatusLabel.Caption := LabelStr + '... ' + ProgressStr + '%';
        end
        else
          WizardForm.StatusLabel.Caption := LabelStr + '...';
      end;
    end;
  end;
end;

procedure InitializeProgress;
begin
  ProgressFile := ExpandConstant('{tmp}\kw_progress.txt');
  if not FileExists(ProgressFile) then
    SaveStringToFile(ProgressFile, '', False);
  
  // Salva dimensÃµes originais
  OrigProgressLeft := WizardForm.ProgressGauge.Left;
  OrigProgressTop := WizardForm.ProgressGauge.Top;
  OrigProgressWidth := WizardForm.ProgressGauge.Width;
  OrigProgressHeight := WizardForm.ProgressGauge.Height;
  
  // Move para fora da tela temporariamente para ocultar durante cÃ³pia de arquivos
  WizardForm.ProgressGauge.Left := -1000;
  WizardForm.ProgressGauge.Position := 0;
  WizardForm.ProgressGauge.Max := 100;
  ProgressActive := False;
  
  ProgressTimerID := SetTimer(0, 0, 500, CreateCallback(@UpdateProgressGauge));
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpInstalling then
    InitializeProgress;
end;

function GetProgressFile(Param: String): String;
begin
  Result := ProgressFile;
end;



procedure DeinitializeSetup();
begin
  if ProgressTimerID <> 0 then
  begin
    KillTimer(0, ProgressTimerID);
    ProgressTimerID := 0;
  end;
end;

procedure InitializeWizard();
begin
  // Ensure progress file exists before installation starts
  ProgressFile := ExpandConstant('{tmp}\kw_progress.txt');
  SaveStringToFile(ProgressFile, '', False);

  // Desce o título e a descrição em todas as telas para otimizar o espaço vazio 
  WizardForm.PageNameLabel.Top := WizardForm.PageNameLabel.Top + 10;
  WizardForm.PageDescriptionLabel.Top := WizardForm.PageDescriptionLabel.Top + 20;
end;

