@echo off
setlocal
cd /d "%~dp0.."
python "CSV Hub\review_gui.py"
if errorlevel 1 (
    echo.
    echo A interface nativa de revisão foi encerrada com erro.
    pause
)
