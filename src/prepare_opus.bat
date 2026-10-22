@echo off
setlocal
cd /d "%~dp0.."
set "EXIT_CODE="

python -m pip install -r src\requirements.txt "transformers[torch]>=4.44,<5"
if errorlevel 1 goto :failed

python src\prepare_opus.py
if errorlevel 1 goto :failed

echo.
echo OPUS-MT preparation completed successfully.
pause
exit /b 0

:failed
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo OPUS-MT preparation failed with exit code %EXIT_CODE%.
echo Copy the error message above before closing this window.
pause
exit /b %EXIT_CODE%
