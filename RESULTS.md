# Completed host results

Generated from completed local runs only. Timing is host measured; operation traces, noisy observations and Hamming weights are software models/simulations.

- O2 correctness: PASS=526 FAIL=0 (524 matrices; 2 oracle-negative checks)
- O3 correctness: PASS=526 FAIL=0 (524 matrices; 2 oracle-negative checks)
- ASan/UBSan: PASS=526 FAIL=0 (524 matrices; 2 oracle-negative checks)
- Hardware: NOT RUN; no board access, firmware, or physical capture.

| Build | Variant | L class | Samples | Median ns/matrix | Q1–Q3 ns/matrix |
|---|---|---|---:|---:|---:|
| O2 | branchy | identity | 101 | 1508.24 | 1479.03–1565.83 |
| O2 | branchy | random | 101 | 8571.74 | 8430.17–8881.08 |
| O2 | masked | identity | 101 | 2698.34 | 2647.13–2795.99 |
| O2 | masked | random | 101 | 2701.94 | 2645.37–2809.21 |
| O3 | branchy | identity | 101 | 1279.43 | 1234.34–1333.93 |
| O3 | branchy | random | 101 | 7120.21 | 6904.43–7343.69 |
| O3 | masked | identity | 101 | 1645.22 | 1603.15–1750.21 |
| O3 | masked | random | 101 | 1664.26 | 1623.34–1732.05 |

Each sample batches 512 eliminations; 8 warm-up batches per group; 64 inputs per class. Copying and an output checksum are included. Groups are deterministically shuffled each round. Spread is the inclusive interquartile range. No Welch t-test or dudect run was performed. Scheduling, caches, branch prediction, frequency changes and WSL can affect results. These class comparisons do not establish key leakage or prove its absence.

Software operation trace: 2016 decisions, 1007 branchy XORs, 2016 masked XORs. Matrix seed `0x20261030`.

Synthetic binary flips; one observation per decision; estimator returns observation. Noise seed `0x5eed20261030`; SplitMix64; continuous stream across rates. Baseline always predicts zero, chosen without looking at the truth distribution.

| Flip probability | Actual flips / bits | Estimator accuracy | Always-zero baseline |
|---:|---:|---:|---:|
| 0.0 | 0 / 2016 | 100.00% | 50.05% |
| 0.1 | 198 / 2016 | 90.18% | 50.05% |
| 0.2 | 424 / 2016 | 78.97% | 50.05% |
| 0.3 | 588 / 2016 | 70.83% | 50.05% |
| 0.4 | 836 / 2016 | 58.53% | 50.05% |

Abstract masked operand Hamming weights (two words combined; not power measurements):
- decision 0: n=1009, mean=0.000, range=0–0
- decision 1: n=1007, mean=33.248, range=23–40

Disassembly: O2/O3 linked kernels saved; see [manual review](docs/ASSEMBLY_REVIEW.md).

Raw CSV, stdout/stderr, compiler/CPU/OS metadata, binary and source SHA-256 hashes: `results/`. These files are local and gitignored. Regenerate with the README commands.
