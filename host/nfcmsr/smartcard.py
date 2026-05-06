"""PC/SC CCID smart-card reader wrapper. Lazy-imports `pyscard` so the rest of
the CLI works without `pyscard` / `pcscd` installed.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from .apdu import (
    KNOWN_AIDS,
    PPSE_AID,
    PSE_AID,
    AtrInfo,
    CommandAPDU,
    ResponseAPDU,
    annotate_aid,
    parse_atr,
    parse_tlv,
    select_aid,
)


class SmartcardError(RuntimeError):
    pass


@dataclass(frozen=True)
class _PyScardAPI:
    readers: Any
    no_card_exc: type[Exception]
    conn_exc: type[Exception]


def _pcsc_service_hint() -> str:
    if sys.platform.startswith("linux"):
        return (
            "On Linux, ensure pcscd is running: "
            "`sudo apt install pcscd pcsc-lite && sudo systemctl start pcscd`."
        )
    if sys.platform == "win32":
        return (
            "On Windows, the built-in Smart Card service (`SCardSvr`) is normally on by default. "
            "Verify with `Get-Service SCardSvr` in PowerShell."
        )
    if sys.platform == "darwin":
        return "On macOS, the system PC/SC daemon is started on demand; no extra setup is required."
    return "Ensure your platform's PC/SC service is running."


def _import_pyscard() -> _PyScardAPI:
    try:
        from smartcard.System import readers  # type: ignore[import-not-found]
        from smartcard.Exceptions import (  # type: ignore[import-not-found]
            CardConnectionException,
            NoCardException,
        )
    except ImportError as exc:
        raise SmartcardError(
            "pyscard is not installed. Install with `pip install nfcmsr[smartcard]`. "
            + _pcsc_service_hint()
        ) from exc
    return _PyScardAPI(
        readers=readers,
        no_card_exc=NoCardException,
        conn_exc=CardConnectionException,
    )


@dataclass
class ApduRecord:
    command_hex: str
    response_hex: str
    sw1: int
    sw2: int
    annotation: str | None = None

    def to_dict(self) -> dict[str, str]:
        out: dict[str, str] = {
            "command_hex": self.command_hex,
            "response_hex": self.response_hex,
            "sw1": f"{self.sw1:02x}",
            "sw2": f"{self.sw2:02x}",
        }
        if self.annotation:
            out["annotation"] = self.annotation
        return out


@dataclass
class CardSnapshot:
    reader_name: str
    atr: AtrInfo
    applications: list[dict[str, str]] = field(default_factory=list)
    apdu_log: list[ApduRecord] = field(default_factory=list)

    def to_iso7816_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "reader_name": self.reader_name,
            "atr": self.atr.raw_hex,
            "atr_decoded": {
                "convention": self.atr.convention,
                "ts": f"{self.atr.ts:02x}",
                "t0": f"{self.atr.t0:02x}",
                "historical_bytes_hex": self.atr.historical_bytes.hex(),
                "protocols": self.atr.protocols,
            },
        }
        if self.applications:
            out["applications"] = self.applications
        if self.apdu_log:
            out["apdu_log"] = [r.to_dict() for r in self.apdu_log]
        return out


class CCIDReader:
    def __init__(self, reader_index: int = 0) -> None:
        self._reader_index = reader_index
        self._sc = _import_pyscard()
        self._connection = None
        self._reader = None

    def list_readers(self) -> list[str]:
        return [str(r) for r in self._sc.readers()]

    def open(self) -> str:
        all_readers = self._sc.readers()
        if not all_readers:
            raise SmartcardError(
                "no PC/SC readers found. " + _pcsc_service_hint()
            )
        if self._reader_index >= len(all_readers):
            raise SmartcardError(
                f"reader index {self._reader_index} out of range (have {len(all_readers)})"
            )
        self._reader = all_readers[self._reader_index]
        self._connection = self._reader.createConnection()
        try:
            self._connection.connect()
        except self._sc.no_card_exc as exc:
            raise SmartcardError("no card present in reader") from exc
        except self._sc.conn_exc as exc:
            raise SmartcardError(f"connection failed: {exc}") from exc
        return str(self._reader)

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception:
                pass
            self._connection = None

    def get_atr(self) -> AtrInfo:
        if self._connection is None:
            raise SmartcardError("not connected")
        raw = bytes(self._connection.getATR())
        return parse_atr(raw)

    def transmit(self, command: CommandAPDU) -> ResponseAPDU:
        if self._connection is None:
            raise SmartcardError("not connected")
        cmd_bytes = command.encode()
        data, sw1, sw2 = self._connection.transmit(list(cmd_bytes))
        return ResponseAPDU(data=bytes(data), sw1=sw1, sw2=sw2)

    def select(self, aid_hex: str) -> ResponseAPDU:
        return self.transmit(select_aid(aid_hex))


@contextmanager
def ccid_reader(reader_index: int = 0) -> Iterator[CCIDReader]:
    reader = CCIDReader(reader_index=reader_index)
    reader.open()
    try:
        yield reader
    finally:
        reader.close()


def snapshot_card(reader: CCIDReader, *, probe_emv: bool = True) -> CardSnapshot:
    """Capture a baseline snapshot: ATR + a small sweep of well-known AIDs.

    Probes contact PSE first, then a list of common EMV / PIV / OpenPGP AIDs.
    Records every command in the APDU log so the resulting profile is
    reproducible. Stops short of full EMV transaction processing — that
    belongs in a dedicated authorisation-gated EMV flow.
    """
    snap = CardSnapshot(reader_name="?", atr=reader.get_atr())

    aid_candidates: list[str] = []
    if probe_emv:
        aid_candidates.extend([PSE_AID, PPSE_AID])
    aid_candidates.extend(
        a for a in KNOWN_AIDS if a not in (PSE_AID, PPSE_AID)
    )

    for aid in aid_candidates:
        cmd = select_aid(aid)
        try:
            resp = reader.transmit(cmd)
        except SmartcardError:
            continue
        snap.apdu_log.append(
            ApduRecord(
                command_hex=cmd.encode().hex(),
                response_hex=resp.data.hex(),
                sw1=resp.sw1,
                sw2=resp.sw2,
                annotation=f"SELECT {annotate_aid(aid)}",
            )
        )
        if resp.ok or resp.has_more:
            snap.applications.append(
                {
                    "aid": aid,
                    "label": annotate_aid(aid),
                    "fci_hex": resp.data.hex(),
                }
            )
    return snap


__all__ = [
    "CCIDReader",
    "CardSnapshot",
    "ApduRecord",
    "SmartcardError",
    "ccid_reader",
    "snapshot_card",
    "parse_tlv",
]
