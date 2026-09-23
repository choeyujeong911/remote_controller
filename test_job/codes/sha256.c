#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#include <bcrypt.h>

#pragma comment(lib, "bcrypt.lib")

double now(void) {
    LARGE_INTEGER f, t;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / f.QuadPart;
}

int main(void) {
    const DWORD SIZE = 1024 * 1024;
    const double TARGET = 310.0;

    unsigned char *data = malloc(SIZE);
    memset(data, 'A', SIZE);

    BCRYPT_ALG_HANDLE alg;
    BCRYPT_HASH_HANDLE hash;

    DWORD objectSize, cb;
    unsigned char *object;
    unsigned char digest[32];

    BCryptOpenAlgorithmProvider(
        &alg, BCRYPT_SHA256_ALGORITHM, NULL, 0
    );

    BCryptGetProperty(
        alg, BCRYPT_OBJECT_LENGTH,
        (PUCHAR)&objectSize, sizeof(objectSize), &cb, 0
    );

    object = malloc(objectSize);

    double start = now();
    unsigned long long count = 0;

    while (now() - start < TARGET) {
        BCryptCreateHash(
            alg, &hash, object, objectSize,
            NULL, 0, 0
        );

        BCryptHashData(hash, data, SIZE, 0);
        BCryptFinishHash(hash, digest, 32, 0);
        BCryptDestroyHash(hash);

        for (DWORD i = 0; i < SIZE; i++)
            data[i] = digest[i % 32];

        count++;
    }

    printf("workload=sha256\n");
    printf("hashes=%llu\n", count);

    printf("digest=");
    for (int i = 0; i < 32; i++)
        printf("%02x", digest[i]);

    printf("\nelapsed=%.3fs\n", now() - start);

    free(object);
    free(data);

    BCryptCloseAlgorithmProvider(alg, 0);

    return 0;
}