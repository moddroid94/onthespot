# Copyright 1999-2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

MY_P="showinfilemanager-${PV}"
DESCRIPTION="Python module to open the system file manager"
HOMEPAGE="
	https://github.com/damonlynch/showinfilemanager/
	https://pypi.org/project/show-in-file-manager/
"
SRC_URI="
        https://github.com/damonlynch/showinfilemanager/archive/refs/tags/v${PV}.tar.gz
                -> ${P}.gh.tar.gz
"
S=${WORKDIR}/${MY_P}

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"

RDEPEND="
	dev-python/argparse-manpage
"

distutils_enable_tests pytest
