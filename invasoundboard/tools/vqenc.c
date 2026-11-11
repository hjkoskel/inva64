/*
 * vqenc - vector quantiser for the C64 sound board.
 *
 * Reads float32 samples (already scaled to the 0..15 volume range, every
 * clip padded to a multiple of L), splits them into vectors of L samples
 * and trains a 256 entry codebook with k-means (k-means++ seeding).
 * The codebook is then rounded to integer 4-bit values and the vectors
 * are re-assigned to the rounded codebook, so the encoder sees exactly
 * what the C64 will play.
 *
 * Output:
 *   codebook file: L tables of 256 bytes; table j holds sample j of every
 *                  codeword (the player does  ldy codebook+j*256,x )
 *   index file   : one byte (codeword number) per vector
 *
 * usage: vqenc in.f32 L iterations codebook.bin indices.bin
 */
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define K 256

static int L;
static long N;
static float *vec;   /* N*L */
static float *cb;    /* K*L */
static unsigned char *idx;
static float *dist;

static unsigned long rng = 12345;
static double rnd(void)  /* deterministic, so builds are reproducible */
{
    rng = rng * 6364136223846793005UL + 1442695040888963407UL;
    return (rng >> 11) * (1.0 / 9007199254740992.0);
}

static float d2(const float *a, const float *b)
{
    float s = 0;
    for (int i = 0; i < L; i++) {
        float d = a[i] - b[i];
        s += d * d;
    }
    return s;
}

/* Assign every vector to its nearest codeword, return total error. */
static double assign(void)
{
    double err = 0;
    for (long n = 0; n < N; n++) {
        float best = FLT_MAX;
        int bk = 0;
        for (int k = 0; k < K; k++) {
            float d = d2(vec + n * L, cb + k * L);
            if (d < best) {
                best = d;
                bk = k;
            }
        }
        idx[n] = bk;
        dist[n] = best;
        err += best;
    }
    return err;
}

/* Move codewords to the mean of their vectors; reseed empty ones with the
 * worst represented vector. */
static void update(void)
{
    static double sum[K * 64];
    static long cnt[K];
    memset(sum, 0, sizeof(double) * K * L);
    memset(cnt, 0, sizeof cnt);
    for (long n = 0; n < N; n++) {
        cnt[idx[n]]++;
        for (int i = 0; i < L; i++)
            sum[idx[n] * L + i] += vec[n * L + i];
    }
    for (int k = 0; k < K; k++) {
        if (cnt[k]) {
            for (int i = 0; i < L; i++)
                cb[k * L + i] = sum[k * L + i] / cnt[k];
        } else {
            long w = 0;
            for (long n = 1; n < N; n++)
                if (dist[n] > dist[w])
                    w = n;
            memcpy(cb + k * L, vec + w * L, sizeof(float) * L);
            dist[w] = 0;
        }
    }
}

static void seed(void)
{
    long first = (long)(rnd() * N);
    memcpy(cb, vec + first * L, sizeof(float) * L);
    for (long n = 0; n < N; n++)
        dist[n] = d2(vec + n * L, cb);
    for (int k = 1; k < K; k++) {
        double tot = 0, r;
        long n;
        for (n = 0; n < N; n++)
            tot += dist[n];
        r = rnd() * tot;
        for (n = 0; n < N - 1 && (r -= dist[n]) > 0; n++)
            ;
        memcpy(cb + k * L, vec + n * L, sizeof(float) * L);
        for (long m = 0; m < N; m++) {
            float d = d2(vec + m * L, cb + k * L);
            if (d < dist[m])
                dist[m] = d;
        }
    }
}

static void round_cb(void)
{
    for (int i = 0; i < K * L; i++) {
        float v = floorf(cb[i] + 0.5f);
        cb[i] = v < 0 ? 0 : v > 15 ? 15 : v;
    }
}

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    int iters, it;
    double err = 0, sig = 0, mean = 0;

    if (argc != 6) {
        fprintf(stderr, "usage: vqenc in.f32 L iterations codebook.bin indices.bin\n");
        return 1;
    }
    L = atoi(argv[2]);
    iters = atoi(argv[3]);
    if (L < 1 || L > 64) {
        fprintf(stderr, "vqenc: bad vector length\n");
        return 1;
    }

    f = fopen(argv[1], "rb");
    if (!f) {
        perror(argv[1]);
        return 1;
    }
    fseek(f, 0, SEEK_END);
    n = ftell(f) / sizeof(float);
    rewind(f);
    N = n / L;
    vec = malloc(sizeof(float) * N * L);
    if (fread(vec, sizeof(float) * L, N, f) != (size_t)N) {
        fprintf(stderr, "vqenc: read error\n");
        return 1;
    }
    fclose(f);
    cb = malloc(sizeof(float) * K * L);
    idx = malloc(N);
    dist = malloc(sizeof(float) * N);

    seed();
    for (it = 0; it < iters; it++) {
        assign();
        update();
    }
    /* Refine with the codebook constrained to integer 4-bit values. */
    for (it = 0; it < 4; it++) {
        round_cb();
        assign();
        update();
    }
    round_cb();
    err = assign();

    for (long i = 0; i < N * L; i++)
        mean += vec[i];
    mean /= N * L;
    for (long i = 0; i < N * L; i++)
        sig += (vec[i] - mean) * (vec[i] - mean);
    fprintf(stderr, "vqenc: %ld vectors of %d, SNR %.1f dB\n", N, L,
            10 * log10(sig / err));

    f = fopen(argv[4], "wb");
    for (int j = 0; j < L; j++)
        for (int k = 0; k < K; k++)
            fputc((int)cb[k * L + j], f);
    fclose(f);
    f = fopen(argv[5], "wb");
    fwrite(idx, 1, N, f);
    fclose(f);
    return 0;
}
