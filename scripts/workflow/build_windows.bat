@echo off

echo ========= OnTheSpot Windows Build Script =========

REM Navigate to the root directory if in scripts
set FOLDER_NAME=%cd%
for %%F in ("%cd%") do set FOLDER_NAME=%%~nxF
if /i "%FOLDER_NAME%"=="scripts" (
    echo You are in the scripts folder. Changing to the parent directory...
    cd ..
)

REM Clean up previous builds
echo => Cleaning up previous builds...
del /F /Q dist\* 2>nul

REM Bundle ffmpeg
echo => Downloading FFmpeg binary...
mkdir build
curl -L https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip -o build\ffmpeg.zip || (
    echo Failed to download FFmpeg. Exiting...
    exit /b 1
)

powershell -Command "Expand-Archive -Path build\ffmpeg.zip -DestinationPath build\ffmpeg" || (
    echo Failed to extract FFmpeg. Exiting...
    exit /b 1
)

mkdir ffbin_win

REM Find the extracted FFmpeg directory
set FFMPEG_DIR=
for /d %%D in ("build\ffmpeg\*") do set FFMPEG_DIR=%%D
if defined FFMPEG_DIR (
    copy "%FFMPEG_DIR%\bin\ffmpeg.exe" ffbin_win\ || (
        echo Failed to copy FFmpeg binary. Exiting...
        exit /b 1
    )
) else (
    echo Failed to find extracted FFmpeg directory. Exiting...
    exit /b 1
)

REM Build with PyInstaller
echo => Building executable with PyInstaller...
pyinstaller --onefile --noconsole --noconfirm ^
    --hidden-import=zeroconf._utils.ipaddress ^
    --hidden-import=zeroconf._handlers.answers ^
    --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
    --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" ^
    --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" ^
    --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
    --add-binary="ffbin_win/ffmpeg.exe;onthespot/bin/ffmpeg" ^
    --paths=src/onthespot ^
    --name=onthespot_windows ^
    --icon=src/onthespot/resources/icons/onthespot.png ^
    src\portable.py || (
    echo PyInstaller build failed. Exiting...
    exit /b 1
)

REM Move the executable to artifacts folder
echo => Moving executable to artifacts folder...
mkdir artifacts
mkdir artifacts\windows
move dist\onthespot_windows.exe artifacts\windows\

REM Clean up unnecessary files
echo => Cleaning up temporary files...
del /F /Q *.spec 2>nul
rd /s /q build 2>nul
rd /s /q __pycache__ 2>nul
rd /s /q ffbin_win 2>nul

echo => Done!
