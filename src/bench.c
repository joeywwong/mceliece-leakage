#define _GNU_SOURCE
#include "gf2.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

enum { POOL = 64, BATCH = 512, SAMPLES = 101, WARMUP = 8 };
static gf2_matrix inputs[2][POOL];
static volatile uint64_t sink;
#ifdef CLOCK_MONOTONIC_RAW
#define BENCH_CLOCK CLOCK_MONOTONIC_RAW
#define BENCH_CLOCK_NAME "CLOCK_MONOTONIC_RAW"
#else
#define BENCH_CLOCK CLOCK_MONOTONIC
#define BENCH_CLOCK_NAME "CLOCK_MONOTONIC"
#endif

static uint64_t now(void)
{
    struct timespec ts;
    if (clock_gettime(BENCH_CLOCK, &ts) != 0) { perror("clock_gettime"); exit(1); }
    return (uint64_t)ts.tv_sec * UINT64_C(1000000000) + (uint64_t)ts.tv_nsec;
}

static uint64_t batch(unsigned variant, unsigned kind, unsigned offset)
{
    void (*kernel)(gf2_matrix *) = variant ? gf2_masked : gf2_branchy;
    uint64_t sum = 0;
    uint64_t start = now();
    for (unsigned i = 0; i < BATCH; ++i) {
        gf2_matrix work = inputs[kind][(i + offset) % POOL];
        kernel(&work);
        /* Consume every output word; overhead is intentionally included. */
        for (unsigned r = 0; r < GF2_N; ++r)
            sum += work.w[r][0] ^ work.w[r][1];
    }
    uint64_t elapsed = now() - start;
    sink += sum;
    return elapsed;
}

int main(void)
{
    uint64_t order_state = UINT64_C(0x42b00b5);
    for (unsigned i = 0; i < POOL; ++i) {
        gf2_generate(&inputs[0][i], GF2_IDENTITY, UINT64_C(0xb000) + i);
        gf2_generate(&inputs[1][i], GF2_RANDOM, UINT64_C(0xb000) + i);
        for (unsigned k = 0; k < 2; ++k) {
            gf2_matrix b = inputs[k][i], m = b;
            gf2_branchy(&b); gf2_masked(&m);
            if (!gf2_equal(&b, &m) || !gf2_invariant(&inputs[k][i], &b)) return 1;
        }
    }
    for (unsigned w = 0; w < WARMUP; ++w)
        for (unsigned group = 0; group < 4; ++group)
            (void)batch(group / 2, group % 2, w);
    puts("sample,order,variant,input_class,batch,elapsed_ns,ns_per_matrix");
    for (unsigned sample = 0; sample < SAMPLES; ++sample) {
        unsigned order[4] = {0, 1, 2, 3};
        for (unsigned j = 3; j > 0; --j) {
            unsigned k = (unsigned)(gf2_random(&order_state) % (j + 1));
            unsigned tmp = order[j]; order[j] = order[k]; order[k] = tmp;
        }
        for (unsigned j = 0; j < 4; ++j) {
            unsigned variant = order[j] / 2, kind = order[j] % 2;
            uint64_t elapsed = batch(variant, kind, sample);
            printf("%u,%u,%s,%s,%u,%" PRIu64 ",%.6f\n", sample, j,
                   variant ? "masked" : "branchy", kind ? "random" : "identity",
                   BATCH, elapsed, (double)elapsed / BATCH);
        }
    }
    fprintf(stderr, "timer=%s samples=%d batch=%d pool=%d warmup=%d checksum=%016" PRIx64 "\n",
            BENCH_CLOCK_NAME, SAMPLES, BATCH, POOL, WARMUP, sink);
    return ferror(stdout) ? 1 : 0;
}
