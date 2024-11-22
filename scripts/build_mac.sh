#!/bin/bash

echo "========= OnTheSpot macOS Build Script =========="


echo " => Cleaning up previous builds!"
rm -rf dist


echo " => Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate


echo " => Upgrading pip and installing necessary dependencies..."
venv/bin/pip install --upgrade pip wheel pyinstaller
venv/bin/pip install -r requirements.txt


echo " => Running PyInstaller to create .app package..."
mkdir build
curl -L -o build/ffmpeg.zip https://evermeet.cx/ffmpeg/ffmpeg-7.1.zip
unzip build/ffmpeg.zip -d build
pyinstaller --windowed \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    --add-binary="build/ffmpeg:onthespot/bin/ffmpeg" \
    --paths="src/onthespot" \
    --name="OnTheSpot" \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py


echo " => Setting executable permissions..."
chmod +x dist/OnTheSpot.app


echo " => Creating dmg..."
mkdir -p dist/dmg
mv dist/OnTheSpot.app dist/dmg/OnTheSpot.app
ln -s /Applications dist/dmg

echo "# Login Issues
Newer versions of macOS have restricted networking features
for apps inside the 'Applications' folder. To login to your
account you will need to:

1. Run the following command in terminal, 'echo \"127.0.0.1 \$HOST\" | sudo tee -a /etc/hosts'

2. Launch the app and click add account before dragging into the applications folder.

3. After successfully logging in you can drag the app into the folder.


# Security Issues
After all this, if you experience an error while trying to launch
the app you will need to open the 'Applications' folder, right-click
the app, and click open anyway." > dist/dmg/readme.txt

hdiutil create -srcfolder dist/dmg -format UDZO -o dist/OnTheSpot.dmg


echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec

echo " => Done! .dmg available in 'dist/OnTheSpot.dmg'."
