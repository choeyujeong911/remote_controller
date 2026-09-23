import subprocess
import tempfile
import zipfile
import time
import psutil
from pathlib import Path


class NativeExecutor:
    name = "NativeExecutor"

    def execute(self, package: Path, received_time: float):

        if package.suffix.lower() != ".zip":
            raise ValueError("Workload must be a ZIP file")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)

            print(f"[NATIVE] Extracting {package.name}")

            with zipfile.ZipFile(package, "r") as zip_file:
                zip_file.extractall(work_dir)

            main_file = work_dir / "main.py"

            if not main_file.exists():
                raise FileNotFoundError("main.py not found")

            # 실제 코드 실행 직전
            execution_start = time.perf_counter()
            overhead = execution_start - received_time

            print(f"[NATIVE] Running {main_file.name}")
            print(f"[NATIVE] Overhead: {overhead:.4f} sec")

            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            ps_process = psutil.Process(process.pid)

            cpu_samples = []
            memory_samples = []

            # CPU 측정을 위한 초기화
            ps_process.cpu_percent(interval=None)

            while process.poll() is None:
                try:
                    cpu = ps_process.cpu_percent(interval=0.5)
                    memory = ps_process.memory_info().rss / (1024 * 1024)

                    cpu_samples.append(cpu)
                    memory_samples.append(memory)

                except psutil.NoSuchProcess:
                    break

            stdout, stderr = process.communicate()

            execution_time = time.perf_counter() - execution_start

            avg_cpu = (
                sum(cpu_samples) / len(cpu_samples)
                if cpu_samples else 0.0
            )

            max_cpu = (
                max(cpu_samples)
                if cpu_samples else 0.0
            )

            avg_memory = (
                sum(memory_samples) / len(memory_samples)
                if memory_samples else 0.0
            )

            max_memory = (
                max(memory_samples)
                if memory_samples else 0.0
            )

            print(
                f"[NATIVE] Process finished "
                f"(exit={process.returncode})"
            )

            return {
                "output": stdout + stderr,
                "overhead": overhead,
                "execution_time": execution_time,
                "avg_cpu": avg_cpu,
                "max_cpu": max_cpu,
                "avg_memory": avg_memory,
                "max_memory": max_memory,
            }