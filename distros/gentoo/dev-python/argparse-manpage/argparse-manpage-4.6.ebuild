# Copyright 1999-2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

DESCRIPTION="Automatically build man-pages for your Python project"
HOMEPAGE="
	https://github.com/praiskup/argparse-manpage/
	https://pypi.org/project/argparse-manpage/
"
SRC_URI="
        https://github.com/praiskup/argparse-manpage/archive/refs/tags/v${PV}.tar.gz
                -> ${P}.tar.gz
"

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64"

distutils_enable_tests pytest
