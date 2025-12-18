@echo off
echo [INFO] Running HornUpdates refresh...

REM Change to the directory where this .bat file lives
cd /d "%~dp0"

REM Run the Python script
python update_articles.py

echo.
echo [INFO] Finished HornUpdates refresh.
pause
