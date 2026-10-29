# Leakage-aware GF(2) row operations

**Research case study**

Gaussian elimination in Classic McEliece connects a concrete computation to side-channel
information flow. Brinkmann, Chuengsatiansup, May, Nowakowski and Yarom's
[*Leaky McEliece*](https://tches.iacr.org/index.php/TCHES/article/view/12043)
(TCHES 2025(2), 94–125) motivates studying row-operation leakage; its
[abstract](https://casa.rub.de/en/research/publications/detail/leaky-mceliece-secret-key-recovery-from-highly-erroneous-side-channel-information)
reports an attack on a constant-time implementation. This completed educational case study
follows **mechanism → evidence → mitigation → costs and limitations**. It does not reproduce
that attack or recover an actual McEliece key.

**Target and models.** Original C11 code transforms a packed 64×128 matrix `[L | R]` into
`[I | X]`, where `LX=R` over GF(2). `L` is unit lower triangular. Fixed pivots deliberately
exclude row exchanges, rank failures and Goppa-code structure. Across 2,016 `(pivot,row)`
pairs, the kernels differ only in how they apply the XOR:

| Baseline: branchy | Mitigation: masked |
|---|---|
| XOR both words only if coefficient is 1 | Always XOR both words, ANDing the pivot with `0 - (uint64_t)bit` |
| Coefficient controls a branch and accesses | Public indices control traversal and addresses |

The architectural model observes branches and ordered memory addresses, excluding data
values and physical switching. Separate instrumented builds expose a **software operation
oracle**. Binary flips provide a **synthetic noisy-observation model**; operand Hamming
weights provide an **abstract activity model**. Only the host timings below are measured
performance observations.

**Correctness and host evidence.** `make all` completed in Ubuntu/WSL2 on an AMD Ryzen 7
7735U, GCC 11.4.0, x86_64-linux-gnu. Both O2 and O3 tests reported **526 PASS, 0 FAIL**:
524 matrices plus two corrupted-output checks. Cases include identity/dense/sparse/random
`L`, zero/all-one/random `R`, and 512 seeded random instances. Both kernels agree; an
independent bitwise matrix product verifies original `L × X = R`. ASan/UBSan also passed
526 checks with findings configured to terminate execution.

Actual host time in ns/matrix, **median [Q1–Q3]**:

| Variant / L class | GCC O2 | GCC O3 |
|---|---:|---:|
| Branchy / identity | 1508.24 [1479.03–1565.83] | 1279.43 [1234.34–1333.93] |
| Branchy / random | 8571.74 [8430.17–8881.08] | 7120.21 [6904.43–7343.69] |
| Masked / identity | 2698.34 [2647.13–2795.99] | 1645.22 [1603.15–1750.21] |
| Masked / random | 2701.94 [2645.37–2809.21] | 1664.26 [1623.34–1732.05] |

Each group has 101 batches × 512 eliminations after warm-up, using a monotonic raw clock,
deterministically shuffled group order, and preserved output checksums. Times include copies
and checksum arithmetic. WSL scheduling, frequency and cache/predictor effects remain;
these class differences do not establish real PQC key leakage. No t-test/dudect run was made.

**Information flow and limits.** The exact software trace contains 1,007 executed baseline
XORs; the masked version executes all 2,016. In this triangular model, decisions equal
original below-diagonal `L` bits. With one noisy observation per bit, the estimator simply
returns that observation: accuracies at flip rates 0/.1/.2/.3/.4 were
100/90.18/78.97/70.83/58.53%, versus 50.05% for always-zero. This is a controlled oracle
demonstration, not sophisticated decoding. Seeds and raw observations are retained.

Manual review of the actual O2/O3 binaries found coefficient-dependent `bt`/`jae` in the
baseline and only public loop branches in the masked kernel. However, modeled masked
operand weight averages are 0 for decision zero and 33.248 for decision one, separated
by construction. Fixed control flow does not provide physical power/EM resistance.
These selection masks are not randomized secret-sharing masks. The
[versioned McEliece source](https://lib.mceliece.org/libmceliece-20240513/crypto_kem/6960119f/vec/pk_gen.c.html)
already uses masked XORs; removing our teaching baseline's branch does not defeat the paper's attack.

**Reproduce and extend.** Branch: `feat/gf2-rowop-leakage-study`.
The exact tested source and binary SHA-256 values are recorded in `results/*.json`.
Run `make all` from the repository in Ubuntu. Flags:
`-std=c11 -Wall -Wextra -Wpedantic -Werror -fno-lto`, plus `-O2` / `-O3`;
sanitizers use O1. Exact commands, toolchain, hashes and raw data are in
[README](README.md), [run log](docs/RUN_LOG.md), `results/`, and the
[assembly review](docs/ASSEMBLY_REVIEW.md). See [full generated results](RESULTS.md).
Methodological references: [official implementation notes](https://classic.mceliece.org/impl.html),
[BearSSL](https://bearssl.org/constanttime.html), [dudect](https://github.com/oreparaz/dudect).

Next: map assumptions onto a pinned real implementation, then inspect a Cortex-M4 build
and design an actual measurement. Hardware/physical capture: **NOT RUN**; chip, flash and
connections remain unverified. No firmware was flashed or cross-compiled; a possible
512 KiB STM32F407VET6 must not inherit a 1 MiB layout. None of this certifies a secure implementation.
