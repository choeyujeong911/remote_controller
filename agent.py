import socket
import struct
import tempfile
import time
import json
from pathlib import Path

from native_exe import NativeExecutor


# ==========================================
# Agent 설정
# ==========================================

HOST = "0.0.0.0"
PORT = 5000

# Central Controller
CENTRAL = "203.250.35.180"

# Hyper-V Guest VM
GUEST_VM_IP = "172.30.230.163"
GUEST_VM_PORT = 5001

# WSL2 VM
WSL2_VM_IP = "172.21.21.206"
WSL2_VM_PORT = 5002


# ==========================================
# Socket Utility
# ==========================================

def recv_n(sock, n):
    data = b""

    while len(data) < n:
        chunk = sock.recv(n - len(data))

        if not chunk:
            raise ConnectionError("Connection closed")

        data += chunk

    return data


# ==========================================
# Executor 선택
# ==========================================

def select_executor():
    print("=== Select Executor ===")
    print("1. NativeExecutor")
    print("2. GuestVMExecutor")
    print("3. WSL2VMExecutor")
    print("4. DockerExecutor")

    while True:
        choice = input("Select [1-4]: ").strip()

        if choice == "1":
            return 1

        elif choice == "2":
            return 2

        elif choice == "3":
            return 3

        elif choice == "4":
            print(
                "[ERROR] DockerExecutor "
                "is not implemented yet."
            )

        else:
            print(
                "[ERROR] Enter a number "
                "from 1 to 4."
            )


# ==========================================
# Native 실행
# ==========================================

def execute_native(package, received_time):
    executor = NativeExecutor()

    print(
        f"[NATIVE] Sending "
        f"{package.name} "
        f"to NativeExecutor"
    )

    return executor.execute(
        package,
        received_time
    )


# ==========================================
# Remote Executor 실행
#
# Guest VM / WSL2 공통
# ==========================================

def execute_remote(
    package,
    received_time,
    target_ip,
    target_port,
    executor_name
):
    data = package.read_bytes()
    name = package.name.encode("utf-8")

    print(
        f"[{executor_name}] "
        f"Connecting to "
        f"{target_ip}:{target_port}"
    )

    with socket.create_connection(
        (target_ip, target_port)
    ) as remote_socket:

        print(
            f"[{executor_name}] "
            f"Connected"
        )

        # ==================================
        # Workload 전송
        #
        # 4 bytes : 파일명 길이
        # N bytes : 파일명
        # 8 bytes : ZIP 크기
        # N bytes : ZIP
        # ==================================

        remote_socket.sendall(
            struct.pack(
                "!I",
                len(name)
            )
        )

        remote_socket.sendall(
            name
        )

        remote_socket.sendall(
            struct.pack(
                "!Q",
                len(data)
            )
        )

        remote_socket.sendall(
            data
        )

        print(
            f"[{executor_name}] "
            f"Workload sent "
            f"({len(data)} bytes)"
        )

        # ==================================
        # READY 신호 대기
        #
        # Remote Executor가
        # ZIP 압축 해제를 완료하고
        # main.py 실행 직전에
        # 0x01을 전송
        # ==================================

        ready = recv_n(
            remote_socket,
            1
        )

        if ready != b"\x01":
            raise RuntimeError(
                f"Invalid READY signal "
                f"from {executor_name}"
            )

        # ==================================
        # Overhead 측정 종료
        #
        # Agent가 workload를 완전히
        # 수신한 시점부터
        # Remote Executor의 READY를
        # 받은 시점까지
        # ==================================

        execution_ready_time = (
            time.perf_counter()
        )

        overhead = (
            execution_ready_time
            - received_time
        )

        print(
            f"[{executor_name}] "
            f"Execution started"
        )

        print(
            f"[{executor_name}] "
            f"Overhead: "
            f"{overhead:.4f} sec"
        )

        # ==================================
        # Metadata 수신
        #
        # 4 bytes : metadata 크기
        # N bytes : JSON
        # ==================================

        metadata_size = struct.unpack(
            "!I",
            recv_n(
                remote_socket,
                4
            )
        )[0]

        metadata_bytes = recv_n(
            remote_socket,
            metadata_size
        )

        remote_metadata = json.loads(
            metadata_bytes.decode(
                "utf-8"
            )
        )

        # ==================================
        # stdout / stderr 수신
        #
        # 8 bytes : output 크기
        # N bytes : output
        # ==================================

        output_size = struct.unpack(
            "!Q",
            recv_n(
                remote_socket,
                8
            )
        )[0]

        output = recv_n(
            remote_socket,
            output_size
        )

        print(
            f"[{executor_name}] "
            f"Execution finished"
        )

        # ==================================
        # Agent 공통 결과 형식
        # ==================================

        return {
            "output":
                output,

            # Host Agent clock으로 측정
            "overhead":
                overhead,

            # Remote Executor에서 측정
            "execution_time":
                remote_metadata[
                    "execution_time"
                ],

            "avg_cpu":
                remote_metadata[
                    "avg_cpu"
                ],

            "max_cpu":
                remote_metadata[
                    "max_cpu"
                ],

            "avg_memory":
                remote_metadata[
                    "avg_memory"
                ],

            "max_memory":
                remote_metadata[
                    "max_memory"
                ]
        }


