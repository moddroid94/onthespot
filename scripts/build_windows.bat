@echo off

set FOLDER_NAME=%cd%
for %%F in ("%cd%") do set FOLDER_NAME=%%~nxF
if /i "%FOLDER_NAME%"=="scripts" (
    echo You are in the scripts folder. Changing to the parent directory...
    cd ..
)

echo ========= OnTheSpot Windows Build Script =========


echo =^> Cleaning up previous builds...
del /F /Q /A dist\onthespot_win_executable.exe


echo =^> Creating virtual environment...
python -m venv venvwin


echo =^> Activating virtual environment...
call venvwin\Scripts\activate.bat


echo =^> Installing dependencies via pip...
python -m pip install --upgrade pip wheel pyinstaller
pip install -r requirements.txt


echo =^> Downloading FFmpeg binary...
mkdir build
curl -L -o build\ffmpeg.zip https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip
powershell -Command "Expand-Archive -Path build\ffmpeg.zip -DestinationPath build\ffmpeg"


echo =^> Running PyInstaller to create .exe package...
pyinstaller --onefile --noconsole --noconfirm ^
    --hidden-import="zeroconf._utils.ipaddress" ^
    --hidden-import="zeroconf._handlers.answers" ^
    --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
    --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" ^
    --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" ^
    --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
    --add-binary="build/ffmpeg/ffmpeg-7.1-essentials_build/bin/ffmpeg.exe;onthespot/bin/ffmpeg" ^
    --paths="src/onthespot" ^
    --name="OnTheSpot" ^
    --icon="src/onthespot/resources/icons/onthespot.png" ^
    src\portable.py


echo =^> Cleaning up temporary files...
del /F /Q *.spec
rmdir /s /q build __pycache__ ffbin_win venvwin


echo =^> Done! Executable available as 'dist/OnTheSpot.exe'.
