#!/bin/bash

PV=0.6.2

echo "========= OnTheSpot Appimage Build Script ==========="


echo " => Cleaning up !"
rm -rf dist
rm -rf build


echo " => Fetch Dependencies"
mkdir build
cd build

wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

wget https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage
chmod +x python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage

./python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage --appimage-extract
mv squashfs-root OnTheSpot.AppDir


echo " => Build OnTheSpot.whl"
cd ..
build/OnTheSpot.AppDir/AppRun -m build


echo " => Prepare OnTheSpot Appimage"
cd build
OnTheSpot.AppDir/AppRun -m pip install -r ../requirements.txt
OnTheSpot.AppDir/AppRun -m pip install ../dist/onthespot-$PV-py3-none-any.whl

rm OnTheSpot.AppDir/AppRun
rm OnTheSpot.AppDir/.DirIcon
rm OnTheSpot.AppDir/python.png
rm OnTheSpot.AppDir/python3.12.3.desktop

cp ../src/onthespot/resources/icon.svg OnTheSpot.AppDir/casual_onthespot.svg
cp ../src/onthespot/resources/org.eu.casualsnek.onthespot.desktop OnTheSpot.AppDir/org.eu.casualsnek.onthespot.desktop

echo '#! /bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"

# Export PATH
export PATH=$HERE/usr/bin:$PATH;

# Resolve the calling command (preserving symbolic links).
export APPIMAGE_COMMAND=$(command -v -- "$ARGV0")

# Export TCl/Tk
export TCL_LIBRARY="${APPDIR}/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="${APPDIR}/usr/share/tcltk/tk8.6"
export TKPATH="${TK_LIBRARY}"

# Export SSL certificate
export SSL_CERT_FILE="${APPDIR}/opt/_internal/certs.pem"

# Call OnTheSpot
"$HERE/opt/python3.12/bin/python3.12" "-m" "onthespot" "$@"' > OnTheSpot.AppDir/AppRun
chmod +x OnTheSpot.AppDir/AppRun

echo ' '
echo ' # ffmpeg, ffprobe, and ffplay need to be manually added to OnTheSpot.AppDir/usr/bin.'
echo ' # Make sure to run chmod +x on each, binaries can be found here:'
echo ' # https://johnvansickle.com/ffmpeg/'
echo ' '
echo ' => Done adding ffmpeg binaries? (y/n)'

read ffmpeg
case $ffmpeg in
  y)
    sleep 1
    clear
    ;;
esac


echo " => Build OnTheSpot Appimage"

./appimagetool-x86_64.AppImage --appimage-extract
squashfs-root/AppRun OnTheSpot.AppDir
mv OnTheSpot-x86_64.AppImage ../dist/OnTheSpot-x86_64.AppImage


echo " => Done "
