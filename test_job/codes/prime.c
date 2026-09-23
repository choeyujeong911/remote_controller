#include <stdio.h>
#include <windows.h>

double now(void) {
    LARGE_INTEGER f, t;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / f.QuadPart;
}

int is_prime(unsigned long long n) {
    if (n < 2) return 0;
    if (n % 2 == 0) return n == 2;

    for (unsigned long long d = 3; d <= n / d; d += 2)
        if (n % d == 0)
            return 0;

    return 1;
}

int main(void) {
    const double TARGET = 310.0;

    unsigned long long n = 2;
    unsigned long long count = 0;
    unsigned long long last_prime = 0;

    double start = now();

    while (now() - start < TARGET) {
        if (is_prime(n)) {
            count++;
            last_prime = n;
        }

        n++;
    }

    printf("workload=prime\n");
    printf("tested_until=%llu\n", n);
    printf("primes=%llu\n", count);
    printf("last_prime=%llu\n", last_prime);
    printf("elapsed=%.3fs\n", now() - start);

    return 0;
}