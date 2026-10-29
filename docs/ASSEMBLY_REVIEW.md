# Manual review of the measured host kernels

Reviewed with GCC 11.4.0
`gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3)`, target `x86_64-linux-gnu`, GNU objdump.
Flags: `-std=c11 -Wall -Wextra -Wpedantic -Werror -fno-lto`, plus `-O2` or `-O3`.
Each source file is compiled separately. No LTO, architecture-specific tuning, assembly
barriers or special branch-suppression flags. Benchmark linkage excludes the traced objects.

`make inspect` saves `objdump -d -M intel --disassemble=gf2_branchy build/O2/bench`
and the analogous masked/O3 outputs in `results/O{2,3}-gf2_{branchy,masked}.asm`.
Compiler, flags, target, tool versions and binary hashes are in `results/inspect.json`.
These are the linked binaries used by `make bench`, not a separately optimized illustration.
Addresses below are link-time addresses in the reviewed binaries, not runtime ASLR addresses.

| Build/function | Observed instruction sequence | Interpretation |
|---|---|---|
| O2 branchy | `0x1704: bt rcx,rdi`; `0x1708: jae 0x16f0` | The matrix coefficient enters carry; the branch skips row loads/XOR/stores when it is zero. |
| O3 branchy | `0x170d: bt rcx,r8`; `0x1711: jae 0x16f8` | The same data-dependent skip remains. The taken-update path uses an SSE `pxor` for both words. |
| O2 masked | `shr rdx,cl; and edx,1; neg rdx` at `0x1791..0x1797`, followed by two masked updates | Coefficient becomes an unsigned all-zero/all-one mask; no coefficient-dependent conditional branch observed. |
| O3 masked | `shr rax,cl; and eax,1; neg rax` at `0x1798..0x179e`, then `punpcklqdq`, `pand`, `pxor`, `movups` | Mask is broadcast across the two-word row and used in an unconditional vector update. |

The masked conditional branches at O2 `0x17af` / `0x17b9` and O3 `0x17b8` /
`0x17c2` follow comparisons of the public row/pivot counters with 64 / 63.
Other jumps are unconditional loop transfers. There are no calls or secret-dependent
indirect jumps in either inspected kernel. The masked loads/stores use base + 16*row,
base + 16*pivot, and (in scalar code) +8; the stack save/restore in O2 is also fixed.
Shift counts come from the public pivot index. Matrix values feed masks and XOR data,
not addresses. The baseline's candidate row address is public, but whether additional
pivot accesses and output stores happen depends on its coefficient.

This is a bounded manual data-flow review, not a formal constant-time proof. `endbr64`
and padding instructions are compiler/toolchain artifacts. We did not assess speculation,
all microarchitectural latency behavior, or physical leakage, and the Hamming-weight
model does not describe these actual scalar/SSE circuits. Recompile with another compiler,
flags, target, or source and repeat the review; source-level masking alone is insufficient.
Fixed control flow does not establish power/EM resistance or defeat Leaky McEliece.
