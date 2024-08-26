# Copyright 1999-2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

MY_P="${PN}-${PV}a1"
DESCRIPTION="Simple OGG Vorbis, Opus and FLAC bindings for Python"
HOMEPAGE="
	https://github.com/TeamPyOgg/PyOgg/
        https://pypi.org/project/PyOgg/
"
SRC_URI="
        https://github.com/TeamPyOgg/PyOgg/archive/refs/tags/${PV}a1.tar.gz
                -> ${P}.tar.gz
"
S=${WORKDIR}/${MY_P}

LICENSE=""
SLOT="0"
KEYWORDS="~amd64"

distutils_enable_tests pytest
