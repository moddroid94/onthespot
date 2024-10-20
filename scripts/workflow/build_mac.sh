#!/bin/bash

echo "========= OnTheSpot macOS Build Script ========="

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../"

echo "Current directory: $(pwd)"

# Clean up previous builds
echo " => Cleaning up!"
rm -rf dist build artifacts/macos
mkdir -p artifacts/macos

# Build with PyInstaller
echo " => Building executable with PyInstaller..."
pyinstaller --windowed \
    --hidden-import zeroconf._utils.ipaddress \
    --hidden-import zeroconf._handlers.answers \
    --add-data "src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data "src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data "src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data "src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    --name OnTheSpot \
    --icon src/onthespot/resources/icons/onthespot.icns \
    src/portable.py

if [ -d "dist/OnTheSpot.app" ]; then
    echo " => Build succeeded."
    hdiutil create -volname OnTheSpot -srcfolder dist/OnTheSpot.app -ov -format UDZO artifacts/macos/OnTheSpot.dmg
else
    echo " => Build failed."
    exit 1
fi

# Clean up unnecessary files
rm -rf dist build *.spec __pycache__

echo " => Done!"
