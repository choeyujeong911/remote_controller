# remote_controller
중앙 컴퓨터의 Controller, 각 워커 데스크톱의 Agent, Executor를 모두 포함하는 저장소
- Controller: `controller.py`, 중앙 컴퓨터에서 실행되어 워커 데스크톱의 IP, Agent의 Port를 입력하면 Job을 보내는 일종의 Client. 지표를 CSV로 저장하기도 함
- Agent: `agent.py`, Host OS에서 실행되어 중앙의 Controller가 보내온 Job을 Executor에게 전달해 처리하고 결과물과 지표를 Controller에게 다시 보내주는 역할
- Executor: 각 환경(Native, WSL2, Guest VM, Docker 컨테이너 등)에서 실행되어 Agent가 준 Job을 처리하고 결과를 Agent에게 반환하는 역할
    - `native_exe.py`: 별도로 실행되진 않고, 에이전트에서 자식 프로세스로 Job을 처리하기 위한 함수를 가지는 모듈(모드 1)
    - `guestvm_exe.py`: Guest VM 내부에서 별도로 실행되는 모듈(모드 2)
    - `wsl2vm_exe.py`: WSL2 배포판 내부에서 별도로 실행되는 모듈(모드 3)
    - `docker_exe.py`: Host OS에서 별도로 실행되는 모듈(모드 4)
    - `k8s_exe.py`: 미정(master node에서 실행할까 싶음)


### 추가 작업
- winget으로 Git, Python 설치
    ```Powershell
    winget install -e --id Git.Git
    winget install -e --id Python.Python.3.12
    ```
- 코드 실행에 필요한 컴파일러/인터프리터 설치
    ```Powershell
    powershell -ExecutionPolicy Bypass -File .\install-dev.ps1
    ```
- MNIST Job 처리에 필요한 라이브러리 설치
    ```Powershell
    pip install torch==2.14.0 torchvision==0.29.0
    python -c "import torch, torchvision; print(torch.__version__); print(torchvision.__version__)"
    ```