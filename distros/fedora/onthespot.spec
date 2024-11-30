Name:           onthespot
Version:        1.0.3
Release:        1%{?dist}
Summary:        A music downloader
License:        MIT
Source0:        onthespot-1.0.3-py3-none-any.whl
Source1:        org.onthespot.OnTheSpot.desktop
BuildArch:      noarch

%description
A music downloader.

%prep
# No preparation needed for a Wheel package

%build
# No build step needed for a Wheel package

%install
mkdir -p %{buildroot}/usr/lib/python3/site-packages
pip3 install --root %{buildroot} --no-deps --ignore-installed %{SOURCE0}

# Ensure that the executables are installed
mkdir -p %{buildroot}/usr/bin

# Install the desktop file
mkdir -p %{buildroot}/usr/share/applications
install -m 0644 %{SOURCE1} %{buildroot}/usr/share/applications/

%files
%{python3_sitelib}/onthespot*
/usr/bin/onthespot-cli
/usr/bin/onthespot-gui
/usr/bin/onthespot-web
/usr/share/applications/org.onthespot.OnTheSpot.desktop

%changelog
* Sat Nov 30 2024 Justin Donofrio <justin025@protonmail.com> - 1.0.3-1
- Initial package creation