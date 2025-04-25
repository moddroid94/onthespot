#!/bin/bash

echo "========= OnTheSpot Linux Build Script ========="


echo " => Cleaning up previous builds and preparing the environment..."
rm -f ./dist/OnTheSpot.tar.gz
mkdir build
mkdir dist
python3 -m venv venv
source ./venv/bin/activate


echo " => Upgrading pip and installing necessary dependencies..."
venv/bin/pip install --upgrade pip wheel pyinstaller
venv/bin/pip install -r requirements.txt


#echo " => Build FFMPEG (Optional)"
#FFBIN="--add-binary=dist/ffmpeg:onthespot/bin/ffmpeg"
#if ! [ -f "dist/ffmpeg" ]; then
#    cd build
#    curl https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz -o ffmpeg.tar.xz
#    tar xf ffmpeg.tar.xz
#    cd ffmpeg-*
#    ./configure --enable-small --disable-ffplay --disable-ffprobe --disable-doc --disable-htmlpages --disable-manpages --disable-podpages --disable-txtpages
#    make
#    cp ffmpeg ../../dist
#    cd ../..
#fi


echo " => Running PyInstaller to create binary..."
pyinstaller --onefile \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/qt/qtui/*.ui:onthespot/qt/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name=onthespot-gui \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py


echo " => Packaging executable as tar.gz archive..."
cd dist
tar -czvf OnTheSpot.tar.gz onthespot-gui
cd ..


echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec


echo " => Done! Packaged tar.gz is available in 'dist/OnTheSpot.tar.gz'."

