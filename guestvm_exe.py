import socket
import struct
import tempfile
import subprocess
import zipfile
import time
import json
from pathlib import Path

import psutil


# ==========================================
# GuestVMExecutor 설정
# ==========================================

HOST = "0.0.0.0"
PORT = 5001

# 자원 사용량 Sampling 주기
SAMPLE_INTERVAL = 0.5


# ==========================================
# Socket Utility
# ==========================================

def recv_n(sock, n):

    data = b""

    while len(data) < n:

        chunk = sock.recv(
            n - len(data)
        )

        if not chunk:
            raise ConnectionError(
                "Connection closed"
            )

        data += chunk

    return data


# ==========================================
# Process + Child Process 자원 측정
# ==========================================

def get_process_tree_usage(process):

    try:

        processes = [
            process
        ]

        try:
            processes.extend(
                process.children(
                    recursive=True
                )
            )
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            pass


        total_cpu = 0.0
        total_memory = 0


        for proc in processes:

            try:

                total_cpu += (
                    proc.cpu_percent(
                        interval=None
                    )
                )

                total_memory += (
                    proc.memory_info().rss
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue


        memory_mb = (
            total_memory
            / (1024 * 1024)
        )


        return (
            total_cpu,
            memory_mb
        )


    except psutil.NoSuchProcess:

        return 0.0, 0.0


# ==========================================
# Workload 실행
# ==========================================

def execute_workload(
    package,
    client
):

    if package.suffix.lower() != ".zip":

        raise ValueError(
            "Workload must be a ZIP file"
        )


    with tempfile.TemporaryDirectory() as temp_dir:

        work_dir = Path(temp_dir)


        # ==================================
        # ZIP 압축 해제
        # ==================================

        print(
            f"[GUEST VM] Extracting "
            f"{package.name}"
        )

        with zipfile.ZipFile(
            package,
            "r"
        ) as zip_file:

            zip_file.extractall(
                work_dir
            )


        main_file = (
            work_dir
            / "main.py"
        )


        if not main_file.exists():

            raise FileNotFoundError(
                "main.py not found"
            )


        # ==================================
        # Agent에 READY 전달
        #
        # 이 신호를 받은 Host Agent가
        # Overhead 측정을 종료함
        # ==================================

        client.sendall(
            b"\x01"
        )


        # ==================================
        # 실제 코드 실행시간 측정 시작
        # ==================================

        execution_start = (
            time.perf_counter()
        )


        print(
            "[GUEST VM] "
            "Running main.py"
        )


        # ==================================
        # main.py 실행
        # ==================================

        process = subprocess.Popen(

            [
                "python",
                "-u",
                "main.py"
            ],

            cwd=work_dir,

            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )


        ps_process = psutil.Process(
            process.pid
        )


        # ==================================
        # CPU 초기화
        # ==================================

        try:

            ps_process.cpu_percent(
                interval=None
            )

        except psutil.NoSuchProcess:
            pass


        cpu_samples = []
        memory_samples = []


        # ==================================
        # 자원 사용량 Sampling
        # ==================================

        while process.poll() is None:

            time.sleep(
                SAMPLE_INTERVAL
            )

            try:

                cpu, memory = (
                    get_process_tree_usage(
                        ps_process
                    )
                )

                cpu_samples.append(
                    cpu
                )

                memory_samples.append(
                    memory
                )


            except psutil.NoSuchProcess:

                break


        # ==================================
        # stdout / stderr
        # ==================================

        stdout, stderr = (
            process.communicate()
        )


        # ==================================
        # 실행시간 종료
        # ==================================

        execution_time = (
            time.perf_counter()
            - execution_start
        )


        # ==================================
        # CPU 통계
        # ==================================

        if cpu_samples:

            avg_cpu = (
                sum(cpu_samples)
                / len(cpu_samples)
            )

            max_cpu = max(
                cpu_samples
            )

        else:

            avg_cpu = 0.0
            max_cpu = 0.0


        # ==================================
        # Memory 통계
        # ==================================

        if memory_samples:

            avg_memory = (
                sum(memory_samples)
                / len(memory_samples)
            )

            max_memory = max(
                memory_samples
            )

        else:

            avg_memory = 0.0
            max_memory = 0.0


        print(
            f"[GUEST VM] "
            f"Process finished "
            f"(exit={process.returncode})"
        )

        print(
            f"[GUEST VM] "
            f"Execution Time: "
            f"{execution_time:.4f} sec"
        )

        print(
            f"[GUEST VM] "
            f"CPU avg/max: "
            f"{avg_cpu:.2f}% / "
            f"{max_cpu:.2f}%"
        )

        print(
            f"[GUEST VM] "
            f"Memory avg/max: "
            f"{avg_memory:.2f} MB / "
            f"{max_memory:.2f} MB"
        )


        # ==================================
        # 결과
        # ==================================

        return {

            "output":
                stdout + stderr,

            "execution_time":
                execution_time,

            "avg_cpu":
                avg_cpu,

            "max_cpu":
                max_cpu,

            "avg_memory":
                avg_memory,

            "max_memory":
                max_memory
        }


# ==========================================
# GuestVMExecutor Server
# ==========================================

with socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
) as server:

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        (HOST, PORT)
    )

    server.listen()


    print(
        "=== GuestVMExecutor ==="
    )

    print(
        f"[READY] Listening on "
        f"{PORT}"
    )

    print(
        "[INFO] Press Ctrl+C to stop"
    )


    try:

        while True:

            client, addr = (
                server.accept()
            )


            with client:

                print(
                    f"[CONNECTED] "
                    f"{addr[0]}:{addr[1]}"
                )


                try:

                    # ==========================
                    # 파일 이름
                    # ==========================

                    name_len = struct.unpack(
                        "!I",
                        recv_n(
                            client,
                            4
                        )
                    )[0]


                    name = recv_n(
                        client,
                        name_len
                    ).decode(
                        "utf-8"
                    )


                    # ==========================
                    # 파일 크기
                    # ==========================

                    file_size = struct.unpack(
                        "!Q",
                        recv_n(
                            client,
                            8
                        )
                    )[0]


                    # ==========================
                    # ZIP 수신
                    # ==========================

                    data = recv_n(
                        client,
                        file_size
                    )


                    print(
                        f"[RECEIVED] "
                        f"{name} "
                        f"({len(data)} bytes)"
                    )


                    # ==========================
                    # 임시 ZIP 저장
                    # ==========================

                    with tempfile.TemporaryDirectory() as temp_dir:

                        package = (
                            Path(temp_dir)
                            / Path(name).name
                        )

                        package.write_bytes(
                            data
                        )


                        # ======================
                        # Workload 실행
                        # ======================

                        result = execute_workload(
                            package,
                            client
                        )


                        # ======================
                        # Metadata
                        # ======================

                        metadata = {

                            "execution_time":
                                result["execution_time"],

                            "avg_cpu":
                                result["avg_cpu"],

                            "max_cpu":
                                result["max_cpu"],

                            "avg_memory":
                                result["avg_memory"],

                            "max_memory":
                                result["max_memory"]
                        }


                        metadata_bytes = (
                            json.dumps(
                                metadata
                            ).encode(
                                "utf-8"
                            )
                        )


                        output = (
                            result["output"]
                        )


                        # ======================
                        # Host Agent로 반환
                        #
                        # READY는 이미 전송됨
                        #
                        # 4 bytes metadata size
                        # N bytes metadata
                        # 8 bytes output size
                        # N bytes output
                        # ======================

                        client.sendall(
                            struct.pack(
                                "!I",
                                len(
                                    metadata_bytes
                                )
                            )
                        )


                        client.sendall(
                            metadata_bytes
                        )


                        client.sendall(
                            struct.pack(
                                "!Q",
                                len(output)
                            )
                        )


                        client.sendall(
                            output
                        )


                        print(
                            f"[DONE] {name}"
                        )


                except Exception as e:

                    print(
                        f"[ERROR] "
                        f"{type(e).__name__}: "
                        f"{e}"
                    )


    except KeyboardInterrupt:

        print(
            "\n[STOPPED] "
            "GuestVMExecutor"
        )