"""Pure-Python ISO 7816 APDU encoder/decoder and ATR parser.

No external dependencies — the device-side wrapper in `smartcard.py` consumes
this module and adds the pyscard transport. Splitting the protocol logic out
makes it testable without PC/SC installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# Common AIDs we'll want to probe / annotate. Hex, no separators, lowercase.
PSE_AID = "315041592e5359532e4444463031"           # "1PAY.SYS.DDF01" — contact PSE
PPSE_AID = "325041592e5359532e4444463031"          # "2PAY.SYS.DDF01" — contactless PPSE

KNOWN_AIDS: dict[str, str] = {
    PSE_AID: "EMV PSE (contact)",
    PPSE_AID: "EMV PPSE (contactless)",
    "a0000000031010": "Visa Credit/Debit",
    "a0000000041010": "Mastercard Credit/Debit",
    "a0000000043060": "Mastercard Maestro",
    "a000000025": "American Express",
    "a0000000651010": "JCB",
    "a0000001523010": "Discover",
    "a000000308000010000100": "PIV (NIST 800-73)",
    "d2760001240102010000000000010000": "OpenPGP card v2",
    "a000000063504b43532d3135": "PKCS#15",
    "a0000000620201": "Java Card runtime ID (sample)",
    "a0000000871002": "USIM",
    "a0000000090001": "GSM SIM",
}


@dataclass
class CommandAPDU:
    cla: int
    ins: int
    p1: int
    p2: int
    data: bytes = b""
    le: int | None = None  # None = no Le; 0 = 256 bytes (short) / 65536 (extended)

    def encode(self) -> bytes:
        if not (0 <= self.cla <= 0xFF and 0 <= self.ins <= 0xFF):
            raise ValueError("cla/ins out of range")
        if not (0 <= self.p1 <= 0xFF and 0 <= self.p2 <= 0xFF):
            raise ValueError("p1/p2 out of range")
        if len(self.data) > 0xFF:
            raise ValueError("extended-length APDUs not supported by this encoder")

        out = bytearray([self.cla, self.ins, self.p1, self.p2])
        if self.data:
            out.append(len(self.data))
            out.extend(self.data)
        if self.le is not None:
            if not (0 <= self.le <= 0xFF):
                raise ValueError("le out of short-length range")
            out.append(self.le)
        return bytes(out)


@dataclass
class ResponseAPDU:
    data: bytes
    sw1: int
    sw2: int

    @property
    def sw(self) -> int:
        return (self.sw1 << 8) | self.sw2

    @property
    def ok(self) -> bool:
        return self.sw1 == 0x90 and self.sw2 == 0x00

    @property
    def has_more(self) -> bool:
        return self.sw1 == 0x61

    @classmethod
    def parse(cls, raw: bytes) -> ResponseAPDU:
        if len(raw) < 2:
            raise ValueError("response too short for sw1/sw2")
        return cls(data=bytes(raw[:-2]), sw1=raw[-2], sw2=raw[-1])


def select_aid(aid_hex: str, *, p2: int = 0x00) -> CommandAPDU:
    """Build a SELECT-by-DF-name APDU for the given AID."""
    aid = bytes.fromhex(aid_hex)
    if not aid:
        raise ValueError("AID must be non-empty")
    return CommandAPDU(cla=0x00, ins=0xA4, p1=0x04, p2=p2, data=aid, le=0x00)


def get_response(le: int) -> CommandAPDU:
    return CommandAPDU(cla=0x00, ins=0xC0, p1=0x00, p2=0x00, le=le & 0xFF)


def read_record(record_number: int, sfi: int) -> CommandAPDU:
    if not (1 <= record_number <= 0xFF):
        raise ValueError("record_number out of range")
    if not (0 <= sfi <= 0x1F):
        raise ValueError("sfi out of range (0..31)")
    p2 = (sfi << 3) | 0x04
    return CommandAPDU(cla=0x00, ins=0xB2, p1=record_number, p2=p2, le=0x00)


def annotate_aid(aid_hex: str) -> str:
    aid = aid_hex.lower()
    if aid in KNOWN_AIDS:
        return KNOWN_AIDS[aid]
    for prefix, label in KNOWN_AIDS.items():
        if aid.startswith(prefix):
            return f"{label} (extended)"
    return "unknown"


@dataclass
class AtrInfo:
    convention: str = "direct"
    ts: int = 0x3B
    t0: int = 0x00
    historical_bytes: bytes = b""
    protocols: list[str] = field(default_factory=list)
    raw_hex: str = ""


def parse_atr(raw: bytes | str) -> AtrInfo:
    """Parse an ISO 7816-3 ATR. Implements enough to extract historical bytes
    and the indicated protocol(s); does not validate TCK for T=1.
    """
    if isinstance(raw, str):
        raw = bytes.fromhex(raw.replace(" ", ""))
    if len(raw) < 2:
        raise ValueError("ATR too short")

    info = AtrInfo(raw_hex=raw.hex())

    ts = raw[0]
    if ts == 0x3B:
        info.convention = "direct"
    elif ts == 0x3F:
        info.convention = "inverse"
    else:
        raise ValueError(f"invalid TS byte 0x{ts:02x}")
    info.ts = ts

    t0 = raw[1]
    info.t0 = t0
    historical_count = t0 & 0x0F
    yi = (t0 >> 4) & 0x0F

    i = 2
    protocols_seen: list[int] = []
    while True:
        # Skip optional TAi/TBi/TCi based on Yi.
        for bit, _name in ((0x01, "TA"), (0x02, "TB"), (0x04, "TC")):
            if yi & bit:
                if i >= len(raw):
                    raise ValueError("ATR truncated in interface bytes")
                i += 1
        if yi & 0x08:
            if i >= len(raw):
                raise ValueError("ATR truncated before TDi")
            td = raw[i]
            i += 1
            protocols_seen.append(td & 0x0F)
            yi = (td >> 4) & 0x0F
            continue
        break

    if not protocols_seen:
        protocols_seen.append(0)
    info.protocols = sorted({f"T={p}" for p in protocols_seen})

    end_hist = i + historical_count
    if end_hist > len(raw):
        raise ValueError("ATR truncated in historical bytes")
    info.historical_bytes = raw[i:end_hist]
    return info


def parse_tlv(data: bytes) -> Iterable[tuple[int, bytes]]:
    """Iterate BER-TLV (tag, value) pairs. Handles 1- or 2-byte tags and 1-byte
    or long-form length fields up to 3 bytes (sufficient for EMV / ISO 7816)."""
    i = 0
    while i < len(data):
        first = data[i]
        i += 1
        if (first & 0x1F) == 0x1F:
            if i >= len(data):
                raise ValueError("TLV truncated in tag")
            tag = (first << 8) | data[i]
            i += 1
        else:
            tag = first
        if i >= len(data):
            raise ValueError("TLV truncated before length")
        length_byte = data[i]
        i += 1
        if length_byte & 0x80:
            n = length_byte & 0x7F
            if n == 0 or i + n > len(data):
                raise ValueError("TLV bad long-form length")
            length = 0
            for _ in range(n):
                length = (length << 8) | data[i]
                i += 1
        else:
            length = length_byte
        if i + length > len(data):
            raise ValueError("TLV value runs past buffer")
        yield tag, bytes(data[i : i + length])
        i += length
