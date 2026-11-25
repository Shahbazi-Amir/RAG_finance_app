#!/bin/sh
# Disposable CI image build only. Versions are minimum fixes from actual
# artifact 15040217938; exact chosen versions are recorded by dpkg and SBOM.
# No package source, repo keys, external script or Python/npm lock changes.
set -eu
apt-get update
apt-get install --only-upgrade --no-install-recommends -y \
  perl-base libssl3 openssl libgnutls30 libpcre2-8-0 \
  gpgv libsqlite3-0 apt libapt-pkg6.0 libcap2
check(){
  actual="$(dpkg-query -W -f='${Version}' "$1")"
  dpkg --compare-versions "$actual" ge "$2"
  printf 'F3_LAB_OS_FIX_VERSION %s %s\n' "$1" "$actual"
}
check perl-base 5.36.0-7+deb12u4
check libssl3 3.0.22-1~deb12u2
check openssl 3.0.22-1~deb12u2
check libgnutls30 3.7.9-2+deb12u7
check libpcre2-8-0 10.42-1+deb12u2
check gpgv 2.2.40-1.1+deb12u2
check libsqlite3-0 3.40.1-2+deb12u2
check apt 2.6.2
check libapt-pkg6.0 2.6.2
check libcap2 1:2.66-4+deb12u3
rm -rf /var/lib/apt/lists/*
