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


# ==========================================
# File / Directory
# ==========================================

path = Path(
    input("File or directory: ").strip('"')
)

if not path.exists():
    print("[ERROR] Path does not exist.")
    raise SystemExit


temp_dir = None


try:

    # ======================================
    # Directory인 경우 ZIP 생성
    # ======================================

    if path.is_dir():

        answer = input(
            f'"{path.name}" is a directory. '
            f'Compress and send it? [y/n]: '
        ).strip().lower()

        if answer != "y":
            print("[CANCELLED]")
            raise SystemExit

        temp_dir = tempfile.TemporaryDirectory()

        zip_base = (
            Path(temp_dir.name)
            / path.name
        )

        zip_path = shutil.make_archive(
            str(zip_base),
            "zip",
            root_dir=path
        )

        file = Path(zip_path)

        print(
            f"[COMPRESSED] {file.name}"
        )

    else:

        file = path


    # ======================================
    # Agent 정보
    # ======================================

    host = input(
        "Agent IP: "
    ).strip()

    port = int(
        input("Agent Port: ")
    )

    repeat_count = int(
        input("How many times? ")
    )

    if repeat_count < 1:
        print(
            "[ERROR] Repeat count "
            "must be at least 1."
        )
        raise SystemExit


    # ======================================
    # Workload는 한 번만 읽음
    # ======================================

    data = file.read_bytes()

    name = file.name.encode(
        "utf-8"
    )


    print()
    print(
        f"[WORKLOAD] {file.name}"
    )

    print(
        f"[SIZE] {len(data)} bytes"
    )

    print(
        f"[TARGET] {host}:{port}"
    )

    print(
        f"[REPEAT] {repeat_count}"
    )


    # ======================================
    # CSV 설정
    # ======================================

    result_file = Path(
        "./result.csv"
    )

    file_exists = (
        result_file.exists()
    )


    # ======================================
    # 반복 테스트
    # ======================================

    for run_number in range(
        1,
        repeat_count + 1
    ):

        print()
        print(
            "=" * 50
        )

        print(
            f"RUN "
            f"{run_number}/"
            f"{repeat_count}"
        )

        print(
            "=" * 50
        )


        try:

            # ==================================
            # 매 테스트마다 새로운 TCP 연결
            # ==================================

            with socket.create_connection(
                (host, port)
            ) as s:

                total_start = (
                    time.perf_counter()
                )


                # ==============================
                # 파일 이름 크기
                # ==============================

                s.sendall(
                    struct.pack(
                        "!I",
                        len(name)
                    )
                )


                # ==============================
                # 파일 이름
                # ==============================

                s.sendall(
                    name
                )


                # ==============================
                # 파일 크기
                # ==============================

                s.sendall(
                    struct.pack(
                        "!Q",
                        len(data)
                    )
                )


                # ==============================
                # ZIP 데이터
                # ==============================

                s.sendall(
                    data
                )


                print(
                    f"[SENT] "
                    f"{file.name} "
                    f"({len(data)} bytes)"
                )


                # ==============================
                # Agent 응답
                #
                # 4 bytes : metadata 크기
                # N bytes : metadata JSON
                # 8 bytes : output 크기
                # N bytes : stdout/stderr
                # ==============================


                # ------------------------------
                # Metadata 크기
                # ------------------------------

                metadata_size = (
                    struct.unpack(
                        "!I",
                        recv_n(
                            s,
                            4
                        )
                    )[0]
                )


                # ------------------------------
                # Metadata
                # ------------------------------

                metadata_bytes = (
                    recv_n(
                        s,
                        metadata_size
                    )
                )

                metadata = json.loads(
                    metadata_bytes.decode(
                        "utf-8"
                    )
                )


                # ------------------------------
                # Output 크기
                # ------------------------------

                output_size = (
                    struct.unpack(
                        "!Q",
                        recv_n(
                            s,
                            8
                        )
                    )[0]
                )


                # ------------------------------
                # Output
                # ------------------------------

                output = recv_n(
                    s,
                    output_size
                )


                # ==============================
                # Total Response Time
                # ==============================

                total_time = (
                    time.perf_counter()
                    - total_start
                )


            # ==================================
            # Workload 출력
            # ==================================

            print()
            print(
                "--- Result ---"
            )

            print(
                output.decode(
                    errors="replace"
                )
            )


            # ==================================
            # Metrics 출력
            # ==================================

            print(
                "=== System Metrics ==="
            )

            print(
                f"Run                 : "
                f"{run_number}/"
                f"{repeat_count}"
            )

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


            # ==================================
            # CSV 저장
            # ==================================

            with result_file.open(
                "a",
                newline="",
                encoding="utf-8"
            ) as csvfile:

                writer = csv.writer(
                    csvfile
                )


                # CSV 최초 생성 시 Header
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

                    file_exists = True


                # 결과 한 행 추가
                writer.writerow([
                    metadata[
                        "agent_mode"
                    ],
                    f"{total_time:.4f}",
                    f"{metadata['overhead']:.4f}",
                    f"{metadata['execution_time']:.4f}",
                    f"{metadata['avg_cpu']:.2f}",
                    f"{metadata['max_cpu']:.2f}",
                    f"{metadata['avg_memory']:.2f}",
                    f"{metadata['max_memory']:.2f}"
                ])


            print(
                f"[SAVED] "
                f"Run {run_number}"
            )


        # ======================================
        # 특정 Run 실패
        # ======================================

        except Exception as e:

            print(
                f"[ERROR] "
                f"Run {run_number} failed: "
                f"{type(e).__name__}: {e}"
            )


    # ==========================================
    # 전체 완료
    # ==========================================

    print()
    print(
        "=" * 50
    )

    print(
        f"[COMPLETED] "
        f"{repeat_count} runs requested"
    )

    print(
        f"[RESULT FILE] "
        f"{result_file.resolve()}"
    )


finally:

    if temp_dir:
        temp_dir.cleanup()