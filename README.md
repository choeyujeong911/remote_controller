# remote_controller
중앙 컨트롤러와 워커 에이전트를 관리하는 저장소
- `controller_ui.py`: PyQt6 기반 중앙 컨트롤러 UI 프로토타입
- 워커 통신, WOL, SSH, 작업 실행 기능은 UI 설계 이후 단계에서 다시 구현 예정


### 추가 작업

### 중앙 컨트롤러 UI 미리보기
- PyQt6 설치: `pip install -r requirements-ui.txt`
- UI 실행: `python controller_ui.py`
- 현재 화면은 워커 카드, 패널 추가/삭제 다이얼로그, 기본 정보·리소스·작업 상태 표시와 기능 버튼 배치만 제공합니다. 실제 WOL, SSH, 에이전트 통신은 후속 작업에서 연결합니다.

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
