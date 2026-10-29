#include "gf2.h"

/* SplitMix64: deterministic test data only, not a cryptographic RNG. */
uint64_t gf2_random(uint64_t *state)
{
    uint64_t z = (*state += UINT64_C(0x9e3779b97f4a7c15));
    z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
    return z ^ (z >> 31);
}

void gf2_generate(gf2_matrix *a, enum gf2_class kind, uint64_t seed)
{
    for (unsigned r = 0; r < GF2_N; ++r) {
        uint64_t diagonal = UINT64_C(1) << r;
        uint64_t below = diagonal - UINT64_C(1);
        uint64_t bits = gf2_random(&seed);
        if (kind == GF2_IDENTITY) bits = 0;
        if (kind == GF2_DENSE) bits = UINT64_MAX;
        if (kind == GF2_SPARSE) {
            bits &= gf2_random(&seed);
            bits &= gf2_random(&seed);
        }
        a->w[r][0] = diagonal | (bits & below);
        a->w[r][1] = gf2_random(&seed);
    }
}

int gf2_equal(const gf2_matrix *a, const gf2_matrix *b)
{
    for (unsigned r = 0; r < GF2_N; ++r)
        for (unsigned w = 0; w < GF2_WORDS; ++w)
            if (a->w[r][w] != b->w[r][w]) return 0;
    return 1;
}

int gf2_invariant(const gf2_matrix *original, const gf2_matrix *output)
{
    /* Independent bit-by-bit matrix multiplication, not elimination. */
    for (unsigned i = 0; i < GF2_N; ++i) {
        if (output->w[i][0] != (UINT64_C(1) << i)) return 0;
        for (unsigned j = 0; j < GF2_N; ++j) {
            unsigned product = 0;
            for (unsigned k = 0; k < GF2_N; ++k)
                product ^= (unsigned)(((original->w[i][0] >> k) & 1U)
                                     & ((output->w[k][1] >> j) & 1U));
            if (product != ((original->w[i][1] >> j) & 1U)) return 0;
        }
    }
    return 1;
}

unsigned gf2_hw(uint64_t x)
{
    unsigned weight = 0;
    for (unsigned i = 0; i < 64; ++i) weight += (unsigned)((x >> i) & 1U);
    return weight;
}
