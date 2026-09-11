import time
import random

N = 120
TARGET = 10

random.seed(42)
A = [[random.random() for _ in range(N)] for _ in range(N)]
B = [[random.random() for _ in range(N)] for _ in range(N)]

start = time.perf_counter()
runs = 0
checksum = 0.0

while time.perf_counter() - start < TARGET:
    C = [[sum(A[i][k] * B[k][j] for k in range(N))
          for j in range(N)] for i in range(N)]
    checksum = sum(map(sum, C))
    runs += 1

elapsed = time.perf_counter() - start

print(f"workload=matrix")
print(f"runs={runs}")
print(f"checksum={checksum:.6f}")
print(f"elapsed={elapsed:.3f}s")