"""MSR605X USB-serial driver.

Protocol reference: MagTek MSR605X ESC command set. The device enumerates as
USB CDC-ACM on Linux (typically /dev/ttyACM0 or /dev/ttyUSB0). Commands are
ESC-prefixed byte sequences; responses use ESC/FS framing with a final
status byte (0x30 = success).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import serial

ESC = 0x1B
FS = 0x1C
STATUS_OK = 0x30
STATUS_ERROR = 0x31
STATUS_WRITE_ERROR = 0x32

DEFAULT_BAUD = 9600
DEFAULT_TIMEOUT = 3.0

# Track 2 alphabet — 4 data bits per character, 0x30 offset (ASCII '0' = 0).
TRACK2_ALPHABET = "0123456789:;<=>?"


@dataclass
class TrackData:
    track1: str | None = None
    track2: str | None = None
    track3: str | None = None


def build_reset() -> bytes:
    return bytes([ESC, ord("a")])


def build_comm_test() -> bytes:
    return bytes([ESC, ord("e")])


def build_firmware_query() -> bytes:
    return bytes([ESC, ord("v")])


def build_model_query() -> bytes:
    return bytes([ESC, ord("t")])


def build_read_iso() -> bytes:
    return bytes([ESC, ord("r")])


def build_set_hi_co() -> bytes:
    return bytes([ESC, ord("x")])


def build_set_lo_co() -> bytes:
    return bytes([ESC, ord("y")])


def build_write_iso(tracks: TrackData) -> bytes:
    """Encode a write-ISO command frame.

    Frame layout (MagTek ESC/FS envelope):
        ESC 'w' ESC 's' ESC 0x01 <track1> ESC 0x02 <track2> ESC 0x03 <track3> '?' FS
    Absent tracks are emitted as empty payloads so the device leaves them unchanged.
    """
    out = bytearray([ESC, ord("w"), ESC, ord("s")])
    out += bytes([ESC, 0x01])
    if tracks.track1:
        out += tracks.track1.encode("ascii")
    out += bytes([ESC, 0x02])
    if tracks.track2:
        out += tracks.track2.encode("ascii")
    out += bytes([ESC, 0x03])
    if tracks.track3:
        out += tracks.track3.encode("ascii")
    out += b"?"
    out += bytes([FS])
    return bytes(out)


def parse_read_iso_response(buf: bytes) -> tuple[TrackData, int]:
    """Parse a read-ISO response buffer, return (tracks, status_byte).

    Expected layout:
        ESC 's' ESC 0x01 <t1> ESC 0x02 <t2> ESC 0x03 <t3> '?' FS ESC <status>
    Track payloads include their own start/end sentinels (e.g. ';1234=?'), so
    tracks 1 and 2 are delimited by the next ESC-marker; track 3 terminates at
    the frame-level '?' FS pair.
    """
    if not buf.startswith(bytes([ESC, ord("s")])):
        raise ValueError("missing ESC 's' prefix")

    tracks = TrackData()
    i = 2

    for track_id, attr in ((0x01, "track1"), (0x02, "track2"), (0x03, "track3")):
        if i + 1 >= len(buf) or buf[i] != ESC or buf[i + 1] != track_id:
            raise ValueError(f"missing ESC 0x{track_id:02x} marker at offset {i}")
        i += 2
        start = i
        if track_id != 0x03:
            while i < len(buf) and buf[i] != ESC:
                i += 1
        else:
            while i + 1 < len(buf) and not (buf[i] == ord("?") and buf[i + 1] == FS):
                i += 1
        value = buf[start:i].decode("ascii", errors="replace")
        if value:
            setattr(tracks, attr, value)

    if i + 1 < len(buf) and buf[i] == ord("?") and buf[i + 1] == FS:
        i += 2
    if i + 1 < len(buf) and buf[i] == ESC:
        return tracks, buf[i + 1]

    return tracks, STATUS_ERROR


def track2_lrc(data: str) -> int:
    """Compute the ISO 7811 Track 2 4-bit LRC across the given character sequence.

    Track 2 is 5-bit encoding: 4 data bits + 1 odd parity bit. The LRC is a
    trailing character whose 4 data bits equal the XOR of all preceding data
    nibbles (start sentinel through end sentinel, LRC itself excluded).

    `data` is the ASCII-decoded track content (e.g. ';1234=12?'). This function
    returns the expected LRC nibble (0..15).
    """
    acc = 0
    for ch in data:
        idx = TRACK2_ALPHABET.find(ch)
        if idx < 0:
            raise ValueError(f"character {ch!r} is not in the Track 2 alphabet")
        acc ^= idx
    return acc


class MSR605X:
    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        self._ser = serial.Serial(self._port, self._baud, timeout=self._timeout)
        self.reset()

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def _write(self, frame: bytes) -> None:
        assert self._ser is not None
        self._ser.write(frame)
        self._ser.flush()

    def _read_until_status(self) -> bytes:
        """Read until we see an ESC <status> tail. Returns the whole frame."""
        assert self._ser is not None
        buf = bytearray()
        saw_fs = False
        while True:
            chunk = self._ser.read(1)
            if not chunk:
                raise TimeoutError("MSR605X read timed out")
            buf.extend(chunk)
            if buf and buf[-1] == FS:
                saw_fs = True
                continue
            if saw_fs and len(buf) >= 2 and buf[-2] == ESC:
                return bytes(buf)

    def reset(self) -> None:
        self._write(build_reset())

    def ping(self) -> bool:
        self._write(build_comm_test())
        assert self._ser is not None
        # Comm test reply: ESC 'y'
        reply = self._ser.read(2)
        return reply == bytes([ESC, ord("y")])

    def firmware_version(self) -> str:
        self._write(build_firmware_query())
        assert self._ser is not None
        reply = self._ser.read(32)
        return reply.decode("ascii", errors="replace").strip()

    def set_coercivity(self, coercivity: str) -> None:
        if coercivity not in ("hi", "lo"):
            raise ValueError(f"coercivity must be 'hi' or 'lo', got {coercivity!r}")
        self._write(build_set_hi_co() if coercivity == "hi" else build_set_lo_co())
        assert self._ser is not None
        self._ser.read(2)  # ESC 0 / ESC A

    def read_iso(self) -> tuple[TrackData, int]:
        self._write(build_read_iso())
        buf = self._read_until_status()
        return parse_read_iso_response(buf)

    def write_iso(self, tracks: TrackData) -> int:
        self._write(build_write_iso(tracks))
        assert self._ser is not None
        reply = self._ser.read(4)
        if len(reply) >= 4 and reply[0] == ESC and reply[1] == ord("s") and reply[2] == ESC:
            return reply[3]
        return STATUS_ERROR


@contextmanager
def msr_device(port: str, baud: int = DEFAULT_BAUD, timeout: float = DEFAULT_TIMEOUT) -> Iterator[MSR605X]:
    device = MSR605X(port, baud=baud, timeout=timeout)
    device.open()
    try:
        yield device
    finally:
        device.close()
