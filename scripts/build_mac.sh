#!/bin/bash

echo "========= OnTheSpot MacOS Build Script =========="

# Check the current folder and change directory if necessary
FOLDER_NAME=$(basename "$PWD")

if [ "$FOLDER_NAME" == "scripts" ]; then
    echo "You are in the scripts folder. Changing to the parent directory..."
    cd ..
elif [ "$FOLDER_NAME" != "onthespot" ]; then
    echo "Make sure that you are inside the project folder. Current folder is: $FOLDER_NAME"
    exit 1
fi

# Clean up previous builds
echo " => Cleaning up!"
rm -rf ./dist/onthespot_mac.app ./dist/onthespot_mac_ffm.app

# Create virtual environment
echo " => Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo " => Activating virtual environment..."
source ./venv/bin/activate

# Upgrade pip and install dependencies
echo " => Upgrading pip and installing dependencies using Bash..."
venv/bin/pip install --upgrade pip wheel pyinstaller

# Install project-specific dependencies
echo " => Installing project-specific dependencies..."
venv/bin/pip install -r requirements.txt

# Check for FFmpeg binary and set build options
NAME="OnTheSpot"
if [ -f "ffbin_mac/ffmpeg" ]; then
    echo " => Found 'ffbin_mac' directory and ffmpeg binary. Including FFmpeg in the build."
    FFBIN='--add-binary=ffbin_mac/*:onthespot/bin/ffmpeg'
else
    echo " => FFmpeg binary not found. Building without it."
fi

# Run PyInstaller to create the app
pyinstaller --windowed \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name=$NAME \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py

# Set executable permissions
echo " => Setting executable permissions..."
chmod +x ./dist/OnTheSpot.app

# Clean up unnecessary files
echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec

echo " => Done!"
