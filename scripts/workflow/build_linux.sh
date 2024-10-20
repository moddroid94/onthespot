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
    echo " => FFmpeg binary not found. Downloading..."
    mkdir -p ffbin_nix
    wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar -xf ffmpeg-release-amd64-static.tar.xz
    cp ffmpeg-*-amd64-static/ffmpeg ffbin_nix/
    rm -rf ffmpeg-*-amd64-static ffmpeg-release-amd64-static.tar.xz
    FFBIN="--add-binary=ffbin_nix/*:onthespot/bin/ffmpeg"
    NAME="onthespot_linux_ffm"
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

if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    echo " => Failed to download linuxdeploy. Exiting."
    exit 1
fi

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

# Check if AppImage was created
if [ ! -f OnTheSpot-x86_64.AppImage ]; then
    echo " => AppImage creation failed. Exiting."
    exit 1
fi

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
