@echo off
cd /d "%~dp0"
echo ===================================================
echo   FastTranslate - Che do Debug Truc Quan
echo   Nhan Alt+D       : Dich van ban boi den
echo   Nhan Alt+Shift+D : Chup man hinh dich OCR
echo ===================================================
"%~dp0.venv\Scripts\python.exe" "%~dp0src\main.py"
pause
