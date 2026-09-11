import socket
import struct
from pathlib import Path

file = Path(input("Code file: ").strip('"'))
host = input("Agent IP: ").strip()
port = int(input("Agent Port: "))

data = file.read_bytes()
name = file.name.encode()

with socket.create_connection((host, port)) as s:
    s.sendall(struct.pack("!I", len(name)))
    s.sendall(name)

    s.sendall(struct.pack("!Q", len(data)))
    s.sendall(data)

    print("\n--- Result ---")

    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        print(chunk.decode(errors="replace"), end="")