"""PyQt6 front-end prototype for the central controller.

The widgets contain the presentation layer and the lightweight agent probe /
heartbeat connection. WOL, SSH, resource collection, and job dispatch remain
separate features to connect later.
"""

from __future__ import annotations

import sys
import json
import socket
import threading
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


WORKERS_FILE = Path(__file__).with_name("controller_workers.json")


@dataclass
class WorkerInfo:
    alias: str
    host: str
    port: str
    mac: str = ""


class AgentConnection(QThread):
    """Persistent TCP connection used for probe responses and heartbeats."""

    message_received = pyqtSignal(object)
    state_changed = pyqtSignal(str)

    def __init__(self, info: WorkerInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.info = info
        self.agent_username = ""
        self._stop_event = threading.Event()
        self._socket: socket.socket | None = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._socket.close()
            except OSError:
                pass

    def _send(self, payload: dict) -> None:
        if self._socket is None:
            return
        self._socket.sendall((json.dumps(payload) + "\n").encode("utf-8"))

    def run(self) -> None:
        while not self._stop_event.is_set():
            self.state_changed.emit("connecting")
            try:
                with socket.create_connection(
                    (self.info.host, int(self.info.port)), timeout=3
                ) as connection:
                    self._socket = connection
                    connection.settimeout(1.0)
                    self._send({"type": "probe"})
                    self.state_changed.emit("connected")
                    buffer = b""
                    while not self._stop_event.is_set():
                        try:
                            chunk = connection.recv(4096)
                        except socket.timeout:
                            continue
                        if not chunk:
                            raise ConnectionError("agent closed the connection")
                        buffer += chunk
                        while b"\n" in buffer:
                            raw, buffer = buffer.split(b"\n", 1)
                            if not raw.strip():
                                continue
                            try:
                                self.message_received.emit(json.loads(raw.decode("utf-8")))
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                continue
            except (OSError, ValueError, ConnectionError):
                if not self._stop_event.is_set():
                    self.state_changed.emit("offline")
                    self._stop_event.wait(3)
            finally:
                self._socket = None
        self.state_changed.emit("offline")


class AddWorkerDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        info: WorkerInfo | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("워커 패널 수정" if info else "워커 패널 추가")
        self.setMinimumWidth(430)

        intro = QLabel("연결할 워커 데스크톱의 정보를 입력하세요.")

        self.alias = QLineEdit()
        self.alias.setPlaceholderText("예: GPU 워커 01")
        self.address = QLineEdit()
        self.address.setPlaceholderText("예: 192.168.0.25:8765")
        self.mac = QLineEdit()
        self.mac.setPlaceholderText("선택 사항 · 예: AA-BB-CC-DD-EE-FF")
        if info is not None:
            self.alias.setText(info.alias)
            self.address.setText(f"{info.host}:{info.port}")
            self.mac.setText(info.mac)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("패널 별명 *", self.alias)
        form.addRow("IP:포트 *", self.address)
        form.addRow("MAC 주소", self.mac)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "저장" if info else "패널 생성"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.alias.text().strip() or not self.address.text().strip():
            QMessageBox.warning(self, "입력 필요", "별명과 IP:포트는 필수입니다.")
            return
        if ":" not in self.address.text():
            QMessageBox.warning(self, "입력 확인", "IP:포트 형식으로 입력하세요.")
            return
        self.accept()

    def worker_info(self) -> WorkerInfo:
        host, port = self.address.text().strip().rsplit(":", 1)
        mac = self.mac.text().strip().replace(":", "-").upper()
        return WorkerInfo(self.alias.text().strip(), host, port, mac)


class WorkerCard(QFrame):
    remove_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    power_requested = pyqtSignal(object)
    job_requested = pyqtSignal(object)

    def __init__(self, info: WorkerInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.info = info
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        title_box = QVBoxLayout()
        self.alias_label = QLabel(info.alias)
        self.connection_label = QLabel("● 연결 테스트 대기")
        self._set_connection_color("gray")
        title_box.addWidget(self.alias_label)
        title_box.addWidget(self.connection_label)
        remove = QPushButton("×")
        remove.setToolTip("패널 삭제")
        remove.clicked.connect(lambda: self.remove_requested.emit(self))
        edit = QPushButton("수정")
        edit.setToolTip("워커 정보 수정")
        edit.clicked.connect(lambda: self.edit_requested.emit(self))
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(edit, alignment=Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(remove, alignment=Qt.AlignmentFlag.AlignTop)
        root.addWidget(header)

        details = QGroupBox("기본 정보")
        details_layout = QVBoxLayout(details)
        device_row, self.device_label = self._meta("장치 이름", "연결 테스트 후 표시")
        user_row, self.user_label = self._meta("기본 사용자", "연결 테스트 후 표시")
        details_layout.addWidget(device_row)
        details_layout.addWidget(user_row)
        address_row, self.address_label = self._meta("주소", f"{info.host}:{info.port}")
        details_layout.addWidget(address_row)
        root.addWidget(details)

        resources = QGroupBox("실시간 리소스")
        resources_layout = QGridLayout(resources)
        self._add_metric(resources_layout, 0, "CPU", "-- %")
        self._add_metric(resources_layout, 1, "메모리", "-- %")
        self._add_metric(resources_layout, 2, "디스크", "-- %")
        self._add_metric(resources_layout, 3, "GPU", "-- %")
        root.addWidget(resources)

        state_row = QHBoxLayout()
        state_row.addWidget(QLabel("작업 상태"))
        state = QLabel("대기 중")
        state_row.addStretch()
        state_row.addWidget(state)
        root.addLayout(state_row)

        actions = QHBoxLayout()
        power = QPushButton("⏻ 전원")
        job = QPushButton("▣ 작업 전송")
        for button in (power, job):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        power.clicked.connect(lambda: self.power_requested.emit(self))
        job.clicked.connect(lambda: self.job_requested.emit(self))
        actions.addWidget(power)
        actions.addWidget(job)
        root.addLayout(actions)

    @staticmethod
    def _meta(label: str, value: str) -> tuple[QWidget, QLabel]:
        row = QWidget()
        layout = QHBoxLayout(row)
        key = QLabel(label)
        val = QLabel(value)
        layout.addWidget(key)
        layout.addStretch()
        layout.addWidget(val)
        return row, val

    def update_connection(self, state: str) -> None:
        if state == "connected":
            self.connection_label.setText("● 연결됨 · probe 전송")
            self._set_connection_color("green")
        elif state == "connecting":
            self.connection_label.setText("● 연결 테스트 중...")
            self._set_connection_color("green")
        else:
            self.connection_label.setText("● 연결 끊김 · 재시도 중")
            self._set_connection_color("red")

    def update_info(self, info: WorkerInfo) -> None:
        self.info = info
        self.agent_username = ""
        self.alias_label.setText(info.alias)
        self.address_label.setText(f"{info.host}:{info.port}")
        self.connection_label.setText("● 연결 테스트 대기")
        self._set_connection_color("gray")

    def update_agent_message(self, message: dict) -> None:
        message_type = message.get("type")
        if message_type not in {"probe_ack", "heartbeat"}:
            return
        self.device_label.setText(str(message.get("hostname", "알 수 없음")))
        self.agent_username = str(message.get("username", "")).strip()
        self.user_label.setText(self.agent_username or "알 수 없음")
        if message_type == "probe_ack":
            self.connection_label.setText("● 연결됨 · 초기 테스트 완료")
        else:
            self.connection_label.setText("● 연결됨 · heartbeat 수신")
        self._set_connection_color("green")

    def _set_connection_color(self, color: str) -> None:
        self.connection_label.setStyleSheet(f"color: {color};")

    @staticmethod
    def _add_metric(layout: QGridLayout, row: int, name: str, value: str) -> None:
        label = QLabel(name)
        number = QLabel(value)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        layout.addWidget(label, row, 0)
        layout.addWidget(bar, row, 1)
        layout.addWidget(number, row, 2)


class ControllerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Remote Controller")
        self.resize(1120, 760)
        self.cards: list[WorkerCard] = []
        self.connections: dict[WorkerCard, AgentConnection] = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        title_box = QVBoxLayout()
        brand = QLabel("Remote Controller")
        subtitle = QLabel("워커 데스크톱을 카드로 관리하고 상태를 모니터링합니다")
        title_box.addWidget(brand)
        title_box.addWidget(subtitle)
        add = QPushButton("＋ 워커 패널 추가")
        add.clicked.connect(self.add_worker)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(add)
        root.addWidget(header)

        section = QHBoxLayout()
        heading = QLabel("워커 데스크톱")
        self.count = QLabel("0개 연결됨")
        section.addWidget(heading)
        section.addWidget(self.count)
        section.addStretch()
        root.addLayout(section)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.canvas = QWidget()
        self.grid = QGridLayout(self.canvas)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.canvas)
        root.addWidget(scroll, 1)

        self.empty = QLabel("워커 패널을 추가하면 이곳에 표시됩니다.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid.addWidget(self.empty, 0, 0, 1, 3)
        self._load_workers()

    def add_worker(self) -> None:
        dialog = AddWorkerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        card = WorkerCard(dialog.worker_info())
        card.remove_requested.connect(self.remove_worker)
        card.edit_requested.connect(self.edit_worker)
        card.power_requested.connect(self.show_placeholder)
        card.job_requested.connect(self.show_placeholder)
        self.cards.append(card)
        self._start_connection(card)
        self._save_workers()
        self._rebuild_grid()

    def remove_worker(self, card: WorkerCard) -> None:
        if card not in self.cards:
            return
        self.cards.remove(card)
        self._stop_connection(card)
        card.deleteLater()
        self._save_workers()
        self._rebuild_grid()

    def edit_worker(self, card: WorkerCard) -> None:
        dialog = AddWorkerDialog(self, card.info)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._stop_connection(card)
        card.update_info(dialog.worker_info())
        self._start_connection(card)
        self._save_workers()

    def _load_workers(self) -> None:
        """Restore the local worker list without failing UI startup on bad data."""
        if not WORKERS_FILE.exists():
            return
        try:
            records = json.loads(WORKERS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(records, list):
            return
        for record in records:
            if not isinstance(record, dict):
                continue
            alias = str(record.get("alias", "")).strip()
            host = str(record.get("host", "")).strip()
            port = str(record.get("port", "")).strip()
            mac = str(record.get("mac", "")).strip().replace(":", "-").upper()
            if alias and host and port:
                card = WorkerCard(WorkerInfo(alias, host, port, mac))
                card.remove_requested.connect(self.remove_worker)
                card.edit_requested.connect(self.edit_worker)
                card.power_requested.connect(self.show_placeholder)
                card.job_requested.connect(self.show_placeholder)
                self.cards.append(card)
                self._start_connection(card)
        self._rebuild_grid()

    def _start_connection(self, card: WorkerCard) -> None:
        connection = AgentConnection(card.info, self)
        connection.state_changed.connect(card.update_connection)
        connection.message_received.connect(card.update_agent_message)
        self.connections[card] = connection
        connection.start()

    def _stop_connection(self, card: WorkerCard) -> None:
        connection = self.connections.pop(card, None)
        if connection is None:
            return
        connection.stop()
        connection.wait(1500)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt callback name
        for card in list(self.connections):
            self._stop_connection(card)
        event.accept()

    def _save_workers(self) -> None:
        records = [
            {
                "alias": card.info.alias,
                "host": card.info.host,
                "port": card.info.port,
                "mac": card.info.mac,
            }
            for card in self.cards
        ]
        try:
            WORKERS_FILE.write_text(
                json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            # A read-only project folder should not prevent the UI from opening.
            pass

    def _rebuild_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(None)
        if not self.cards:
            self.grid.addWidget(self.empty, 0, 0, 1, 3)
        else:
            for index, card in enumerate(self.cards):
                self.grid.addWidget(card, index // 3, index % 3)
        self.count.setText(f"{len(self.cards)}개 연결됨")

    def show_placeholder(self, card: WorkerCard) -> None:
        QMessageBox.information(
            self,
            "UI 미리보기",
            f"'{card.info.alias}' 패널의 기능 연결 위치입니다.\n실제 기능은 다음 단계에서 연결합니다.",
        )

def main() -> int:
    app = QApplication(sys.argv)
    window = ControllerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
