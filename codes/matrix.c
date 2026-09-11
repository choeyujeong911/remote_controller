#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

double now(void) {
    LARGE_INTEGER f, t;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / f.QuadPart;
}

int main(void) {
    const int N = 300;
    const double TARGET = 10.0;

    double *A = malloc(N * N * sizeof(double));
    double *B = malloc(N * N * sizeof(double));
    double *C = malloc(N * N * sizeof(double));

    srand(42);

    for (int i = 0; i < N * N; i++) {
        A[i] = (double)rand() / RAND_MAX;
        B[i] = (double)rand() / RAND_MAX;
    }

    double start = now();
    int runs = 0;
    double checksum = 0;

    while (now() - start < TARGET) {
        for (int i = 0; i < N; i++)
            for (int j = 0; j < N; j++) {
                double sum = 0;

                for (int k = 0; k < N; k++)
                    sum += A[i*N+k] * B[k*N+j];

                C[i*N+j] = sum;
            }

        checksum = 0;

        for (int i = 0; i < N*N; i++)
            checksum += C[i];

        runs++;
    }

    printf("workload=matrix\n");
    printf("runs=%d\n", runs);
    printf("checksum=%.6f\n", checksum);
    printf("elapsed=%.3fs\n", now() - start);

    free(A);
    free(B);
    free(C);

    return 0;
}