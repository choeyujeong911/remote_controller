## https://wikidocs.net/236898 참고
import docker

# 1. 로컬 환경의 도커 데몬과 연결 (소켓 자동 인식)
client = docker.from_env()

# 2. 우분투 컨테이너를 백그라운드에서 실행하고 'echo' 명령어 전달
# (이미지가 없으면 알아서 다운로드합니다)
container = client.containers.run(
    "ubuntu:latest",
    "echo Hello from Python Docker SDK in 2026!",
    detach=True
)

# 3. 컨테이너가 실행을 마치고 남긴 로그를 출력
print(container.logs().decode('utf-8'))

# 4. 다 쓴 컨테이너를 깨끗하게 삭제
container.remove()