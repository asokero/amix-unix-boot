# Working in this repository with an AI assistant

This file is for coding agents. `README.md` explains what the loader is and what the patches fix;
`NOTICE` defines what may and may not be distributed here. This file is the short list of rules
an agent will otherwise break, and every one of them was learned by breaking it.

The companion repository is the kernel port, `amix-040-060-port`. Its `AGENTS.md` carries the
measurement discipline that applies to both; this file adds what is specific to the loader.

## What this repository is

Patches and a build script for `unix_boot`, the AmigaOS program that loads an Amiga UNIX kernel.
A dozen files and no sources: the reader supplies the original archive.

**It is Markus Wild's program, not Commodore's.** It is derived from Commodore's AMIX boot code,
so every file inside the archive carries a 1991 Commodore copyright header while the program as a
whole is his, and no licence is stated for his work. Reading the files alone gives the wrong
answer, which is how the wrong attribution survived in this repository for a while. Do not
describe the loader as Commodore's.

## The one thing that makes this repository different

**A mistake here does not produce a wrong answer. It produces a machine that does not boot.**

The loader disables the MMU, moves the kernel, and jumps into it, with interrupts off and no
operating system left underneath. There is no diagnostic layer below this code. That is why:

* the nine compiler warnings are known and deliberately **not** fixed — adding prototypes can
  change code generation, and that needs a hardware smoke test rather than a tidy-up;
* changes here are worth a boot test in a way that documentation changes never are.

## Rules that are not style

* **Never commit sources.** `.gitignore` excludes `src/`, `bin/`, `.extract/`, `*.lha` and the
  local build area for a reason, and the reason is in `NOTICE`. If a build step wants a file
  tracked, that is a bug in the build step.
* **A file that is untracked but *not* ignored is the dangerous state**, and it does not look
  dangerous. It sits quietly outside every check that reads the index, and then `git add -A`
  sweeps it in. `local-worktree/` is 3.7 MB of the reader's own extracted sources — the whole
  original of every file this repository is careful not to carry — and one missing `.gitignore`
  line is all that stands between it and a commit. Check before you stage:

  ```sh
  git ls-files --others --exclude-standard    # must print nothing
  ```
* **The patches are generated from a working tree. Never edit a `.patch` by hand.** A fix applied
  to generated output is reverted the next time it is regenerated — that has already happened
  here once. Fix the source, regenerate, and verify the result is byte-identical to what the old
  patch produced.
* **Keep diff context minimal.** Context lines are original text, and `NOTICE` measures how much
  of each file this repository carries. One line of context is the working default; three
  doubled the figure for `unix_boot.c` before it was narrowed.
* **`copyit.s` is rebuilt, not patched, and must stay that way.** A diff of it carries the whole
  original file, because the change removes 40 of its 70 lines. `transforms/transform_copyit.py`
  holds our text and the line numbers of what survives, and reads the surviving lines out of the
  reader's own copy. Turning it back into a patch would undo the point of it.
* **Both hash gates stay.** `apply.sh` verifies the archive before touching anything, and the
  transform verifies its own output. The transform cuts by line number, so against a different
  original it would keep the wrong lines and still write a file that looks fine. Never relax a
  gate to make a run succeed.
* **If you change text the transform emits, update `RESULT_SHA256` — and prove the change was
  what you thought it was.** A comment-only edit must produce a byte-identical loader binary. If
  it does not, the edit was not comment-only.

## What this build supports, and what it does not

**68040 and 68060 only.** On a 68060, SetPatch must run before booting; it is a precondition, not
a tweak.

**On a 68030 it gurus**, `8000 0038` — vector 56, a 68030 MMU Configuration Error — immediately
after the handoff, with any kernel including the stock one. Note where it fails: the loader hands
off correctly and the kernel reaches its own `pstart`, faulting on the `pmove` sequence that
enables the MMU. Reproduced on real hardware and under both emulators. It is `ISSUE-1` in the
kernel port's `KNOWN-ISSUES.md`, deferred rather than fixed, and it may be worth fixing one day.

So: **do not describe this as a drop-in replacement for the original loader.** On a 68030 the
answer is the original archive from Aminet, which boots the same kernels without trouble. Gaining
the 68040 and 68060 cost the 68030, and that trade is deliberate but not permanent.

## Facts that are easy to get backwards

* **`arp.library` is the original prebuilt loader's requirement, not this build's.** The shipped
  binary references it; the sources do not, and neither does `unix_boot040`. Measured, not
  assumed.
* **The patched loader is mandatory for the kernel port** — for three independent reasons, any
  one sufficient: the stock `copyit.s` uses 68030 `pmove` and traps before the kernel runs; the
  stock `rel.c` mis-applies PC-relative relocations, of which the FPU support package has about
  330; and `cputype` is poked into the kernel *by the loader*, so without it a 68060 runs every
  CPU-gated path as a 68040.
* **Only the third of those depends on the FPU package**, so a build without it is not a reason
  to reach for the stock loader.

## Before you claim you are finished

```sh
git ls-files --others --exclude-standard   # nothing, or something is about to leak
sh apply.sh /path/to/unix_boot.lha         # verifies the archive, patches, rebuilds copyit.s
sh build.sh                                # -> src/unix_boot040
```

Run the first one before you stage anything, not after. It is the only check here whose failure
is silent and permanent: a build error you fix, but a source file pushed to a public repository
is in someone's clone before you notice.

Then check the two things a green build does not tell you: that the patched sources are
byte-identical to what the previous patches produced, and that the resulting binary is unchanged
unless you meant to change it. If you meant to change behaviour, say plainly that it has not been
tested on hardware — because it has not.
