#!/usr/bin/env python3
"""transform_copyit.py -- rebuild the loader's copyit.s for the 68040 and 68060.

    python3 transforms/transform_copyit.py src/copyit.s

WHY THIS IS NOT A PATCH

Every other change in this repository ships as a unified diff, which is the clearest way to show
a reviewer what moved.  copyit.s cannot: the 68030 MMU-disable sequence is replaced wholesale, so
the diff removes 40 of the file's 70 lines and reproduces the rest as context.  Measured, a diff
carries the whole file -- and this repository's claim is that it distributes no source of a work
that is not ours to redistribute.  A promise that costs nothing is not a promise.

So copyit.s is rebuilt instead of patched.  This script contains OUR text and nothing else; every
line of the original that survives is copied out of YOUR file by line number.  Nothing of
Markus Wild's archive, and nothing of the Commodore boot code it derives from, is stored here.

The recipe below is machine-derived from the two files and then verified end to end: the result
is compared against a known sha256, so a wrong input or a mis-edited recipe fails loudly rather
than producing a loader that boots into something almost right.

WHAT THE TRANSFORMATION DOES, in the order it matters

  1. The MMU-disable.  The stock sequence uses 68030 `pmove tc/crp/srp`, which does not exist on
     a 68040 or 68060 -- the CPU traps and the machine dies before the kernel runs.  Replaced
     with a branch on SysBase->AttnFlags: 68030 keeps the original path, 040/060 clear TC and
     ITT0/1, DTT0/1 through `movec` and flush the ATC with `pflusha`.
  2. Cache coherency.  040/060 have split copyback caches with no automatic coherency, so the
     freshly copied kernel text can still be sitting in the data cache while the instruction
     fetcher reads stale memory.  A `cpusha bc` is issued before the jump.
  3. Privileged 040/060 opcodes are emitted as `.word`, exactly as the stock file already does
     for the transparent-translation registers, so the file still assembles with a plain -m68030
     assembler.

WHAT IT DEPENDS ON

The input must be the copyit.s from the archive apply.sh verifies (Aminet misc/unix/unix_boot
v1.1c).  Its sha256 is checked before anything is written.  If yours differs, nothing is written
and the reason is printed: the line numbers below would otherwise cut the wrong lines out of a
file that is not the one this was derived from.

Exit status: 0 written, 1 refused or the result did not match.
"""
import hashlib, os, sys

ORIG_SHA256   = "f22aba214158eb41dc4dfa3f45767d6afd0289fc57c71fadc653dd2dff5441f2"
RESULT_SHA256 = "89217952663cae027b7c166db595b7c8dd7b798ff892aa3d5215c63268845dce"

