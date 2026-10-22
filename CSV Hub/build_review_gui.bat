@echo off
setlocal
cd /d "%~dp0.."

python -m pip install customtkinter pyinstaller
if errorlevel 1 goto :failed

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name CSV_Hub --paths src --collect-all customtkinter ^
    --specpath build --workpath build\csv_hub_work --distpath dist ^
    --exclude-module ctranslate2 --exclude-module sentencepiece ^
    --exclude-module xxhash --exclude-module numpy "CSV Hub\review_gui.py"
if errorlevel 1 goto :failed

if exist "build\csv_hub_work" rmdir /s /q "build\csv_hub_work"
if exist "build\CSV_Hub" rmdir /s /q "build\CSV_Hub"
if exist "build\CSV_Hub.spec" del /q "build\CSV_Hub.spec"
if exist "CSV_Hub.spec" del /q "CSV_Hub.spec"

echo.
echo Compilacao concluida. Executavel standalone: dist\CSV_Hub.exe
pause
exit /b 0

:failed
echo.
echo Falha ao compilar o CSV Hub. Codigo: %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%
