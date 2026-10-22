@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "EXIT_CODE="
set "STAGE_DIR=build\release_staging"

set "MODEL_DIR=build\opus-mt-tc-big-en-pt-ct2-int8"
if not exist "%MODEL_DIR%\model.bin" (
    echo OPUS-MT tc-big has not been prepared.
    echo Run src\prepare_opus.bat first; it downloads and converts the model.
    set "EXIT_CODE=1"
    goto :failed
)
if not exist "%MODEL_DIR%\source.spm" (
    echo OPUS-MT source tokenizer is missing. Run src\prepare_opus.bat again with a new output directory.
    set "EXIT_CODE=1"
    goto :failed
)
if not exist "%MODEL_DIR%\target.spm" (
    echo OPUS-MT target tokenizer is missing. Run src\prepare_opus.bat again with a new output directory.
    set "EXIT_CODE=1"
    goto :failed
)

python -m pip install -r src\requirements.txt pyinstaller
if errorlevel 1 goto :failed

python -m PyInstaller --noconsole --onedir --noconfirm --name "Tradução Brasileira" --paths src --collect-all ctranslate2 --hidden-import xxhash --distpath "%STAGE_DIR%" --workpath "build\pyinstaller_work" --specpath "build\pyinstaller_spec" src\module.py
if errorlevel 1 goto :failed

if not exist "%STAGE_DIR%\Tradução Brasileira\PT_BR" mkdir "%STAGE_DIR%\Tradução Brasileira\PT_BR"
robocopy "%MODEL_DIR%" "%STAGE_DIR%\Tradução Brasileira\PT_BR\model" /E /NFL /NDL /NJH /NJS /NC /NS
if errorlevel 8 goto :failed
if exist "build\gw2_titles.db" copy /y "build\gw2_titles.db" "%STAGE_DIR%\Tradução Brasileira\PT_BR\gw2_titles.db" >nul
if not exist "build\gw2_titles.db" echo Warning: no GW2 API title catalog found; run src\sync_gw2_titles.bat and rebuild to enable title bypass.
if not exist "dist\Tradução Brasileira" mkdir "dist\Tradução Brasileira"
robocopy "%STAGE_DIR%\Tradução Brasileira" "dist\Tradução Brasileira" /E /NFL /NDL /NJH /NJS /NC /NS
if errorlevel 8 goto :failed
echo.
echo Build completed successfully. Output: dist\Tradução Brasileira
pause
exit /b 0

:failed
if not defined EXIT_CODE set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Build failed with exit code %EXIT_CODE%.
echo Copy the error message above before closing this window.
pause
exit /b %EXIT_CODE%
