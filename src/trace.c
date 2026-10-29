#include "gf2.h"
#include <stdio.h>

int main(void)
{
    gf2_matrix original, b, m;
    gf2_event be[GF2_DECISIONS], me[GF2_DECISIONS];
    gf2_generate(&original, GF2_RANDOM, UINT64_C(0x20261030));
    b = m = original;
    gf2_branchy_trace(&b, be);
    gf2_masked_trace(&m, me);
    if (!gf2_equal(&b, &m) || !gf2_invariant(&original, &b)) return 1;
    puts("pivot,row,original_coefficient,decision,branchy_xor_executed,masked_xor_executed,masked_operand_hw");
    for (size_t i = 0; i < GF2_DECISIONS; ++i) {
        unsigned coefficient = (unsigned)((original.w[be[i].row][0] >> be[i].pivot) & 1U);
        if (coefficient != be[i].bit || be[i].executed != be[i].bit
            || be[i].bit != me[i].bit || me[i].executed != 1) return 1;
        printf("%u,%u,%u,%u,%u,%u,%u\n", be[i].pivot, be[i].row,
               coefficient, be[i].bit, be[i].executed, me[i].executed, me[i].operand_hw);
    }
    return ferror(stdout) ? 1 : 0;
}
