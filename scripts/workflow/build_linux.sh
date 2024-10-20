#!/bin/bash

echo "========= OnTheSpot Linux Build Script ========="

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../"

echo "Current directory: $(pwd)"

# Clean up previous builds
echo " => Cleaning up!"
rm -rf dist build artifacts/linux
mkdir -p artifacts/linux

# Build with PyInstaller
echo " => Building executable with PyInstaller..."
pyinstaller --onefile \
    --hidden-import zeroconf._utils.ipaddress \
    --hidden-import zeroconf._handlers.answers \
    --add-data "src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data "src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data "src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data "src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    --name onthespot_linux \
    --icon src/onthespot/resources/icons/onthespot.png \
    src/portable.py

if [ -f "dist/onthespot_linux" ]; then
    echo " => Build succeeded."
    tar -czvf artifacts/linux/onthespot_linux.tar.gz -C dist onthespot_linux
else
    echo " => Build failed."
    exit 1
fi

# Clean up unnecessary files
rm -rf dist build *.spec __pycache__

echo " => Done!"