# ("keep", a, b) copies lines [a:b) of YOUR copyit.s, 0-based.  ("emit", text) is ours.
RECIPE = [
    ("keep", 0, 1),
    ("emit", """\
| 2026 modifications: CPU-class-aware MMU disable for 68030 / 68040 / 68060."""),
    ("keep", 1, 2),
    ("emit", """\
| Entered in supervisor mode with a2 holding the copyinfo pointer; Supervisor.s
| arranges that.  The routine is memcpy()'d into chip RAM
| and executed there, so it must stay position-independent: data labels are
| reached PC-relative, and the 040/060 path uses only immediate/register forms.
|
| What changed vs. the stock copyit.s:
|   * The stock version disabled the MMU with three UNGUARDED 68030 `pmove`
|     instructions (tc/crp/srp).  On a 68040/060 `pmove` is illegal, so the
|     machine trapped here BEFORE the kernel ran.  This is the first 040/060
|     bring-up blocker (see boot-path-map.md, Stage 0c).
|   * We now branch on SysBase->AttnFlags: 68030 keeps the pmove path; 68040 and
|     68060 use `movec` to clear TC + ITT0/1 + DTT0/1 and `pflusha` to flush the
|     ATC.  After the copy, 040/060 do `cpusha bc` so the freshly copied kernel
|     text is coherent before we jump into it (040/060 have split copyback caches
|     with no automatic coherency).
|
| 040/060 privileged ops are emitted as `.word` (validated with
| m68k-linux-gnu-as -m68040/-m68060) so the file assembles under a plain
| -m68030 assembler, exactly as the stock file already does for tt0/tt1."""),
    ("keep", 5, 7),
    ("emit", """\
	.set	ATTNFLAGS,0x129		| low byte of SysBase->AttnFlags (UWORD @ 0x128)
	.set	AFB_68030,2
	.set	AFB_68040,3
	.set	AFB_68060,7"""),
    ("keep", 7, 9),
    ("keep", 10, 16),
    ("emit", """\
	.set	ci_cksum, 24		| DIAG 2026-07-09: loader-computed image sum"""),
    ("keep", 17, 22),
    ("emit", """\
	movew	#0x2700,sr		| ints off, supervisor"""),
    ("keep", 23, 24),
    ("emit", """\
	movel	ABSEXECBASE,a1		| a1 = ExecBase (SysBase)
	btst	#AFB_68040,a1@(ATTNFLAGS)
	bne	mmu040
	btst	#AFB_68060,a1@(ATTNFLAGS)
	bne	mmu040

| ---- 68030 (or 68020+68851) : original PMMU disable ----
mmu030:"""),
    ("keep", 24, 30),
    ("emit", """\
	btst	#AFB_68030,a1@(ATTNFLAGS)
	beq	docopy			| Skip TT registers if not 68030
	lea	pc@(zero-.+2),a0
	.word 0xf010,0x0800		| pmove a0@,tt0  (gas only knows 68851 ops)
	.word 0xf010,0x0c00		| pmove a0@,tt1
	bra	docopy"""),
    ("keep", 31, 32),
    ("emit", """\
| ---- 68040 / 68060 : MOVEC-based MMU disable ----
mmu040:
	moveq	#0,d0
	.word 0x4e7b,0x0003		| movec d0,tc    -> paged MMU off (clears TCR E)
	.word 0x4e7b,0x0004		| movec d0,itt0  -> no transparent translation
	.word 0x4e7b,0x0005		| movec d0,itt1
	.word 0x4e7b,0x0006		| movec d0,dtt0
	.word 0x4e7b,0x0007		| movec d0,dtt1
	.word 0xf518			| pflusha        -> flush ATC (040/060 encoding)
	| fall through to docopy"""),
    ("keep", 37, 38),
    ("emit", """\
docopy:
	movel	a2@(ci_loadbuf),a0	| a0 = text+data buffer (source)
	movel	a2@(ci_vaddr),a1	| a1 = destination
	movel	a2@(ci_size),d0		| d0 = byte count
| FIX 2026-07-09 (THE COLD-BOOT KILLER): the stock direction choice was
| INVERTED for overlapping ranges -- dest<src copied DESCENDING and dest>=src
| ASCENDING, each of which clobbers unread source bytes when the ranges
| overlap.  Measured on Amiberry: AllocMem placed the ELF buffer ~0.94MB above
| the fast-RAM base, the ~0.96MB text+data image overlapped its head by ~25KB,
| and the descending copy shifted data-section bytes over the first 25KB of
| kernel text (including _start) -> instant wild execution at handoff.  The
| ed/dir "warm-up" only worked by pushing the buffer past the overlap.
| Also fixed the off-by-one: `subl #1,d0 / bcc` copied size+1 bytes (stray
| byte at dest-1 / dest+size, seen as a Gary timeout at RAM_base-1).
	tstl	d0
	beq	copydone		| size 0: nothing to copy
	cmpl	a0,a1			| dest - src
	bcs	copyfwd			| dest < src  -> ascending is overlap-safe
	addl	d0,a0			| dest >= src -> descending from the tail
	addl	d0,a1
copybwd:
	moveb	a0@-,a1@-
	subql	#1,d0
	bne	copybwd"""),
    ("keep", 51, 52),
    ("emit", """\
copyfwd:
	moveb	a0@+,a1@+
	subql	#1,d0
	bne	copyfwd"""),
    ("keep", 57, 59),
    ("emit", """\
	movel	ABSEXECBASE,a1		| reload SysBase (a1 was clobbered by the copy)
	btst	#AFB_68040,a1@(ATTNFLAGS)
	bne	flush040
	btst	#AFB_68060,a1@(ATTNFLAGS)
	beq	handoff
flush040:
	.word 0xf4f8			| cpusha bc -> push+invalidate caches before jmp
| CACHE-HANDOFF FIX (2026-07-21, ISSUE-21 hypothesis): disable the inherited
| 040/060 caches -- especially the COPYBACK data cache that AmigaOS/68040.library
| leaves ENABLED -- before entering the kernel.  The kernel runs its earliest code
| (config(), then pstart040's table-build memcpy/bzero) BEFORE it sets up its own
| cache regime (pstart040 enables IC only, much later at MMU-on), so it must not
| inherit copyback DC.  The intermittent real-HW early-boot fault (illegal-instr
| in config/memcpy, address-error in pstart/bzero) NEVER reproduces on Amiberry,
| which does not model 040 copyback DC -> points squarely at inherited cache state.
| cpusha bc above already pushed+invalidated, so the caches are clean here; CACR=0
| leaves them off until pstart040 re-enables IC.  d0 is reloaded by the checksum
| loop below, so clobbering it is safe.  movec d0,cacr (CACR=ctrl reg 0x002) is
| valid on 020/030/040/060; 0 = all caches off.
	moveq	#0,d0
	.word 0x4e7b,0x0002		| movec d0,cacr -> all 040/060 caches OFF
handoff:
| ---- DIAG 2026-07-09: verify the copied image against the loader-side checksum.
| The loader summed (ci_size>>2) longwords of the SOURCE buffer just before
| supervisor(); we recompute the same sum over the DESTINATION after the copy
| (and after cpusha on 040/060, so we read what the kernel will fetch).  A
| mismatch means the image was corrupted in transit (source/dest overlap, DMA,
| whatever) -- flashing color0 forever beats jumping into a corrupt kernel.
	movel	a2@(ci_vaddr),a0	| a0 = copied image
	movel	a2@(ci_size),d0
	lsrl	#2,d0			| longword count
	moveq	#0,d1
cksloop:
	addl	a0@+,d1
	subql	#1,d0
	bne	cksloop
	cmpl	a2@(ci_cksum),d1
	beq	cksok
cksbad:
	movew	#0xfff,0xdff180		| white / red flash = corrupt copy
	movew	#0xf00,0xdff180
	bra	cksbad
cksok:
	movel	a2@(ci_entry),a0	| kernel entry point
	movel	a2@(ci_d0),d0		| d0 = boot method (EXEC1)
	movel	a2@(ci_d1),d1		| d1 = bootinfo *
	jmp	a0@			| into the kernel, MMU off"""),
    ("keep", 63, 64),
    ("emit", """\
| A do-nothing MMU root pointer (includes the following long as well)"""),
    ("keep", 66, 69),
]


