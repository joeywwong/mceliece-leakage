# Leakage-aware GF(2) row operations

A small, original C11 case study of leakage in GF(2) row operations.
Start with [CASE_STUDY.md](CASE_STUDY.md); see [RESULTS.md](RESULTS.md) for generated
results and [assembly review](docs/ASSEMBLY_REVIEW.md) for the inspected machine code.

This educational case study is inspired by Gaussian elimination in Classic McEliece.
It is **not a reproduction of Leaky McEliece, a real key-recovery attack, or a secure cryptographic implementation**.
The branchy baseline deliberately introduces a simpler leakage mechanism than the paper studies.

## What this project demonstrates — short summary

This is a **small, reproducible GF(2) Gaussian-elimination leakage case study**, motivated by the role of row operations in Classic McEliece key generation and the *Leaky McEliece* paper (TCHES/CHES 2025).

**Research question:** What information is exposed when a row-operation decision controls a conditional XOR, and what changes when that XOR is rewritten as an unconditional masked update?

- **Computation:** Eliminate a toy 64 × 128 binary matrix `[L | R]`, where the 64 × 64 left block `L` is unit lower triangular. Verify that the result is `[I | X]` with `L·X = R` over GF(2).
- **Deliberately branchy baseline:** `if (bit) row ^= pivot;` — data controls whether row loads/XORs/stores occur.
- **Selection-mask variant:** `row ^= pivot & (0 - bit);` — the same mathematical result, with a fixed row-update schedule in the inspected x86 binaries.
- **Evidence:** An instrumented **software decision trace**, a reproducible **synthetic bit-flip simulation**, an **abstract Hamming-weight model**, host runtime benchmarks, and inspection of the GCC `-O2`/`-O3` binaries.
- **Validation:** 524 deterministic test matrices plus two negative checks; the repository reports 526 PASS / 0 FAIL at `-O2`, `-O3` and under ASan/UBSan. The independent oracle checks the original `L·X = R` relation.

**Key distinction:** The instrumented decisions and noisy observations are **models/simulations**, not physical traces. The host timings are real host measurements, but **not measured side-channel attacks**. This project does **not** recover a Classic McEliece key, reproduce the paper's decoder, or demonstrate security against power/EM leakage. The paper attacks a constant-time reference implementation, so removing this project's deliberately introduced branch does **not** neutralize that attack.

**Start here:** [Case study report](CASE_STUDY.md) · [Results summary](RESULTS.md) · [Assembly review](docs/ASSEMBLY_REVIEW.md)

## Reproduce

Dependencies: a Linux/POSIX environment, GCC, GNU Make, Python 3.8+ (standard library only),
and GNU objdump. No network, package install, or cryptographic library is required to run.
From this directory in Ubuntu/WSL:

```sh
make all
```

The equivalent individual targets, in order, are:

```sh
make OPT=O2 test trace bench
make OPT=O3 test bench
make OPT=O2 inspect sanitize report
```

From Windows PowerShell, the exact full-run command is:

```powershell
wsl -d Ubuntu --exec bash -lc 'cd /mnt/c/Users/wongy/mceliece-leakage && make all'
```

Select `Ubuntu` explicitly: on this machine the default WSL distribution is Docker Desktop.
The build serializes targets to keep benchmarks from competing with its own test jobs.
`make test`, `make trace`, `make bench`, `make inspect`, `make sanitize`, and `make report`
are also individually available. `OPT=O2` is the default. `make inspect` builds both optimization
levels and disassembles the **linked benchmark binaries**. `make report` refuses stale source
or binary hashes; missing successful runs are marked NOT RUN. Sanitizer support is probed;
unavailable compiler/runtime support is SKIP, whereas a failing real test is a failure.
UBSan is configured to terminate on its first finding. Every failed test command exits nonzero.

Raw CSV, stdout/stderr, source/binary SHA-256 hashes, commands, Git state, timestamps,
compiler/version/target/flags, CPU and OS details are written into `results/` (gitignored).
`build/` is also ignored. Each rerun replaces that target's previous results; copy `results/`
elsewhere inside your own archive before rerunning if you want to retain a run. There is no
automatic cleanup. The generated, compact `RESULTS.md` can be tracked with the report.
Build configuration stamps invalidate objects when compiler identity or flags change.
Reinspect after any such change; the manual assembly review only covers its named GCC builds.

