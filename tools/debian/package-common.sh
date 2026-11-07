# Shared setup for Darling's daily Debian packages. Source this from the repo root.
DATE=$(date +%Y%m%d)
DISTRO=${DEB_DISTRO:-"$(lsb_release -cs)"}
UPSTREAM_VERSION=0.1.${DATE}
DEBIAN_REVISION=1~${DISTRO}
VERSION=${UPSTREAM_VERSION}-${DEBIAN_REVISION}
ORIG_ARCHIVE=../darling_${UPSTREAM_VERSION}.orig.tar.xz

write_daily_changelog() {
    rm -f debian/changelog
    EDITOR=true NAME="Darling build server" EMAIL=${DEB_EMAIL:-noreply@darlinghq.org} \
        dch -u low -v "$VERSION" --create --distribution "$DISTRO" --package darling "Daily build"
}

write_orig_archive() {
    # Quilt packages keep Debian packaging in the separate debian.tar archive.
    # Git metadata is not part of the upstream source, including submodule .git files.
    tar -cJf "$ORIG_ARCHIVE" --exclude=./debian --exclude=.git .
}
