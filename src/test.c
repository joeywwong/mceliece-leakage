#include "gf2.h"
#include <stdio.h>

static int check(const gf2_matrix *input)
{
    gf2_matrix b = *input, m = *input, bt = *input, mt = *input;
    gf2_event be[GF2_DECISIONS], me[GF2_DECISIONS];
    gf2_branchy(&b);
    gf2_masked(&m);
    gf2_branchy_trace(&bt, be);
    gf2_masked_trace(&mt, me);
    if (!gf2_equal(&b, &m) || !gf2_equal(&b, &bt) || !gf2_equal(&m, &mt)
        || !gf2_invariant(input, &b) || !gf2_invariant(input, &m)) return 0;
    size_t i = 0;
    for (unsigned p = 0; p < GF2_N; ++p)
        for (unsigned r = p + 1; r < GF2_N; ++r, ++i) {
            unsigned expected = (unsigned)((input->w[r][0] >> p) & 1U);
            if (be[i].pivot != p || be[i].row != r || be[i].bit != expected
                || be[i].executed != expected || me[i].pivot != p
                || me[i].row != r || me[i].bit != expected || me[i].executed != 1
                || me[i].operand_hw != (expected ? 1U + gf2_hw(m.w[p][1]) : 0U))
                return 0;
        }
    return i == GF2_DECISIONS;
}

int main(void)
{
    unsigned passed = 0, failed = 0;
    gf2_matrix a;
    for (unsigned kind = 0; kind < 4; ++kind)
        for (unsigned right = 0; right < 3; ++right) {
            gf2_generate(&a, (enum gf2_class)kind, UINT64_C(0x123456789));
            if (right < 2)
                for (unsigned r = 0; r < GF2_N; ++r)
                    a.w[r][1] = right ? UINT64_MAX : 0;
            if (check(&a)) ++passed;
            else { ++failed; fprintf(stderr, "FAIL class=%u R=%u\n", kind, right); }
        }
    for (uint64_t seed = 0; seed < 512; ++seed) {
        gf2_generate(&a, GF2_RANDOM, seed);
        if (check(&a)) ++passed;
        else { ++failed; fprintf(stderr, "FAIL seed=%llu\n", (unsigned long long)seed); }
    }
    /* Make sure the independent oracle rejects both kinds of corruption. */
    gf2_generate(&a, GF2_RANDOM, 7);
    gf2_matrix good = a;
    gf2_masked(&good);
    gf2_matrix bad = good;
    bad.w[63][0] ^= 1U;
    if (!gf2_invariant(&a, &bad)) ++passed; else ++failed;
    bad = good;
    bad.w[0][1] ^= UINT64_C(1) << 63;
    if (!gf2_invariant(&a, &bad)) ++passed; else ++failed;
    printf("PASS=%u FAIL=%u (524 matrices; 2 oracle-negative checks)\n", passed, failed);
    return failed ? 1 : 0;
}
