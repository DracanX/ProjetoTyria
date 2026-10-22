@echo off
setlocal
cd /d "%~dp0.."
set "EXIT_CODE="

echo Downloading the Guild Wars 2 title catalog. Progress appears below.
python -u src\gw2_titles.py --output build\gw2_titles.db
if errorlevel 1 goto :failed

echo.
echo GW2 API title catalog updated. Rebuild the module with build.bat.
pause
exit /b 0

:failed
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo GW2 title catalog update failed with exit code %EXIT_CODE%.
echo The previous catalog, if any, was not replaced.
echo Copy the error message above before closing this window.
pause
exit /b %EXIT_CODE%
