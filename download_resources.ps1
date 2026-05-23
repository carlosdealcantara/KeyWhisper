param (
    [string]$ProgressFile  = "",
    [string]$SelectedLanguage = "brazilianportuguese"
)

# Force console output to UTF-8 to fix Inno Setup mojibake
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Force TLS 1.2 for all HTTPS requests
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Common request headers (User-Agent)
$Headers = @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
$ErrorActionPreference = "Stop"

$AppData   = [Environment]::GetFolderPath("ApplicationData")
$KwDir     = Join-Path $AppData "KeyWhisper"
$EngineDir = Join-Path $KwDir "engine"
$ModelsDir = Join-Path $KwDir "models"
$OutputDir = Join-Path $KwDir "output"

# Garante que as pastas de destino existam
New-Item -ItemType Directory -Force -Path $KwDir    | Out-Null
New-Item -ItemType Directory -Force -Path $EngineDir | Out-Null
New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir  | Out-Null

# Função para reportar progresso ao Inno Setup via arquivo temporário
function Write-Progress-File {
    param([string]$Message)
    if ($ProgressFile -ne "") {
        try {
            [IO.File]::WriteAllText($ProgressFile, $Message, [System.Text.Encoding]::Default)
        } catch {}
    }
    # Also log progress messages to the transcript for debugging
    if ($null -ne $Message) { Write-Host $Message }
}

# Função para encerrar processos que possam bloquear arquivos de modelo/engine
function Stop-KeyWhisperProcess {
    try {
        Get-Process -Name "WhisperDesktop" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
    } catch {}
}

# Função para remover arquivos que podem estar bloqueados
function Remove-FileIfLocked {
    param([string]$Path)
    $maxAttempts = 5
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        if (-not (Test-Path $Path)) { return }
        try {
            Remove-Item $Path -Force -ErrorAction Stop
            return
        } catch {
            # Attempt to stop any locking process
            Stop-KeyWhisperProcess
            Start-Sleep -Seconds 2
        }
    }
    # Final attempt, suppress errors
    try { Remove-Item $Path -Force -ErrorAction SilentlyContinue } catch {}
}

# Start transcript for detailed logging


# Tradução do progresso baseada no idioma selecionado
$IsPt = $SelectedLanguage -like "*portuguese*" -or $SelectedLanguage -like "*brazilian*"
$IsEs = $SelectedLanguage -like "*spanish*"

$MsgStarting = if ($IsPt) { "Iniciando instalação..." } elseif ($IsEs) { "Iniciando instalación..." } else { "Starting installation..." }
$MsgCheckModel = if ($IsPt) { "Verificando modelo de IA..." } elseif ($IsEs) { "Verificando modelo de IA..." } else { "Checking AI model..." }
$MsgModelExists = if ($IsPt) { "Modelo já instalado. Pulando download." } elseif ($IsEs) { "Modelo ya instalado. Omitiendo descarga." } else { "Model already installed. Skipping download." }
$MsgCheckEngine = if ($IsPt) { "Verificando motor de transcrição..." } elseif ($IsEs) { "Verificando motor de transcripción..." } else { "Checking transcription engine..." }
$MsgEngineExists = if ($IsPt) { "Motor já instalado. Pulando download." } elseif ($IsEs) { "Motor ya instalado. Omitiendo descarga." } else { "Engine already installed. Skipping download." }
$MsgExtractEngine = if ($IsPt) { "Extraindo motor de transcrição..." } elseif ($IsEs) { "Extrayendo motor de transcripción..." } else { "Extracting transcription engine..." }
$MsgConfig = if ($IsPt) { "Aplicando configurações..." } elseif ($IsEs) { "Aplicando configuraciones..." } else { "Applying settings..." }
$MsgSuccess = if ($IsPt) { "Motor baixado com sucesso!" } elseif ($IsEs) { "¡Motor descargado con éxito!" } else { "Engine successfully downloaded!" }

# Modelo fixo: Small (~466MB) — melhor custo-benefício para transcrição em tempo real
$ModelUrl  = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
$ModelDest = Join-Path $ModelsDir "ggml-small.bin"
$ExpectedMinSize = 440 * 1MB

# URL estável da Engine WhisperDesktop (releases Const-me)
$EngineUrl  = "https://github.com/Const-me/Whisper/releases/download/1.12.0/WhisperDesktop.zip"
$ZipDest    = Join-Path $EngineDir "engine.zip"
$EngineDest = Join-Path $EngineDir "WhisperDesktop.exe"

