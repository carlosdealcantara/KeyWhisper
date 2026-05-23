@echo off
chcp 65001 > nul
echo ===================================================
echo   KeyWhisper v2.0 - Pipeline de Compilacao Limpa
echo ===================================================
echo.

:: Usa o ambiente virtual local do projeto (sem dependencia de disco externo)
set VENV_PYTHON=%~dp0env\Scripts\python.exe
set VENV_PYINSTALLER=%~dp0env\Scripts\pyinstaller.exe

:: Valida que o ambiente virtual existe
if not exist "%VENV_PYINSTALLER%" (
    echo [ERRO] PyInstaller nao encontrado em: %VENV_PYINSTALLER%
    echo Execute: python -m venv env  e depois  env\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/4] Limpando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [2/4] Compilando KeyWhisper.exe com PyInstaller...

"%VENV_PYINSTALLER%" ^
    --noconfirm ^
    --clean ^
    KeyWhisper.spec

if errorlevel 1 (
    echo.
    echo [ERRO] Compilacao falhou! Verifique o log acima.
    pause
    exit /b 1
)

echo [3/4] Compilacao concluida com sucesso!
echo.

:: ═══════════════════════════════════════════════════════
::  LIMPEZA AUTOMATICA POS-BUILD
::  Remove artefatos intermediarios do PyInstaller que
::  inflam o workspace (build/ tem ~22 MB de lixo).
::  O unico resultado necessario e: dist\KeyWhisper.exe
:: ═══════════════════════════════════════════════════════
echo [4/4] Limpando artefatos intermediarios...
if exist build rmdir /s /q build
if exist build_log.txt del /q build_log.txt
if exist iscc_log.txt del /q iscc_log.txt

echo.
echo ===================================================
echo  Executavel gerado em: dist\KeyWhisper.exe
echo  Artefatos intermediarios removidos automaticamente.
echo  Pronto para empacotar com o Inno Setup!
echo ===================================================
pause