# ==========================================
# Executor별 Wrapper
# ==========================================

def execute_guest_vm(
    package,
    received_time
):
    return execute_remote(
        package=package,
        received_time=received_time,
        target_ip=GUEST_VM_IP,
        target_port=GUEST_VM_PORT,
        executor_name="GuestVMExecutor"
    )


def execute_wsl2_vm(
    package,
    received_time
):
    return execute_remote(
        package=package,
        received_time=received_time,
        target_ip=WSL2_VM_IP,
        target_port=WSL2_VM_PORT,
        executor_name="WSL2VMExecutor"
    )


# ==========================================
# Executor 선택
# ==========================================

agent_mode = select_executor()

if agent_mode == 1:
    executor_name = "NativeExecutor"

elif agent_mode == 2:
    executor_name = "GuestVMExecutor"

elif agent_mode == 3:
    executor_name = "WSL2VMExecutor"

else:
    raise RuntimeError(
        "Invalid executor mode"
    )


print()
print(
    f"[SELECTED] Mode {agent_mode}: "
    f"{executor_name}"
)


# ==========================================
# 선택된 Remote Executor 정보 출력
# ==========================================

if agent_mode == 2:
    print(
        f"[TARGET] "
        f"{GUEST_VM_IP}:"
        f"{GUEST_VM_PORT}"
    )

elif agent_mode == 3:
    print(
        f"[TARGET] "
        f"{WSL2_VM_IP}:"
        f"{WSL2_VM_PORT}"
    )


# ==========================================
# Agent Server
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

    print()
    print(
        f"[READY] Worker Agent "
        f"listening on {PORT}"
    )

    print(
        f"[EXECUTOR] "
        f"{executor_name}"
    )

    print(
        "[INFO] Press Ctrl+C to stop"
    )

    # ======================================
    # Main Loop
    # ======================================

    try:
        while True:

            client, addr = (
                server.accept()
            )

            with client:

                print()
                print(
                    f"[CONNECTED] "
                    f"{addr[0]}:"
                    f"{addr[1]}"
                )

                # ==========================
                # Central IP 검사
                # ==========================

                if addr[0] != CENTRAL:
                    print(
                        "[DENIED] "
                        "Unauthorized IP"
                    )
                    continue

                try:

                    # ======================
                    # 파일 이름 수신
                    # ======================

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

                    # ======================
                    # 파일 크기 수신
                    # ======================

                    file_size = struct.unpack(
                        "!Q",
                        recv_n(
                            client,
                            8
                        )
                    )[0]

                    # ======================
                    # Workload 수신
                    # ======================

                    data = recv_n(
                        client,
                        file_size
                    )

                    # ======================
                    # Agent가 ZIP을
                    # 완전히 받은 시점
                    # ======================

                    received_time = (
                        time.perf_counter()
                    )

                    print(
                        f"[RECEIVED] "
                        f"{name} "
                        f"({len(data)} bytes)"
                    )

                    # ======================
                    # 임시 ZIP 저장
                    # ======================

                    with tempfile.TemporaryDirectory() as temp_dir:

                        package = (
                            Path(temp_dir)
                            / Path(name).name
                        )

                        package.write_bytes(
                            data
                        )

                        # ==================
                        # Mode 1
                        # Native
                        # ==================

                        if agent_mode == 1:

                            result = (
                                execute_native(
                                    package,
                                    received_time
                                )
                            )

                        # ==================
                        # Mode 2
                        # Hyper-V Guest VM
                        # ==================

                        elif agent_mode == 2:

                            result = (
                                execute_guest_vm(
                                    package,
                                    received_time
                                )
                            )

                        # ==================
                        # Mode 3
                        # WSL2 VM
                        # ==================

                        elif agent_mode == 3:

                            result = (
                                execute_wsl2_vm(
                                    package,
                                    received_time
                                )
                            )

                        else:

                            raise RuntimeError(
                                "Unsupported "
                                "executor mode"
                            )

                        # ==================
                        # Controller에
                        # 보낼 Metadata
                        # ==================

                        metadata = {
                            "agent_mode":
                                agent_mode,

                            "overhead":
                                result[
                                    "overhead"
                                ],

                            "execution_time":
                                result[
                                    "execution_time"
                                ],

                            "avg_cpu":
                                result[
                                    "avg_cpu"
                                ],

                            "max_cpu":
                                result[
                                    "max_cpu"
                                ],

                            "avg_memory":
                                result[
                                    "avg_memory"
                                ],

                            "max_memory":
                                result[
                                    "max_memory"
                                ]
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

                        # ==================
                        # Controller로 반환
                        #
                        # 4 bytes
                        # metadata size
                        #
                        # N bytes
                        # metadata JSON
                        #
                        # 8 bytes
                        # output size
                        #
                        # N bytes
                        # stdout/stderr
                        # ==================

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
                            f"[DONE] {name} | "
                            f"mode={agent_mode}, "
                            f"overhead="
                            f"{result['overhead']:.4f}s, "
                            f"execution="
                            f"{result['execution_time']:.4f}s"
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
            "Worker Agent"
        )
