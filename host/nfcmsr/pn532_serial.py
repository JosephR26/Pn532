"""Talks to the ESP32 firmware over USB serial using the line-delimited JSON protocol."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Iterator

import serial

DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 2.0


class FirmwareError(RuntimeError):
    pass


class FirmwareClient:
    """Line-delimited JSON client for the ESP32 handheld firmware."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        self._ser = serial.Serial(self._port, self._baud, timeout=self._timeout)
        # ESP32 auto-resets on DTR/RTS toggle; give it a moment to boot.
        time.sleep(1.2)
        self._drain()

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def _drain(self) -> None:
        assert self._ser is not None
        self._ser.reset_input_buffer()

    def _write_command(self, cmd: dict[str, Any]) -> None:
        assert self._ser is not None
        payload = (json.dumps(cmd, separators=(",", ":")) + "\n").encode("utf-8")
        self._ser.write(payload)
        self._ser.flush()

    def _read_line(self, overall_timeout: float | None = None) -> dict[str, Any]:
        assert self._ser is not None
        deadline = time.monotonic() + (overall_timeout if overall_timeout is not None else self._timeout)
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._ser.read(1)
            if not chunk:
                continue
            if chunk in (b"\n", b"\r"):
                if not buf:
                    continue
                try:
                    return json.loads(buf.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise FirmwareError(f"invalid JSON from firmware: {buf!r}") from exc
            else:
                buf.extend(chunk)
        raise FirmwareError("timed out waiting for firmware response")

    def ping(self) -> bool:
        self._write_command({"cmd": "ping"})
        resp = self._read_line()
        return resp.get("type") == "pong"

    def status(self) -> dict[str, Any]:
        self._write_command({"cmd": "status"})
        resp = self._read_line()
        if resp.get("type") != "status":
            raise FirmwareError(f"unexpected response: {resp!r}")
        return resp

    def scan(self, timeout_ms: int = 2000) -> dict[str, Any] | None:
        self._write_command({"cmd": "scan", "timeout_ms": timeout_ms})
        deadline_s = (timeout_ms / 1000.0) + 1.0
        resp = self._read_line(overall_timeout=deadline_s)
        if resp.get("type") == "scan_timeout":
            return None
        if resp.get("type") == "card":
            return resp.get("data", {})
        raise FirmwareError(f"unexpected response: {resp!r}")

    def last(self) -> dict[str, Any] | None:
        self._write_command({"cmd": "last"})
        resp = self._read_line()
        if resp.get("type") == "no_card":
            return None
        if resp.get("type") == "card":
            return resp.get("data", {})
        raise FirmwareError(f"unexpected response: {resp!r}")


@contextmanager
def firmware(port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT) -> Iterator[FirmwareClient]:
    client = FirmwareClient(port, baud=baud, timeout=timeout)
    client.open()
    try:
        yield client
    finally:
        client.close()


def parse_scan_line(line: str) -> dict[str, Any]:
    """Parse a single JSON line emitted by the firmware. Useful for offline testing."""
    data = json.loads(line)
    if not isinstance(data, dict):
        raise FirmwareError(f"expected JSON object, got {type(data).__name__}")
    return data
