@echo off
echo  =^> Installing 'pyinstaller' via pip...
pip install --upgrade pip
pip install wheel
pip install pyinstaller
echo  =^> Installing dependencies pip...
pip install winsdk
pip install -r requirements.txt
if exist ffbin_win\ffmpeg.exe (
    echo =^> Found 'ffbin_win' directory and ffmpeg binary.. Using ffmpeg binary append mode
    pyinstaller --onefile --noconsole --noconfirm --hidden-import="zeroconf._utils.ipaddress" --hidden-import="zeroconf._handlers.answers" --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" --add-binary="ffbin_win/*.exe;onthespot/bin/ffmpeg" --paths="src/onthespot" --name="onthespot_win_ffm" --icon="src/onthespot/resources/icons/onthespot.png" src\portable.py
) else (
    echo  =^> Building to use ffmpeg binary from system...
    pyinstaller --onefile --noconsole --noconfirm --hidden-import="zeroconf._utils.ipaddress" --hidden-import="zeroconf._handlers.answers" --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources" --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" --paths="src/onthespot" --name="onthespot_win" --icon="src/onthespot/resources/icons/onthespot.png" src\portable.py
)
echo  =^> Cleaning..
if exist onthespot_win.spec (
    del /F /Q /A onthespot_win.spec
)
if exist onthespot_win_ffm.spec (
    del /F /Q /A onthespot_win_ffm.spec
)
if exist build\ (
    rmdir build /s /q
)

if exist __pycache__\ (
    rmdir __pycache__ /s /q
)
if exist venvwin\ (
    rmdir venvwin /s /q
)

echo  =^> Done
