@echo off
echo [INFO] Running HornUpdates refresh...

REM Change to the directory where this .bat file lives
cd /d "%~dp0"

REM Update articles
echo [STEP] Updating articles.json...
python update_articles.py

REM Build reader sitemap
echo [STEP] Building reader sitemap...
python build_reader_sitemap.py

echo.
echo [SUCCESS] Articles + sitemap updated.
pause
