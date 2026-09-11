import hashlib
import time

TARGET = 310
data = b"A" * (1024 * 1024)

start = time.perf_counter()
count = 0
digest = b""

while time.perf_counter() - start < TARGET:
    digest = hashlib.sha256(data).digest()
    data = digest * (len(data) // len(digest))
    count += 1

elapsed = time.perf_counter() - start

print("workload=sha256")
print(f"hashes={count}")
print(f"digest={digest.hex()}")
print(f"elapsed={elapsed:.3f}s")