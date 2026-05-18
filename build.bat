@echo off
echo ===================================================
echo Iniciando a compilacao do KeyWhisper (Modo GPU)...
echo ===================================================

:: Comando do PyInstaller usando o ambiente do Disco D
D:\KeyWhisper_env\Scripts\pyinstaller.exe --onedir --console -y --collect-all customtkinter --collect-all faster_whisper --add-data "D:\KeyWhisper_env\Lib\site-packages\nvidia\cublas\bin\*;." --add-data "D:\KeyWhisper_env\Lib\site-packages\nvidia\cudnn\bin\*;." --add-data "D:\KeyWhisper_env\Lib\site-packages\nvidia\cuda_nvrtc\bin\*;." --distpath D:\KeyWhisper_dist --name KeyWhisper main.py

echo.
echo ===================================================
echo Compilacao concluida! 
echo O resultado esta em: D:\KeyWhisper_dist\KeyWhisper
echo ===================================================
pause
