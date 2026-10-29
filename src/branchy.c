#include "gf2.h"

#ifdef GF2_TRACE
void gf2_branchy_trace(gf2_matrix *a, gf2_event events[GF2_DECISIONS])
#else
void gf2_branchy(gf2_matrix *a)
#endif
{
#ifdef GF2_TRACE
    size_t index = 0;
#endif
    for (unsigned p = 0; p < GF2_N; ++p) {
        for (unsigned r = p + 1; r < GF2_N; ++r) {
            unsigned bit = (unsigned)((a->w[r][0] >> p) & UINT64_C(1));
#ifdef GF2_TRACE
            gf2_event *e = &events[index++];
            *e = (gf2_event){p, r, bit, 0, 0};
#endif
            /* Deliberately leaky teaching baseline. */
            if (bit != 0) {
                for (unsigned w = 0; w < GF2_WORDS; ++w)
                    a->w[r][w] ^= a->w[p][w];
#ifdef GF2_TRACE
                e->executed = 1;
#endif
            }
        }
    }
}
