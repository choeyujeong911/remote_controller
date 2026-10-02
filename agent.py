"""Headless worker agent for the remote controller.

The first version only exposes a TCP probe and a periodic heartbeat. It has no
GUI and is intended to run as a background process on a worker desktop.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import platform
import socket
import time


LOG = logging.getLogger("remote-agent")


class WorkerAgent:
    def __init__(self, heartbeat_seconds: float = 5.0) -> None:
        self.heartbeat_seconds = heartbeat_seconds

    @staticmethod
    def _identity() -> dict[str, str]:
        return {
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "platform": platform.platform(),
        }

    async def _send(self, writer: asyncio.StreamWriter, message: dict) -> None:
        writer.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
        await writer.drain()

    async def _heartbeat_loop(self, writer: asyncio.StreamWriter) -> None:
        while not writer.is_closing():
            await asyncio.sleep(self.heartbeat_seconds)
            await self._send(
                writer,
                {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "status": "idle",
                    **self._identity(),
                },
            )

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        LOG.info("controller connected: %s", peer)
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(writer))
        try:
            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if message.get("type") == "probe":
                    await self._send(
                        writer,
                        {
                            "type": "probe_ack",
                            "timestamp": time.time(),
                            **self._identity(),
                        },
                    )
        except (ConnectionError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
            writer.close()
            await writer.wait_closed()
            LOG.info("controller disconnected: %s", peer)

    async def serve(self, host: str, port: int) -> None:
        server = await asyncio.start_server(self.handle_client, host, port)
        addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
        LOG.info("agent listening on %s", addresses)
        async with server:
            await server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless remote worker agent")
    parser.add_argument("--host", default="0.0.0.0", help="listen address")
    parser.add_argument("--port", type=int, default=8765, help="listen port")
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=5.0,
        help="heartbeat interval (default: 5 seconds)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        asyncio.run(WorkerAgent(args.heartbeat_seconds).serve(args.host, args.port))
    except KeyboardInterrupt:
        LOG.info("agent stopped")


if __name__ == "__main__":
    main()
