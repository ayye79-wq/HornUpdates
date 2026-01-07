@echo off
set SRC=C:\Users\ayye7\Desktop\Horn UpdatesDN
set DEST=C:\Users\ayye7\Desktop\HornUpdates

xcopy "%SRC%\index.html" "%DEST%\" /Y
xcopy "%SRC%\style.css" "%DEST%\" /Y
xcopy "%SRC%\script.js" "%DEST%\" /Y
xcopy "%SRC%\articles.json" "%DEST%\" /Y

cd /d "%DEST%"
git add .
git commit -m "Auto update articles.json"
git push
