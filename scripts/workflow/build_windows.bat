@echo off

echo ========= OnTheSpot Windows Build Script =========

REM Get the directory of the script
SET SCRIPT_DIR=%~dp0
CD /D "%SCRIPT_DIR%\..\.."

echo Current directory: %CD%

REM Clean up previous builds
echo => Cleaning up previous builds...
IF EXIST dist (
    RMDIR /S /Q dist
)
IF EXIST build (
    RMDIR /S /Q build
)
IF EXIST artifacts\windows (
    RMDIR /S /Q artifacts\windows
)
mkdir artifacts\windows

REM Build with PyInstaller
echo => Building executable with PyInstaller...
pyinstaller --onefile --noconsole --noconfirm ^
    --hidden-import=zeroconf._utils.ipaddress ^
    --hidden-import=zeroconf._handlers.answers ^
    --add-data "src\onthespot\gui\qtui\*.ui;onthespot/gui/qtui" ^
    --add-data "src\onthespot\resources\icons\*.png;onthespot/resources/icons" ^
    --add-data "src\onthespot\resources\themes\*.qss;onthespot/resources/themes" ^
    --add-data "src\onthespot\resources\translations\*.qm;onthespot/resources/translations" ^
    --name onthespot_windows ^
    --icon src\onthespot\resources\icons\onthespot.ico ^
    src\portable.py

IF EXIST dist\onthespot_windows.exe (
    echo => Build succeeded.
    copy dist\onthespot_windows.exe artifacts\windows\
) ELSE (
    echo => Build failed.
    exit /b 1
)

REM Clean up unnecessary files
del /F /Q *.spec
RMDIR /S /Q build
RMDIR /S /Q __pycache__

echo => Done!
