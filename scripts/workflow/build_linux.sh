#!/bin/bash

echo "========= OnTheSpot Linux Build Script ========="

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project root directory (parent of scripts directory)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Current directory: $(pwd)"

# Clean up previous builds
echo " => Cleaning up!"
rm -f ./dist/onthespot_linux ./dist/onthespot_linux_ffm
rm -f ./dist/onthespot_linux.tar.gz
rm -f ./dist/OnTheSpot.AppImage
rm -rf ./AppDir

# Check for FFmpeg and set build options
if [ -f "ffbin_nix/ffmpeg" ]; then
    echo " => Found 'ffbin_nix' directory and ffmpeg binary. Including FFmpeg in the build."
    FFBIN="--add-binary=ffbin_nix/*:onthespot/bin/ffmpeg"
    NAME="onthespot_linux_ffm"
else
    echo " => FFmpeg binary not found. Building without it."
    FFBIN=""
    NAME="onthespot_linux"
fi

# Run PyInstaller
echo " => Running PyInstaller..."
pyinstaller --onefile \
    --hidden-import=zeroconf._utils.ipaddress \
    --hidden-import=zeroconf._handlers.answers \
    --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name="$NAME" \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py

# Check if the build was successful
if [ -f "./dist/$NAME" ]; then
    # Set executable permissions
    echo " => Setting executable permissions..."
    chmod +x "./dist/$NAME"
else
    echo " => Build failed or output file not found."
    exit 1
fi

# Create .tar.gz archive
echo " => Creating tar.gz archive..."
cd dist
tar -czvf "$NAME.tar.gz" "$NAME"
cd ..

# Build AppImage
echo " => Building AppImage..."

# Download linuxdeploy
wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage

# Create AppDir structure
mkdir -p AppDir/usr/bin
cp "dist/$NAME" AppDir/usr/bin/onthespot

# Copy desktop file and icon
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp src/onthespot/resources/icons/onthespot.png AppDir/usr/share/icons/hicolor/256x256/apps/onthespot.png

# Create desktop file
cat > AppDir/usr/share/applications/onthespot.desktop <<EOF
[Desktop Entry]
Name=OnTheSpot
Exec=onthespot
Icon=onthespot
Type=Application
Categories=Utility;
EOF

# Run linuxdeploy to create AppImage
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

# Move the AppImage to dist
mv OnTheSpot*.AppImage dist/OnTheSpot.AppImage

# Move the artifacts to artifacts folder
echo " => Moving artifacts to artifacts folder..."
mkdir -p artifacts/linux
mv dist/"$NAME.tar.gz" artifacts/linux/
mv dist/OnTheSpot.AppImage artifacts/linux/

# Clean up
rm linuxdeploy-x86_64.AppImage
rm -rf AppDir

# Clean up unnecessary files
echo " => Cleaning up temporary files..."
rm -rf __pycache__ build *.spec

echo " => Done!"
