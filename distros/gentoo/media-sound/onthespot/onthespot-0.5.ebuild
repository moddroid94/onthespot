# Copyright 2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{10..13} )

inherit distutils-r1 desktop xdg

DESCRIPTION="qt based music downloader written in python"
HOMEPAGE="https://github.com/justin025/onthespot"
SRC_URI="https://github.com/justin025/onthespot/archive/refs/tags/v${PV}.tar.gz
		 -> ${P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"

BDEPEND="
        dev-lang/python[gdbm]
        dev-python/async-timeout
        dev-python/certifi
        dev-python/charset-normalizer
        dev-python/defusedxml
        dev-python/gssapi
        dev-python/idna
        dev-python/ifaddr
        dev-python/librespot
        dev-python/music-tag
        dev-python/packaging
        dev-python/pillow
        dev-python/protobuf-python
        dev-python/PyOgg
        dev-python/PyQt5[network,widgets]
        dev-python/PyQt5-sip
        dev-python/pyxdg
        dev-python/requests
        dev-python/show-in-file-manager
        dev-python/urllib3
        dev-python/websocket-client
        dev-python/zeroconf
        media-libs/mutagen
"

RDEPEND="
        media-video/ffmpeg[mp3,sdl]
"

src_install() {
	distutils-r1_src_install

	domenu "${S}"/src/onthespot/resources/org.eu.casualsnek.onthespot.desktop
	newicon -s 256 "${S}"/src/onthespot/resources/icon.svg casual_onthespot.svg
}