# Função robusta de download com fallback
function Download-FileWithRetry {
    param (
        [string]$Url,
        [string]$Destination,
        [string]$Label,
        [long]$MinSize = 10MB,
        [int]$StartPercent = 0,
        [int]$EndPercent = 100
    )
    $Headers = @{'User-Agent'='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # Detect if this is the engine download (URL matches EngineUrl)
    $isEngine = $Url -eq $EngineUrl
    # Skip HEAD size verification for engine (header often missing)
    if (-not $isEngine) {
        # Verifica tamanho esperado via HEAD antes de iniciar download
        try {
            $head = Invoke-WebRequest -Method Head -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
            $contentLength = $head.Headers["Content-Length"]
            if ($null -ne $contentLength) {
                $contentLength = [int64]$contentLength
                if ($contentLength -gt 0 -and $contentLength -lt $MinSize) {
                    throw "Servidor informou tamanho de download (${contentLength/1MB:N2} MB) menor que o mínimo esperado (${MinSize/1MB:N2} MB)."
                }
            }
        } catch {
            $msg = "Erro ao obter tamanho do arquivo via HEAD para ${Label}: $_"
            Write-Progress-File $msg
            # Continua mesmo se falhar na verificação de HEAD
        }
    }
    
    $retries = 5
    for ($i = 1; $i -le $retries; $i++) {
        try {
            $msgLabel = if ($IsPt) { "Baixando $Label... (Tentativa ${i}/${retries})" } elseif ($IsEs) { "Descargando $Label... (Intento ${i}/${retries})" } else { "Downloading $Label... (Attempt ${i}/${retries})" }
            Write-Progress-File "Progress=$StartPercent|TotalMB=0|Label=$msgLabel"

            # Define dedicated temp directory
            $TempDir = Join-Path $KwDir "temp_downloads"
            if (-not (Test-Path $TempDir)) { New-Item -ItemType Directory -Path $TempDir | Out-Null }
            
            # Generate a unique temporary file name for this attempt within temp directory
            $TempFileName = "$(Split-Path $Destination -Leaf).$([guid]::NewGuid()).tmp"
            $TempPath = Join-Path $TempDir $TempFileName
            # Ensure any previous temp file is removed (in case of leftover)
            if (Test-Path $TempPath) { Remove-FileIfLocked $TempPath }
            
            # Chunked Download using .NET HttpWebRequest for real progress reporting
            Write-Progress-File "Progress=$StartPercent|TotalMB=0|Label=Conectando ao servidor..."
            $request = [System.Net.HttpWebRequest]::Create($Url)
            $request.UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            $request.Timeout = 600000 # 10 minutes
            $request.Method = "GET"
            
            $response = $request.GetResponse()
            $totalBytes = $response.ContentLength
            $totalMB = [Math]::Round($totalBytes / 1MB, 1)
            
            $responseStream = $response.GetResponseStream()
            $fileStream = [System.IO.File]::Create($TempPath)
            
            $buffer = New-Object byte[] 65536
            $downloaded = 0
            $lastProgressTime = 0
            
            while (($read = $responseStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $fileStream.Write($buffer, 0, $read)
                $downloaded += $read
                
                $currentTime = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                if ($currentTime - $lastProgressTime -gt 250 -or $downloaded -eq $totalBytes) {
                    $lastProgressTime = $currentTime
                    if ($totalBytes -gt 0) {
                        $percent = ($downloaded / $totalBytes) * 100
                        $overallPercent = $StartPercent + [Math]::Floor(($percent / 100) * ($EndPercent - $StartPercent))
                        Write-Progress-File "Progress=$overallPercent|TotalMB=$totalMB|Label=$Label"
                    } else {
                        Write-Progress-File "Progress=$StartPercent|TotalMB=0|Label=$Label ($([Math]::Round($downloaded/1MB,1)) MB)..."
                    }
                }
            }
            
            $fileStream.Close()
            $responseStream.Close()
            $response.Close()
            
            # Verifica tamanho final do arquivo temporário
            if (Test-Path $TempPath) {
                $size = (Get-Item $TempPath).Length
                if ($size -ge $MinSize) {
                     # Ensure no process is holding the destination file
                     Stop-KeyWhisperProcess
                     Move-Item -Force $TempPath $Destination
                     $msgSuccess = if ($IsPt) { "Concluído: $Label" } elseif ($IsEs) { "Completado: $Label" } else { "Completed: $Label" }
                     Write-Progress-File "Progress=$EndPercent|TotalMB=$totalMB|Label=$msgSuccess"
                     return $true
                } else {
                    Remove-Item $TempPath -Force -ErrorAction SilentlyContinue
                    throw "Arquivo baixado tem tamanho insuficiente ($([Math]::Round($size/1MB,2)) MB)."
                }
            } else {
                throw "Arquivo não encontrado após a transferência."
            }
        }
        catch {
            # Ensure streams are closed
            if ($null -ne $fileStream) { try { $fileStream.Close() } catch {} }
            if ($null -ne $responseStream) { try { $responseStream.Close() } catch {} }
            if ($null -ne $response) { try { $response.Close() } catch {} }

            # Ensure any leftover temp files are cleaned before fallback
            if (Test-Path $TempPath) {
                try {
                    Remove-Item $TempPath -Force -ErrorAction Stop
                } catch {
                    Stop-KeyWhisperProcess
                    Remove-Item $TempPath -Force -ErrorAction SilentlyContinue
                }
            }
            $errText = $_
            $msgRetryErr = if ($IsPt) { "Erro na tentativa ${i}: $errText" } elseif ($IsEs) { "Error en el intento ${i}: $errText" } else { "Error on attempt ${i}: $errText" }
            Write-Progress-File "Progress=$StartPercent|TotalMB=0|Label=$msgRetryErr"
            
            Start-Sleep -Seconds (5 * $i)
        }
    }
    return $false
}

Write-Progress-File "Progress=2|TotalMB=0|Label=$MsgStarting"

# ─── 1. Download do Modelo de IA ─────────────────────────────────────────────
Write-Progress-File "Progress=5|TotalMB=0|Label=$MsgCheckModel"
$modelSuccess = $false

# Se o arquivo kw_progress.txt já contiver "CONCLUIDO", pula o download
if ($ProgressFile -ne "" -and (Test-Path $ProgressFile)) {
    $c = Get-Content $ProgressFile -Raw
    if ($c -like "*CONCLUIDO*") {
        Write-Progress-File "Progress=70|TotalMB=0|Label=Instalação rápida: Pescando modelo já existente."
        $modelSuccess = $true
    }
}

if (-not $modelSuccess -and (Test-Path $ModelDest)) {
    $existingSize = (Get-Item $ModelDest).Length
    if ($existingSize -ge $ExpectedMinSize) {
        Write-Progress-File "Progress=70|TotalMB=0|Label=$MsgModelExists"
        $modelSuccess = $true
    } else {
        $msgCorrupted = if ($IsPt) { "Modelo existente está corrompido ($([Math]::Round($existingSize / 1MB, 1)) MB). Baixando novamente..." } elseif ($IsEs) { "Modelo existente está dañado ($([Math]::Round($existingSize / 1MB, 1)) MB). Descargando de nuevo..." } else { "Existing model is corrupted ($([Math]::Round($existingSize / 1MB, 1)) MB). Downloading again..." }
        Write-Progress-File "Progress=5|TotalMB=0|Label=$msgCorrupted"
        Remove-Item $ModelDest -Force -ErrorAction SilentlyContinue
    }
}

if (-not $modelSuccess) {
    $lblModel = if ($IsPt) { "Modelo de IA (Small)" } elseif ($IsEs) { "Modelo de IA (Small)" } else { "AI Model (Small)" }
    $modelSuccess = Download-FileWithRetry -Url $ModelUrl -Destination $ModelDest -Label $lblModel -MinSize $ExpectedMinSize -StartPercent 5 -EndPercent 70
}

# ─── 2. Download e Extração da Engine ────────────────────────────────────────
Write-Progress-File "Progress=70|TotalMB=0|Label=$MsgCheckEngine"
$engineSuccess = $false

if ((Test-Path $EngineDest) -and (Test-Path (Join-Path $EngineDir "Whisper.dll"))) {
    $exeSize = (Get-Item $EngineDest).Length
    $dllSize = (Get-Item (Join-Path $EngineDir "Whisper.dll")).Length
    if ($exeSize -gt 5MB -and $dllSize -gt 5MB) {
        Write-Progress-File "Progress=90|TotalMB=0|Label=$MsgEngineExists"
        $engineSuccess = $true
    } else {
        Remove-Item $EngineDest -Force -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $EngineDir "Whisper.dll") -Force -ErrorAction SilentlyContinue
    }
}

if (-not $engineSuccess) {
    $lblEngine = if ($IsPt) { "Motor de Transcrição" } elseif ($IsEs) { "Motor de Transcripción" } else { "Transcription Engine" }
    $zipSuccess = Download-FileWithRetry -Url $EngineUrl -Destination $ZipDest -Label $lblEngine -MinSize 100KB -StartPercent 70 -EndPercent 90
    
    if ($zipSuccess) {
        try {
            Write-Progress-File "Progress=90|TotalMB=0|Label=$MsgExtractEngine"
            Expand-Archive -Path $ZipDest -DestinationPath $EngineDir -Force
            Remove-Item $ZipDest -Force -ErrorAction SilentlyContinue
            # After extracting WhisperDesktop, remove any stray whisper-stream.exe to avoid engine conflict
            try { Remove-Item -Path (Join-Path $EngineDir "whisper-stream.exe") -Force -ErrorAction SilentlyContinue } catch {}
            $engineSuccess = Test-Path $EngineDest
        }
        catch {
            $engineSuccess = $false
            $errExtract = $_
            Write-Progress-File "Progress=90|TotalMB=0|Label=Erro: $errExtract"
        }
    }
}

# ─── 3. Configuração Final ────────────────────────────────────────────────────
if ($modelSuccess -and $engineSuccess) {
    try {
        Write-Progress-File "Progress=95|TotalMB=0|Label=$MsgConfig"

        $TranscriptPath = Join-Path $OutputDir "transcript.txt"
        if (-not (Test-Path $TranscriptPath)) {
            New-Item -ItemType File -Path $TranscriptPath -Force | Out-Null
        }

        # Carrega ou cria config.json
        $ConfigFile = Join-Path $KwDir "config.json"
        $Config = @{}
        if (Test-Path $ConfigFile) {
            try { $Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json -AsHashtable } catch {}
        }

        # Define idioma no formato esperado pelo KeyWhisper ('pt', 'en', 'es', 'auto')
        $ConfigLanguage = "pt"
        if ($SelectedLanguage -like "*english*") {
            $ConfigLanguage = "en"
        } elseif ($SelectedLanguage -like "*spanish*") {
            $ConfigLanguage = "es"
        }

        $Config["model_name"]             = "ggml-small.bin"
        $Config["file_path"]              = $TranscriptPath
        if (-not $Config.ContainsKey("hotkey"))                  { $Config["hotkey"]                  = "f9" }
        if (-not $Config.ContainsKey("bridge_enabled"))          { $Config["bridge_enabled"]           = $false }
        if (-not $Config.ContainsKey("toast_enabled"))           { $Config["toast_enabled"]            = $true }
        if (-not $Config.ContainsKey("show_welcome_on_startup")) { $Config["show_welcome_on_startup"]  = $true }
        
        # Mapeia idioma que o usuário escolheu no instalador
        $Config["language"]               = $ConfigLanguage
        
        if (-not $Config.ContainsKey("gpu_acceleration"))        { $Config["gpu_acceleration"]         = $true }
        if (-not $Config.ContainsKey("step_ms"))                 { $Config["step_ms"]                  = 500 }
        if (-not $Config.ContainsKey("length_ms"))               { $Config["length_ms"]                = 5000 }

        $ConfigJson = $Config | ConvertTo-Json -Depth 4
        [IO.File]::WriteAllText($ConfigFile, $ConfigJson)

        # Limpa marcas de erro antigas se tudo ocorreu bem
        $ErrorLog = Join-Path $KwDir "setup_error.txt"
        if (Test-Path $ErrorLog) { Remove-Item $ErrorLog -Force }

        Write-Progress-File "CONCLUIDO"
    }
    catch {
        $msg = "Erro ao salvar configuração: $_"
        Write-Progress-File "ERRO: $msg"
        $msg | Out-File (Join-Path $KwDir "setup_error.txt")
    }
} else {
    $errFinal = if ($IsPt) { "Falha no download dos recursos. Verifique a conexão com a internet." } elseif ($IsEs) { "Error al descargar recursos. Revise su conexión a Internet." } else { "Failed to download resources. Please check your internet connection." }
    Write-Progress-File "ERRO: $errFinal"
    $errFinal | Out-File (Join-Path $KwDir "setup_error.txt")
}
try { Stop-Transcript } catch {}
