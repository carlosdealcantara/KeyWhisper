@echo off
chcp 65001 > nul
echo ===================================================
echo   KeyWhisper - Limpeza do Workspace
echo ===================================================
echo.
echo Este script remove artefatos de build e arquivos
echo temporarios que inflam o workspace para o Antigravity.
echo.

set /p CONFIRM="Deseja continuar? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Cancelado.
    pause
    exit /b 0
)

echo.
echo [1/5] Removendo pasta build/ (artefatos PyInstaller)...
if exist build (
    rmdir /s /q build
    echo       Removido: build/ 
) else (
    echo       Ja limpo: build/
)

echo [2/5] Removendo pasta dist/ (executavel compilado)...
if exist dist (
    rmdir /s /q dist
    echo       Removido: dist/
) else (
    echo       Ja limpo: dist/
)

echo [3/5] Removendo __pycache__/...
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo       Removido: __pycache__/
) else (
    echo       Ja limpo: __pycache__/
)

echo [4/5] Removendo logs de compilacao...
if exist build_log.txt (
    del /q build_log.txt
    echo       Removido: build_log.txt
)
if exist iscc_log.txt (
    del /q iscc_log.txt
    echo       Removido: iscc_log.txt
)

echo [5/5] Removendo ZIPs de teste do engine...
if exist engine_test.zip (
    del /q engine_test.zip
    echo       Removido: engine_test.zip
)
if exist engine_test3.zip (
    del /q engine_test3.zip
    echo       Removido: engine_test3.zip
)

echo.
echo ===================================================
echo  Limpeza concluida!
echo  Apenas o codigo-fonte Python permanece no workspace.
echo ===================================================
pause