## Kernel and correctness

Each matrix has 64 rows of two `uint64_t` words: word 0 is `L`, word 1 is `R`.
Column zero is the least significant bit. `L` must be unit lower triangular; `R` is arbitrary.
Forward elimination visits pivots `p=0..63`, rows `r=p+1..63`, words `w=0..1`.
There are 64*63/2 = 2,016 row decisions. It transforms `[L | R]` into `[I | X]` with `LX=R`.
The API assumes the precondition; it has no row exchanges, pivot search, rank failure,
Goppa-code structure, key generation, or key serialization.

| Variant | Update at each visited row | Intended architectural behavior |
|---|---|---|
| `branchy` | `if (bit) row[w] ^= pivot[w];` | Secret-dependent conditional row XOR |
| `masked` | `mask = UINT64_C(0) - (uint64_t)bit; row[w] ^= pivot[w] & mask;` | Both words accessed and updated at every pair |

All shifts are by 0..63, and word arithmetic is unsigned. For bit 0 the mask is zero;
for bit 1 it is all ones. This is a **selection mask**, not random sharing or a physical
side-channel masking scheme. The functions are separate translation units, linked with
`-fno-lto`; no compiler-specific branch suppression or `volatile` is used in the kernels.
Flags: `-std=c11 -Wall -Wextra -Wpedantic -Werror -fno-lto -O2` (or `-O3`).

Correctness uses 12 structured cases: four `L` classes (identity, dense, sparse, random)
crossed with zero, all-one and random `R`, plus 512 random matrices with seeds 0..511.
SplitMix64 is the documented deterministic generator, not a cryptographic RNG.
Every case checks both ordinary and instrumented variants, exact differential equality,
identity on the left, and **independent bit-by-bit multiplication** of original `L` by output
`X` against original `R`. Two deliberately corrupted outputs test the oracle's ability
to reject errors. Thus each test executable reports 526 checks across 524 matrices.
Trace tests also check event ordering, both decisions, execution flags, and operand weights.

## Evidence and leakage models

**Architectural model.** Treat all entries of `L` and `R` as potentially secret, except the
known triangular shape and diagonal. Dimensions, loop indices and the base address are public.
An observer sees control-flow decisions and the ordered addresses of loads/stores, but not
register values or data-dependent switching. For the inspected masked binaries these observations
depend only on the public traversal. This statement is limited to these kernels and builds;
it does not cover arbitrary compiler transformations, the test harness, speculative behavior,
operand-dependent instruction latency, power, EM, or faults.

**A — Instrumented operation oracle, SOFTWARE MODEL.** The same source is separately compiled
with `-DGF2_TRACE`; it records `(pivot,row)`, the current coefficient, and whether the source
row XOR executed. These counters are transparent ground truth, not sampled instructions or
an external side channel. No instrumentation is linked into the benchmark. Trace seed is
`0x20261030`. In this special triangular model, a processed pivot's left word is just its
basis bit. Earlier eliminations cannot change later coefficients. Consequently the 2,016
decisions equal the original below-diagonal entries of `L`. The original coefficients in
the CSV are for evaluation, not information supplied to a supposed attacker. There is no
actual McEliece private key to recover here.

**B — Noisy observations, SIMULATION.** For rates 0, .1, .2, .3, .4, flip each decision
using fresh SplitMix64 outputs, a continuous stream seeded `0x5eed20261030`, and threshold
`floor(p * 2^64)` (computed with integer arithmetic). This models independent binary flips;
the pseudorandom stream makes the run reproducible. The estimate is simply the noisy observed
bit. It never consults truth when choosing its estimate. The preselected always-zero predictor
is the baseline. Raw observations and estimates are in `results/noise-O2.csv`.
There is one observation per bit, no repetition, error-correcting decoder or structural attack.
At p=.4 the expected accuracy is only 60%; realized accuracy has finite-sample variation.

**C — Masked operand activity, ABSTRACT MODEL.** The instrumented masked version sums
Hamming weights of the two masked pivot words. A zero decision gives weight zero; a one
decision includes the unit pivot and therefore gives a positive weight. This separation
holds by construction, not because a power acquisition worked. It shows a possible
data-dependent intermediate despite a fixed schedule. Real switching depends on prior
values, registers, buses, glitches, instructions and device physics; this model establishes
neither the strength nor exploitability of any real power/EM leakage.

