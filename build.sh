#!/bin/sh
# Build unix_boot (AmigaOS bootstrap for AMIX) with bebbo's amiga-gcc.
#
# Produces an AmigaOS executable that boots an AMIX ELF kernel from AmigaDOS.
# Uses the 040/060-aware copyit.s (src/copyit.s, patched by apply.sh), so it can hand off to
# the kernel on 68040 and 68060 (the MMU path is selected at runtime via AttnFlags, and copyit
# keeps the 68030 branch, but the loader/kernel chain as a whole does not boot on an 68030 --
# see ISSUE-1 in the kernel port and the README).
#
# Prereqs:
#   * bebbo amiga-gcc at $AMIGA_GCC (m68k-amigaos-gcc, GCC 6.5), default $HOME/amiga-gcc.
#   * AT&T ELF headers copied into src/include/ (elf.h, sys/elf*.h) from an
#     AMIX install — see src/README.BEFORE.BUILD!.  This script copies them
#     from $AMIX_ROOT if that is set and include/ is empty.  It has no default.
#
# Usage:  sh build.sh
set -e

AMIGA_GCC="${AMIGA_GCC:-$HOME/amiga-gcc}"
CC="$AMIGA_GCC/bin/m68k-amigaos-gcc"
[ -x "$CC" ] || {
    echo "ERROR: no m68k-amigaos-gcc at $CC"
    echo "       set AMIGA_GCC to your amiga-gcc install prefix."
    exit 1
}

cd "$(dirname "$0")/src"

# 1. ELF headers (AT&T-licensed; not shipped with unix_boot).  AMIX_ROOT has no default:
#    it is a path on your machine, and copying from the wrong tree fails obscurely later.
if [ ! -f include/sys/elf.h ]; then
    [ -n "$AMIX_ROOT" ] || {
        echo "ERROR: src/include/sys/elf.h is missing and AMIX_ROOT is not set."
        echo "       Either copy elf.h and sys/elf*.h from your AMIX installation into"
        echo "       src/include/ by hand (see src/README.BEFORE.BUILD!), or set AMIX_ROOT"
        echo "       to a mounted AMIX root and rerun."
        exit 1
    }
    echo "copying ELF headers from $AMIX_ROOT/usr/include ..."
    mkdir -p include/sys
    cp "$AMIX_ROOT/usr/include/elf.h"            include/
    cp "$AMIX_ROOT/usr/include/sys/elf.h"        include/sys/
    cp "$AMIX_ROOT/usr/include/sys/elf_68K.h"    include/sys/
    cp "$AMIX_ROOT/usr/include/sys/elftypes.h"   include/sys/
fi

CFLAGS="-mcrt=clib2 -O2 -fomit-frame-pointer -Iinclude -DSUPERKICKSTART_KLUDGE"
# -Wa,-m68030 lets the 030 `pmove` ops assemble; the 040/060 ops are .word, so one
# binary carries all three paths -- but only the 040 and 060 ones boot.  See the README.
ASFLAGS="-mcrt=clib2 -Wa,-m68030"

set -x
for c in bind rel streq streqn unix_boot; do
    "$CC" $CFLAGS -c "$c.c" -o "$c.o"
done
for s in Supervisor copyit; do
    "$CC" $ASFLAGS -c "$s.s" -o "$s.o"
done
"$CC" -mcrt=clib2 bind.o rel.o streq.o streqn.o unix_boot.o \
      Supervisor.o copyit.o -o unix_boot040
set +x

file unix_boot040
echo "built: src/unix_boot040  (copy to an AmigaDOS volume next to your 'unix' kernel)"
