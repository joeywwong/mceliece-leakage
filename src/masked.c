#include "gf2.h"

#ifdef GF2_TRACE
void gf2_masked_trace(gf2_matrix *a, gf2_event events[GF2_DECISIONS])
#else
void gf2_masked(gf2_matrix *a)
#endif
{
#ifdef GF2_TRACE
    size_t index = 0;
#endif
    for (unsigned p = 0; p < GF2_N; ++p) {
        for (unsigned r = p + 1; r < GF2_N; ++r) {
            unsigned bit = (unsigned)((a->w[r][0] >> p) & UINT64_C(1));
            uint64_t mask = UINT64_C(0) - (uint64_t)bit;
#ifdef GF2_TRACE
            gf2_event *e = &events[index++];
            *e = (gf2_event){p, r, bit, 1, 0};
#endif
            for (unsigned w = 0; w < GF2_WORDS; ++w) {
                uint64_t operand = a->w[p][w] & mask;
#ifdef GF2_TRACE
                /* Abstract operand Hamming weight, NOT sampled power/EM. */
                e->operand_hw += gf2_hw(operand);
#endif
                a->w[r][w] ^= operand;
            }
        }
    }
}