## Host benchmark method

The timer is `clock_gettime(CLOCK_MONOTONIC_RAW)` when available, otherwise `CLOCK_MONOTONIC`.
There are 101 measured batches per variant/class, 512 fresh eliminations per batch and
8 warm-up batches per group. Each class uses a pool of 64 deterministic inputs, seeds
`0xb000+i`; corresponding identity/random cases have identical `R`. Each iteration copies
an original matrix so it never accidentally benchmarks an already-eliminated matrix.
The pool is rotated by sample number, and all four groups are shuffled each round with
SplitMix64 seed `0x42b00b5`. Reuse of a small pool favors warm caches and may train predictors.

The timer includes the 1,024-byte input copy, kernel call, and checksum arithmetic over all
output words. A volatile sink and separate compilation preserve the work. Both variants
are checked on all pool inputs before timing. CSV records batch elapsed nanoseconds;
summary values are per-matrix batch averages, with median and inclusive Q1/Q3. They are not
individual-operation latency distributions. Inputs, seeds, warm-up and batching are identical
at O2 and O3; the runs occurred separately. No affinity pinning, frequency control, cache
flushing, independent repeated sessions, Welch t-test, or dudect analysis was performed.
These noisy WSL results describe costs and class differences, not real PQC key leakage.
A nonsignificant timing result would be inconclusive, never a proof of no leakage.

## Source map and references

- `src/gf2.h`, `src/branchy.c`, `src/masked.c`: matrix interface and the two kernels.
- `src/support.c`, `src/test.c`: generator, independent oracle and tests.
- `src/trace.c`, `src/bench.c`: separate instrumented and timing drivers.
- `scripts/lab.py`, `scripts/build_config.py`, `Makefile`: execution, simulation, provenance and reporting.
- `docs/ASSEMBLY_REVIEW.md`, `docs/RUN_LOG.md`: manual evidence and exact execution history.

Marcus Brinkmann, Chitchanok Chuengsatiansup, Alexander May, Julian Nowakowski and Yuval Yarom,
[*Leaky McEliece: Secret Key Recovery From Highly Erroneous Side-Channel Information*](https://tches.iacr.org/index.php/TCHES/article/view/12043),
IACR TCHES 2025(2), 94–125. The [paper's abstract](https://casa.rub.de/en/research/publications/detail/leaky-mceliece-secret-key-recovery-from-highly-erroneous-side-channel-information)
describes noisy row-operation leakage and an attack on a constant-time reference implementation
on STM32L592. It motivates this study; the study does not implement its decoding attack.

The [official implementation overview](https://classic.mceliece.org/impl.html) explains timing
protections and the need to test compiled code. The inspected
[`libmceliece-20240513/6960119f/vec/pk_gen.c`](https://lib.mceliece.org/libmceliece-20240513/crypto_kem/6960119f/vec/pk_gen.c.html)
already uses masked XORs and also handles pivot preparation, column movement and rank failures.
It is a versioned `vec` source example, not asserted to be the exact paper experiment.
Replacing our baseline branch with a mask does **not** defeat the paper's attack.

[BearSSL's constant-time discussion](https://bearssl.org/constanttime.html) provides context
for control flow, addresses and compiler behavior. [dudect](https://github.com/oreparaz/dudect)
is a reference for statistical timing testing; this lab does not run it or claim its results.
References consulted include the paper's abstract, source listing,
implementation overview, BearSSL discussion and dudect README. Direct retrieval of the
implementation/source pages initially returned 502; their indexed full text was available.
The journal landing page denied automated access; the abstract was read on the linked institutional publication page.

## Next steps and hardware status

First map the toy operations onto a pinned Classic McEliece implementation and explicitly
identify where its pivot strategy, matrix structure and leakage assumptions differ. Then
inspect a Cortex-M4 build and plan DWT-cycle or physical-capture experiments with verified
hardware and a documented acquisition setup. Hardware is **NOT RUN**, and firmware has
not been cross-compiled. Chip identity, flash capacity and connections have not been verified.
In particular, do not assume a 1 MiB layout for a possible STM32F407VET6 with 512 KiB flash.
No board was flashed, and no physical measurement or security certification is claimed.
