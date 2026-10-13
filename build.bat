@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo        FastTranslate - Dong goi ung dung Windows (.exe)
echo ========================================================
echo.

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller chua duoc cai dat trong .venv.
    echo Dang cai dat pyinstaller...
    ".venv\Scripts\pip.exe" install pyinstaller
)

echo [1/2] Dang build file FastTranslate.exe bang PyInstaller...
".venv\Scripts\pyinstaller.exe" FastTranslate.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build that bai voi ma loi %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Build thanh cong!
echo File thuc thi: dist\FastTranslate.exe
echo.
echo ========================================================
endlocal
