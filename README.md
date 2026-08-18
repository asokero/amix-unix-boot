# unix_boot for 68040/68060 — Amiga UNIX bootstrap patches

## Overview

`unix_boot` is **Markus Wild's** AmigaDOS program that loads an Amiga UNIX (AMIX) ELF kernel and
transfers control to it, distributed on Aminet as version 1.1c
([`misc/unix/unix_boot`](https://aminet.net/package/misc/unix/unix_boot)). This repository contains
**patches** that make it work on a 68040 or 68060, plus the build script.

It is **not** a Commodore product, although it is derived from Commodore code: its own readme
records that the author took the boot sources from `/usr/sys/amiga/boot` in the AMIX distribution,
changed them to use DOS instead of device I/O, and converted the assembler files from SGS to MIT
syntax so GCC could build them. That is why the files still carry Commodore's 1991 copyright
header while the program as a whole is his.

This repository ships **none of the original `unix_boot` source files**. Two independent
reasons: every source file in the archive carries Commodore's 1991 copyright — checked, all ten
of them, and none carries Markus Wild's name — and no licence is stated for his own work on
top. You supply the archive yourself, exactly as with the kernel port.

What the patches *do* contain of the original is measured rather than described, and `NOTICE`
gives the number for each file. `copyit.s` is not among them: it is **rebuilt rather than
patched** by `transforms/transform_copyit.py`, which holds our text and the line numbers of what
survives and reads the rest out of your own copy — because a diff of that file would have carried
all 70 of its lines.

That arrangement is not an invention of ours. Wild's own `README.BEFORE.BUILD!` explains that he
left AT&T's ELF headers out of the archive — *"Since I didn't want to risk any Copyright war with
AT&T"* — and told the reader to copy them from their own SVR4 partition. Same reasoning, from the
author of the thing being patched; see `NOTICE`.

Three things were wrong with the stock loader on anything newer than a 68030:

* `copyit.s` disabled the MMU with three unguarded 68030 `pmove` instructions. On a 68040 or 68060
  those are illegal instructions, so the machine trapped **before the kernel ever ran**. This is
  the first thing that has to work.
* `rel.c` mis-applied PC-relative relocations. That went unnoticed until the kernel gained
  Motorola's FPSP, whose body carries ~330 of them.
* the load buffer could overlap its destination, and the memory list handed to the kernel needed
  the SuperKickstart region reclaimed.

## What is different, from where you sit

Four of these you will see on the screen the moment you run it.

**It boots a 68040 or a 68060 at all.** That is the whole point, and it is three separate fixes
(see the list above). One of them is visible: the loader reads `SysBase->AttnFlags`, prints it,
says which MMU-disable path it will take, and pokes the kernel's `cputype` global before handing
over — which is what lets a single kernel image serve both CPUs.

```
AttnFlags = 0x0000804f
  -> copyit will take the 68040/060 (movec) path.
kernel cputype set to 40
```

**It lists the AutoConfig boards it is handing to the kernel.** The stock loader filled the
kernel's board table silently; this one prints it, one line per board, so a card that the kernel
later cannot see can be ruled in or out before the kernel ever runs.

```
bootinfo @ 0000d6a0: 5 board(s), 3 mem region(s)
  board[0] mfg=0202 prod=70 addr=00e90000 size=00010000
  board[1] mfg=4231 prod=01 addr=00ea0000 size=00010000
  board[2] mfg=0893 prod=05 addr=00200000 size=00200000
  board[3] mfg=0893 prod=06 addr=00eb0000 size=00010000
  board[4] mfg=6d6e prod=01 addr=00600000 size=00400000
```

That is a real capture from an Amiga 3000: a Commodore A2065 Ethernet card, an ACT Prelude, a
Piccolo graphics card in its two AutoConfig pieces (`0893:05` the RAM aperture, `0893:06` the
registers), and an MNT VA2000. Five boards, and the kernel will be told about exactly these.

**Everything it prints also goes to the serial port.** Written straight to the custom-chip
register at `$DFF030`, with no `serial.device`, so it works regardless of what is or is not
initialised. Two reasons it matters: the screen holds about 40 lines and the interesting part
scrolls away, and one capture then contains the loader's output *and* the kernel's, in order, on
one timeline. On a real machine that is a serial cable; under Amiberry it is a TCP port.

**It pauses for 10 seconds before the handoff, and does not require you.** Press RETURN to go on
immediately, or wait and it continues by itself — so an unattended or emulated boot never blocks
on a keypress. `unix_boot040 -w` restores the original behaviour and waits forever, which is what
you want when you are photographing the screen on real hardware.

```
[RETURN to continue now; auto-continue in 10 s; -w waits forever]
```

Two more diagnostics print in that same pause, and both are worth reading: a **checksum of the
loaded image**, so you can tell whether what is in memory is what is on disk, and an explicit
**overlap check** on the copy that is about to happen. The stock loader could place the load
buffer over its own destination and corrupt the kernel silently; this one says either

```
no overlap (copy is safe)
```

or a warning that it is about to do exactly that.

## Disclaimer

This is hobbyist work on a 34-year-old proprietary operating system. It is not affiliated with
Commodore, AT&T or anyone else, it is not supported, and it is not for production use. It can
render a machine unbootable; keep a copy of the original loader.

## Requirements

* the original **`unix_boot.lha`** — Markus Wild's package, Aminet `misc/unix/unix_boot` (v1.1c)
* nothing else. In particular **`arp.library` is not needed** by what you build here — see below
* **bebbo's amiga-gcc** (`m68k-amigaos-gcc`, GCC 6.5) — <https://github.com/bebbo/amiga-gcc>
* **7z** (p7zip) to unpack the archive, `patch`, and **Python 3** (`apply.sh` rebuilds `copyit.s`
  with it)
* AT&T ELF headers (`elf.h`, `sys/elf*.h`) from an AMIX installation — see
  `src/README.BEFORE.BUILD!` in the archive; `build.sh` copies them from a mounted AMIX root if
  `AMIX_ROOT` is set

Two environment variables tell `build.sh` where the last two live. `build.sh` stops with an
explanation if it cannot find either, rather than failing later and obscurely:

| variable | what it points at | default |
|---|---|---|
| `AMIGA_GCC` | the amiga-gcc install prefix, the one containing `bin/m68k-amigaos-gcc` | `$HOME/amiga-gcc` |
| `AMIX_ROOT` | a mounted AMIX root, read once to copy the ELF headers | none — or copy the four headers in by hand |

## Quick start

```sh
sh apply.sh /path/to/unix_boot.lha     # verifies the archive's sha256, extracts, patches -> src/
sh build.sh                            # -> src/unix_boot040 (AmigaOS executable)
```

`apply.sh` refuses an archive it does not recognise, for the same reason the kernel side refuses
an unknown `/stand/unix`: the patches address the sources by content, so a different archive would
not fail cleanly — some hunks would apply, others would reject, and the result would be a tree
nobody can trust. `AMIX_ALLOW_UNKNOWN_UNIX_BOOT=1` overrides it, at your own risk.

**`arp.library`: needed by the original, not by this.** Markus Wild's readme lists it as a
requirement, and the *prebuilt* `bin/unix_boot` in his archive does reference it. The sources do
not, and neither does what you build here — measured on both the binary used for every hardware
acceptance in the kernel project and a fresh build: zero references to `arp.library` or `ArpBase`
in either, against three in the shipped binary. So if you are running the original executable you
need it in `LIBS:`; if you are running `unix_boot040`, you do not.

Copy the result to the Amiga and boot with it instead of the stock `unix_boot`:

```
unix_boot040 unix-040
```

On a 68060, **SetPatch must run first** — it is a boot precondition, not an optimisation.

### This build is for the 68040 and 68060 only

On a **68030 it gurus** with `8000 0038` — vector 56, a 68030 MMU Configuration Error — right
after the loader hands off, with any kernel including the stock one. The handoff itself is fine:
the kernel reaches its own `pstart` and faults there, on the `pmove` sequence that enables the
MMU. It reproduces on real hardware and under both emulators.

That is a known defect, deferred rather than fixed, and it is `ISSUE-1` in the kernel port's
`KNOWN-ISSUES.md`. It may get fixed one day; it is not being worked on, because the 68030 already
has a loader that works.

**On a 68030, use the original** `unix_boot` from Aminet (`misc/unix/unix_boot`). It boots the
same kernels without trouble, and it is the archive these patches are applied to anyway.

## Files

| path | what |
|---|---|
| `patches/unix_boot.c.patch` | loader main: memory list, overlap-safe copy, diagnostics |
| `transforms/transform_copyit.py` | **the important one** — rebuilds `copyit.s` with a 68040/68060 MMU disable. Not a patch; see `NOTICE` |
| `patches/rel.c.patch` | PC-relative relocation fix (mandatory for an FPSP kernel) |
| `patches/bind.c.patch` | bind-address selection |
| `patches/Makefile.patch` | build adjustments |
| `apply.sh` | unpack the archive and apply the patches |
| `build.sh` | build with amiga-gcc |

Everything else in the archive is used unmodified.

## Status

Hardware-verified as the loader for the **AMIX 68040/68060 Port** on an Amiga 3000 with:

* **68060** on a Mercury card (66 MHz), 2026-08
* **68040** on an A3640 (25 MHz), 2026-08 — a card with no local RAM, where the kernel binds into
  motherboard memory at `0x07000000` instead of the accelerator's `0x08000000`

The patched loader is what every hardware acceptance run in the kernel project used.

The build at the `v1.0-040-060` tag is `sha256 479c496e…` (`src/unix_boot040`, 39 308 bytes). It
was booted on real hardware on 2026-08-18 — an Amiga 3000 with the 68060 Mercury card — and the
machine came up normally.

That is a regression result and should be read as one. The capacity checks on
`bootinfo.autocon[]` and `memory[]` refuse to boot rather than overrun those arrays, and reaching
either needs more than sixteen AutoConfig boards or sixteen memory regions — far more than an
Amiga 3000 has. Those branches did not execute. What the boot establishes is that adding them did
not disturb the path every machine actually takes.

The 68060 is the more useful of the two CPUs to have run it on. `cputype` is poked into the kernel
here, a few dozen lines below the changed code, and on a 68060 that poke is what stops every
CPU-gated path in the kernel from running as a 68040. An 040 boot would have been silent about it.

## Related

The kernel side lives in the companion repository `amix-040-060-port`, project name
**AMIX 68040/68060 Port**. It is the same kind of artifact: a patch and override layer over a
proprietary binary that you supply.

## Repository metadata

Description, one line, for the repository listing:

> Patches that make Markus Wild's `unix_boot` load an Amiga UNIX kernel on a 68040 or 68060 —
> patches only, you supply the archive.

Topics:

`amiga` `amiga-unix` `amix` `68040` `68060` `m68k` `bootloader` `retrocomputing`

## License

New code and modifications: **MIT** — see `LICENSE`.

The original `unix_boot` is Markus Wild's, and the files in it carry
`Copyright (C) 1991, Commodore Business Machines, Inc.` from the boot sources it was adapted from.
No licence is stated for either layer, so no source file of it is shipped here. The patches do
carry some original text — the lines they remove and the context around them — and `NOTICE`
measures it per file. `copyit.s`, which a diff would have carried in full, is rebuilt by a
transformation instead.

-Antti Sokero 2026
