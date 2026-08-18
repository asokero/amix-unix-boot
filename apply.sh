#!/bin/sh
# apply.sh -- reconstruct the patched loader sources.
#
# This repository contains PATCHES, not sources.  The originals are not ours to redistribute --
# no licence is stated for Markus Wild's work, and the files carry Commodore's 1991 copyright
# from the AMIX boot code they were adapted from -- so you supply them, exactly as with the
# kernel port itself.
#
#   1. obtain unix_boot.lha -- Markus Wild's AmigaDOS loader sources, Aminet misc/unix/unix_boot
#      (v1.1c).  Derived from Commodore's /usr/sys/amiga/boot, hence the 1991 headers inside.
#   2. sh apply.sh /path/to/unix_boot.lha
#   3. sh build.sh
#
# The extracted and patched tree lands in src/ and is gitignored.
set -e
LHA="${1:-unix_boot.lha}"
HERE=$(cd "$(dirname "$0")" && pwd)

[ -f "$LHA" ] || { echo "usage: sh apply.sh /path/to/unix_boot.lha"; exit 1; }

# The archive this project's patches were measured against.  Same reasoning as the kernel side's
# tools/verify-stock.sh: the patches address the sources by content, so a different archive would
# not fail cleanly -- it would apply some hunks, reject others, and leave a tree nobody can trust.
UNIX_BOOT_SHA256=643562c09cac44f13e46c8c05b3ba1d52cac999525d117c32d7f118642a2000a
_got=$(sha256sum "$LHA" | cut -d' ' -f1)
if [ "$_got" != "$UNIX_BOOT_SHA256" ]; then
	if [ "${AMIX_ALLOW_UNKNOWN_UNIX_BOOT:-0}" = "1" ]; then
		echo "[!] UNKNOWN unix_boot.lha, and you set AMIX_ALLOW_UNKNOWN_UNIX_BOOT=1."
		echo "[!]   sha256   $_got"
		echo "[!]   expected $UNIX_BOOT_SHA256"
		echo "[!] Hunks may apply in the wrong place or not at all.  Check every reject."
	else
		echo "[FAIL] this is not the unix_boot.lha these patches were made against."
		echo
		echo "         file     $LHA"
		echo "         sha256   $_got"
		echo "         expected $UNIX_BOOT_SHA256   (Aminet misc/unix/unix_boot, v1.1c, 37277 bytes)"
		echo
		echo "       If your copy genuinely differs, that is worth knowing -- please report the hash"
		echo "       above.  To proceed anyway, at your own risk:"
		echo "           AMIX_ALLOW_UNKNOWN_UNIX_BOOT=1 sh apply.sh $LHA"
		exit 1
	fi
else
	echo "[*] archive verified: $LHA"
fi
command -v 7z >/dev/null 2>&1 || { echo "ERROR: 7z (p7zip) is needed to unpack the .lha"; exit 1; }

rm -rf "$HERE/src"
mkdir -p "$HERE/.extract"
( cd "$HERE/.extract" && rm -rf ./* && 7z x "$(cd "$(dirname "$LHA")" && pwd)/$(basename "$LHA")" >/dev/null )
[ -d "$HERE/.extract/src" ] || { echo "ERROR: no src/ inside the archive -- is this unix_boot.lha?"; exit 1; }
mv "$HERE/.extract/src" "$HERE/src"
rm -rf "$HERE/.extract"

echo "[*] applying patches"
for p in "$HERE"/patches/*.patch; do
	f=$(basename "$p" .patch)
	patch -p0 -d "$HERE/src" -i "$p" >/dev/null || { echo "FAILED: $f"; exit 1; }
	echo "      $f"
done

# copyit.s is REBUILT, not patched.  A diff of it would carry the whole original file, because
# the change replaces the 68030 MMU-disable sequence wholesale -- and this repository ships no
# source of a work that is not ours to redistribute.  The transformation holds our text and the
# line numbers of what survives; it reads the rest out of your own copy.  See NOTICE.
echo "[*] rebuilding copyit.s (transformation, not a patch -- see transforms/transform_copyit.py)"
# NOT piped.  In POSIX sh a pipeline's exit status is its LAST command's, so `python3 ... | sed`
# would report sed's success and this script would print [OK] with copyit.s left unpatched.
# Measured: the transform alone exits 1 on a bad input, through the pipe it exited 0.  That is
# the same defect as ISSUE-45 in the kernel port, reintroduced here by a cosmetic indent.
_copyit_log=$(python3 "$HERE/transforms/transform_copyit.py" "$HERE/src/copyit.s" 2>&1) || {
	printf '%s\n' "$_copyit_log" | sed 's/^/      /'
	echo "FAILED: copyit.s"; exit 1
}
printf '%s\n' "$_copyit_log" | sed 's/^/      /'

echo "[OK] patched sources in src/ -- next: sh build.sh"
