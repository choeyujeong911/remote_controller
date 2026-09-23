import math
import time

TARGET = 310

def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2

    limit = math.isqrt(n)
    d = 3

    while d <= limit:
        if n % d == 0:
            return False
        d += 2

    return True

start = time.perf_counter()
n = 2
count = 0
last_prime = 0

while time.perf_counter() - start < TARGET:
    if is_prime(n):
        count += 1
        last_prime = n
    n += 1

elapsed = time.perf_counter() - start

print("workload=prime")
print(f"tested_until={n}")
print(f"primes={count}")
print(f"last_prime={last_prime}")
print(f"elapsed={elapsed:.3f}s")