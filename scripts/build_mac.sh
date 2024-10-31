#!/bin/bash

echo "========= OnTheSpot macOS Build Script =========="


echo " => Cleaning up previous builds!"
rm -rf dist/onthespot_mac.app dist/onthespot_mac_ffm.app


echo " => Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate


echo " => Upgrading pip and installing necessary dependencies..."
venv/bin/pip install --upgrade pip wheel pyinstaller
venv/bin/pip install -r requirements.txt


echo " => Running PyInstaller to create .app package..."
mkdir build
wget https://evermeet.cx/ffmpeg/ffmpeg-7.1.zip -O build/ffmpeg.zip
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
mkdir -p dist/OnTheSpot
mv dist/OnTheSpot.app dist/OnTheSpot/OnTheSpot.app
ln -s /Applications dist/OnTheSpot
hdiutil create -srcfolder dist/OnTheSpot -format UDZO -o dist/OnTheSpot.dmg

echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec

echo " => Done! .dmg available in 'dist/OnTheSpot.dmg'."