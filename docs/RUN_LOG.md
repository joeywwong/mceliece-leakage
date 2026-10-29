# Executed commands and provenance

Machine metadata timestamps in `results/*.json` use UTC.

The working directory was `C:\Users\wongy\mceliece-leakage`. Initial `git status --short`
reported that this was not a repository; the only existing project file was a local assignment
under `docs/`. Its contents were preserved outside version control. `git init -b feat/gf2-rowop-leakage-study`
created the requested branch. There is no upstream library checkout to modify.

Environment discovery first tried `wsl --exec bash -lc ...`; sandboxed WSL access was denied.
After running with the needed access, the default distribution lacked Bash. `wsl --list --verbose`
identified Docker Desktop as default and a separate Ubuntu installation. Subsequent commands
explicitly selected `-d Ubuntu`. No tools were installed and no WSL configuration was changed.

These development-run commands actually executed, in order:

```powershell
wsl -d Ubuntu --exec bash -lc 'cd /mnt/c/Users/wongy/mceliece-leakage && make test trace bench inspect sanitize report'
wsl -d Ubuntu --exec bash -lc 'cd /mnt/c/Users/wongy/mceliece-leakage && make OPT=O3 test bench && make report'
```

They passed. The build/report workflow was then tightened to track build configuration,
reject stale binary hashes and make sanitizer findings fatal. LF checkout rules were added.
The definitive full run used the completed C, Makefile and Python sources:

```powershell
wsl -d Ubuntu --exec bash -lc 'cd /mnt/c/Users/wongy/mceliece-leakage && make all'
```

`make all` executed these serialized subcommands, all with exit status zero:

```sh
make OPT=O2 test trace bench
make OPT=O3 test bench
make OPT=O2 inspect sanitize report
```

| Action | Executed result |
|---|---|
| O2 tests | PASS=526 FAIL=0; 524 matrices and 2 oracle-negative checks |
| O3 tests | PASS=526 FAIL=0; same cases |
| O2 trace + simulation | 2,016 verified decisions; 1,007 baseline XORs; five synthetic noise rates |
| O2 / O3 host benchmarks | 404 CSV rows each; 101 samples for each of four groups |
| O2 / O3 disassembly | Four linked-kernel listings generated and manually reviewed |
| ASan + UBSan O1 | PASS=526 FAIL=0; no diagnostic; fail-fast sanitizer settings |
| Results generation | Completed source and binary hashes checked; RESULTS.md generated |
| ARM cross-compilation, physical board and power/EM acquisition | NOT RUN; optional extension, no verified board/capture setup |
| Welch test / dudect | NOT RUN; descriptive timing summary only |

The final run replaced the earlier target files in `results/`; report values are from this
last completed run, not selected extrema across runs. Benchmark checksums at both levels:
`6a21bd400be26160`. Raw elapsed times and sample order are in `bench-O2.csv` / `bench-O3.csv`.
`trace-O2.csv` and `noise-O2.csv` are **software model/simulation output**, not captured side channels.
The published branch history was rewritten locally to keep the assignment out of version
control. The C, Makefile and Python sources are unchanged from the tested run; their exact
SHA-256 values are recorded in the JSON metadata.

Toolchain: GCC `11.4.0-1ubuntu1~22.04.3`, target `x86_64-linux-gnu`; Python 3.10.12;
Linux `5.15.146.1-microsoft-standard-WSL2`, glibc 2.35; AMD Ryzen 7 7735U with Radeon Graphics.
Full compiler/objdump versions, flags, commands, source checksums and binary checksums are
retained in the JSON files. Each ordinary object is built with `-std=c11 -Wall -Wextra
-Wpedantic -Werror -fno-lto` and its named optimization level; traced objects additionally
use `-DGF2_TRACE`. The sanitizer command list records its separate O1 configuration.

No pushes, pull requests, messages, hardware flashing, or upstream-code edits were performed.
