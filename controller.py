import socket
import struct
import shutil
import tempfile
import time
import json
import csv
from pathlib import Path


def recv_n(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data += chunk
    return data


path = Path(input("File or directory: ").strip('"'))
if not path.exists():
    print("[ERROR] Path does not exist.")
    raise SystemExit

temp_dir = None

try:
    if path.is_dir():
        answer = input(
            f'"{path.name}" is a directory. '
            f'Compress and send it? [y/n]: '
        ).strip().lower()
        if answer != "y":
            print("[CANCELLED]")
            raise SystemExit
        temp_dir = tempfile.TemporaryDirectory()
        zip_base = (Path(temp_dir.name) / path.name)
        zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=path)
        file = Path(zip_path)
        print(f"[COMPRESSED] {file.name}")
    else:
        file = path

    host = input("Agent IP: ").strip()
    port = int(input("Agent Port: "))
    data = file.read_bytes()
    name = file.name.encode()
    print(
        f"[SENDING] {file.name} "
        f"({len(data)} bytes)"
    )

    with socket.create_connection((host, port)) as s:
        total_start = time.perf_counter()
        # 파일 이름 크기
        s.sendall(
            struct.pack(
                "!I",
                len(name)
            )
        )
        s.sendall(name)  # 파일 이름
        # 파일 크기
        s.sendall(
            struct.pack(
                "!Q",
                len(data)
            )
        )
        s.sendall(data)  # 파일 데이터
        print("[SENT]")
        print("\n--- Result ---")


        # ==============================
        # Agent 응답
        #
        # 4 bytes : metadata 크기
        # N bytes : metadata JSON
        # 8 bytes : output 크기
        # N bytes : stdout/stderr
        # ==============================


        # --------------------------
        # Metadata 크기
        # --------------------------

        metadata_size = struct.unpack("!I", recv_n(s, 4))[0]


        # --------------------------
        # Metadata
        # --------------------------

        metadata_bytes = recv_n(s, metadata_size)
        metadata = json.loads(metadata_bytes.decode("utf-8"))

        output_size = struct.unpack("!Q", recv_n(s, 8))[0]
        output = recv_n(s, output_size)

        total_time = (time.perf_counter() - total_start)
        print(output.decode(errors="replace"))

        print()
        print("=== System Metrics ===")

        print(
            f"Agent Mode          : "
            f"{metadata['agent_mode']}"
        )

        print(
            f"Total Response Time : "
            f"{total_time:.4f} sec"
        )

        print(
            f"Overhead Time       : "
            f"{metadata['overhead']:.4f} sec"
        )

        print(
            f"Execution Time      : "
            f"{metadata['execution_time']:.4f} sec"
        )

        print(
            f"Average CPU         : "
            f"{metadata['avg_cpu']:.2f} %"
        )

        print(
            f"Maximum CPU         : "
            f"{metadata['max_cpu']:.2f} %"
        )

        print(
            f"Average Memory      : "
            f"{metadata['avg_memory']:.2f} MB"
        )

        print(
            f"Maximum Memory      : "
            f"{metadata['max_memory']:.2f} MB"
        )


        # ==============================
        # CSV 저장
        # ==============================

        result_file = Path("./result.csv")

        file_exists = result_file.exists()


        with result_file.open(
            "a",
            newline="",
            encoding="utf-8"
        ) as csvfile:
            writer = csv.writer(csvfile)
            # CSV가 처음 생성된 경우, Header 작성
            if not file_exists:

                writer.writerow([
                    "agent_mode",
                    "total_time_sec",
                    "overhead_sec",
                    "execution_time_sec",
                    "avg_cpu_percent",
                    "max_cpu_percent",
                    "avg_memory_mb",
                    "max_memory_mb"
                ])
            writer.writerow([
                metadata["agent_mode"],
                f"{total_time:.4f}",
                f"{metadata['overhead']:.4f}",
                f"{metadata['execution_time']:.4f}",
                f"{metadata['avg_cpu']:.2f}",
                f"{metadata['max_cpu']:.2f}",
                f"{metadata['avg_memory']:.2f}",
                f"{metadata['max_memory']:.2f}"
            ])
        print(f"\n[SAVED] {result_file.resolve()}")
        
finally:
    if temp_dir:           
        temp_dir.cleanup()