def main():
    if len(sys.argv) != 2:
        print("usage: python3 transforms/transform_copyit.py <path to copyit.s>")
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print("[FAIL] no such file: %s" % path)
        return 1

    raw = open(path, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != ORIG_SHA256:
        print("[FAIL] this is not the copyit.s this transformation was derived from.")
        print()
        print("         file     %s" % path)
        print("         sha256   %s" % got)
        print("         expected %s" % ORIG_SHA256)
        print()
        print("       The recipe copies surviving lines out of your file BY LINE NUMBER, so against")
        print("       a different original it would keep the wrong lines and still write a file.")
        print("       Nothing has been written.  apply.sh verifies the archive for the same reason.")
        return 1

    src = raw.decode("latin1").split("\n")
    out = []
    for step in RECIPE:
        if step[0] == "keep":
            out.extend(src[step[1]:step[2]])
        else:
            out.extend(step[1].split("\n"))
    result = "\n".join(out).encode("latin1")

    made = hashlib.sha256(result).hexdigest()
    if made != RESULT_SHA256:
        print("[FAIL] the transformation produced an unexpected result.")
        print("         sha256   %s" % made)
        print("         expected %s" % RESULT_SHA256)
        print("       Nothing has been written.  This means the recipe and the checked-in result")
        print("       have diverged -- a bug here, not in your copy.")
        return 1

    open(path, "wb").write(result)
    kept = sum(s[2] - s[1] for s in RECIPE if s[0] == "keep")
    ours = sum(len(s[1].split("\n")) for s in RECIPE if s[0] == "emit")
    print("[*] copyit.s rebuilt: %d lines kept from your copy, %d written by this project" % (kept, ours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
