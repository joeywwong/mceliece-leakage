#ifndef GF2_H
#define GF2_H
#include <stddef.h>
#include <stdint.h>

enum { GF2_N = 64, GF2_WORDS = 2, GF2_DECISIONS = 2016 };
typedef struct { uint64_t w[GF2_N][GF2_WORDS]; } gf2_matrix;
typedef struct {
    unsigned pivot, row, bit, executed, operand_hw;
} gf2_event;

/* Precondition: left block is unit lower triangular. No pivot search/failure. */
void gf2_branchy(gf2_matrix *a);
void gf2_masked(gf2_matrix *a);
void gf2_branchy_trace(gf2_matrix *a, gf2_event events[GF2_DECISIONS]);
void gf2_masked_trace(gf2_matrix *a, gf2_event events[GF2_DECISIONS]);

enum gf2_class { GF2_IDENTITY, GF2_DENSE, GF2_SPARSE, GF2_RANDOM };
uint64_t gf2_random(uint64_t *state);
void gf2_generate(gf2_matrix *a, enum gf2_class kind, uint64_t seed);
int gf2_equal(const gf2_matrix *a, const gf2_matrix *b);
int gf2_invariant(const gf2_matrix *original, const gf2_matrix *output);
unsigned gf2_hw(uint64_t x);
#endif
