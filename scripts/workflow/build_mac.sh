#!/bin/bash

echo "========= OnTheSpot MacOS Build Script =========="

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project root directory (parent of scripts directory)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Current directory: $(pwd)"

# Clean up previous builds
echo " => Cleaning up!"
rm -rf ./dist/OnTheSpot.app
rm -f ./dist/OnTheSpot.dmg

# Check for FFmpeg binary and set build options
if [ -f "ffbin_mac/ffmpeg" ]; then
    echo " => Found 'ffbin_mac' directory and ffmpeg binary. Including FFmpeg in the build."
    FFBIN='--add-binary=ffbin_mac/*:onthespot/bin/ffmpeg'
else
    echo " => FFmpeg binary not found. Downloading..."
    mkdir -p ffbin_mac
    curl -L https://evermeet.cx/ffmpeg/ffmpeg -o ffbin_mac/ffmpeg
    chmod +x ffbin_mac/ffmpeg
    FFBIN='--add-binary=ffbin_mac/*:onthespot/bin/ffmpeg'
fi

# Run PyInstaller to create the app
echo " => Running PyInstaller..."
pyinstaller --windowed \
    --hidden-import=zeroconf._utils.ipaddress \
    --hidden-import=zeroconf._handlers.answers \
    --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name="OnTheSpot" \
    --icon="src/onthespot/resources/icons/onthespot.icns" \
    src/portable.py

# Check if the build was successful
if [ -d "./dist/OnTheSpot.app" ]; then
    echo " => Build succeeded."
else
    echo " => Build failed or output app not found."
    exit 1
fi

# Create .dmg file
echo " => Creating DMG file..."
mkdir -p dist/dmg_contents
cp -R dist/OnTheSpot.app dist/dmg_contents/
hdiutil create -volname "OnTheSpot" -srcfolder dist/dmg_contents -ov -format UDZO dist/OnTheSpot.dmg
rm -rf dist/dmg_contents

# Check if DMG was created
if [ ! -f "dist/OnTheSpot.dmg" ]; then
    echo " => DMG creation failed. Exiting."
    exit 1
fi

# Move the DMG to artifacts folder
echo " => Moving DMG to artifacts folder..."
mkdir -p artifacts/macos
mv dist/OnTheSpot.dmg artifacts/macos/

# Clean up unnecessary files
echo " => Cleaning up temporary files..."
rm -rf __pycache__ build *.spec

echo " => Done!"
