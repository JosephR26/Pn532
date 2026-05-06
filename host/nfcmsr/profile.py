"""Card profile data model — mirrors shared/schemas/card_profile.schema.json."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "card_profile.schema.json"


@dataclass
class NfcData:
    technology: str | None = None
    uid: str | None = None
    atqa: str | None = None
    sak: str | None = None
    ats: str | None = None
    tag_type: str | None = None
    sectors: list[dict[str, Any]] = field(default_factory=list)
    pages: list[str] = field(default_factory=list)
    ndef: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in ("technology", "uid", "atqa", "sak", "ats", "tag_type"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.sectors:
            out["sectors"] = self.sectors
        if self.pages:
            out["pages"] = self.pages
        if self.ndef:
            out["ndef"] = self.ndef
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NfcData:
        if not data:
            return cls()
        return cls(
            technology=data.get("technology"),
            uid=data.get("uid"),
            atqa=data.get("atqa"),
            sak=data.get("sak"),
            ats=data.get("ats"),
            tag_type=data.get("tag_type"),
            sectors=list(data.get("sectors", [])),
            pages=list(data.get("pages", [])),
            ndef=list(data.get("ndef", [])),
        )


@dataclass
class MagstripeData:
    coercivity: str | None = None
    track1: str | None = None
    track2: str | None = None
    track3: str | None = None
    track1_raw_hex: str | None = None
    track2_raw_hex: str | None = None
    track3_raw_hex: str | None = None
    track2_lrc_ok: bool | None = None
    read_device: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in (
            "coercivity",
            "track1",
            "track2",
            "track3",
            "track1_raw_hex",
            "track2_raw_hex",
            "track3_raw_hex",
            "track2_lrc_ok",
            "read_device",
        ):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> MagstripeData:
        if not data:
            return cls()
        return cls(
            coercivity=data.get("coercivity"),
            track1=data.get("track1"),
            track2=data.get("track2"),
            track3=data.get("track3"),
            track1_raw_hex=data.get("track1_raw_hex"),
            track2_raw_hex=data.get("track2_raw_hex"),
            track3_raw_hex=data.get("track3_raw_hex"),
            track2_lrc_ok=data.get("track2_lrc_ok"),
            read_device=data.get("read_device"),
        )


@dataclass
class Iso7816Data:
    reader_name: str | None = None
    atr: str | None = None
    atr_decoded: dict[str, Any] = field(default_factory=dict)
    applications: list[dict[str, Any]] = field(default_factory=list)
    apdu_log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.reader_name:
            out["reader_name"] = self.reader_name
        if self.atr:
            out["atr"] = self.atr
        if self.atr_decoded:
            out["atr_decoded"] = self.atr_decoded
        if self.applications:
            out["applications"] = self.applications
        if self.apdu_log:
            out["apdu_log"] = self.apdu_log
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Iso7816Data:
        if not data:
            return cls()
        return cls(
            reader_name=data.get("reader_name"),
            atr=data.get("atr"),
            atr_decoded=dict(data.get("atr_decoded", {})),
            applications=list(data.get("applications", [])),
            apdu_log=list(data.get("apdu_log", [])),
        )


@dataclass
class CardProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    captured_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str | None = None
    schema_version: str = SCHEMA_VERSION
    source: str = "host"
    label: str | None = None
    notes: str | None = None
    nfc: NfcData = field(default_factory=NfcData)
    magstripe: MagstripeData = field(default_factory=MagstripeData)
    iso7816: Iso7816Data = field(default_factory=Iso7816Data)
    emv: dict[str, Any] = field(default_factory=dict)
    attacks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "captured_at": self.captured_at,
            "source": self.source,
        }
        if self.updated_at:
            out["updated_at"] = self.updated_at
        if self.label:
            out["label"] = self.label
        if self.notes:
            out["notes"] = self.notes
        nfc = self.nfc.to_dict()
        if nfc:
            out["nfc"] = nfc
        mag = self.magstripe.to_dict()
        if mag:
            out["magstripe"] = mag
        iso = self.iso7816.to_dict()
        if iso:
            out["iso7816"] = iso
        if self.emv:
            out["emv"] = self.emv
        if self.attacks:
            out["attacks"] = self.attacks
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardProfile:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            captured_at=data.get("captured_at", _now_iso()),
            updated_at=data.get("updated_at"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            source=data.get("source", "host"),
            label=data.get("label"),
            notes=data.get("notes"),
            nfc=NfcData.from_dict(data.get("nfc")),
            magstripe=MagstripeData.from_dict(data.get("magstripe")),
            iso7816=Iso7816Data.from_dict(data.get("iso7816")),
            emv=dict(data.get("emv", {})),
            attacks=list(data.get("attacks", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = _now_iso()
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> CardProfile:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(profile: CardProfile | dict[str, Any]) -> list[str]:
    """Return a list of validation error messages. Empty list == valid."""
    import jsonschema

    data = profile.to_dict() if isinstance(profile, CardProfile) else profile
    validator = jsonschema.Draft202012Validator(load_schema())
    return [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(data)]


def diff(a: CardProfile, b: CardProfile) -> list[str]:
    """Human-readable summary of differences between two profiles."""
    changes: list[str] = []

    def cmp(label: str, av: Any, bv: Any) -> None:
        if av != bv:
            changes.append(f"{label}: {av!r} -> {bv!r}")

    cmp("nfc.uid", a.nfc.uid, b.nfc.uid)
    cmp("nfc.atqa", a.nfc.atqa, b.nfc.atqa)
    cmp("nfc.sak", a.nfc.sak, b.nfc.sak)
    cmp("nfc.tag_type", a.nfc.tag_type, b.nfc.tag_type)

    a_sectors = {s["index"]: s for s in a.nfc.sectors}
    b_sectors = {s["index"]: s for s in b.nfc.sectors}
    for idx in sorted(set(a_sectors) | set(b_sectors)):
        av = a_sectors.get(idx)
        bv = b_sectors.get(idx)
        if av != bv:
            changes.append(f"nfc.sector[{idx}]: changed")

    cmp("magstripe.track1", a.magstripe.track1, b.magstripe.track1)
    cmp("magstripe.track2", a.magstripe.track2, b.magstripe.track2)
    cmp("magstripe.track3", a.magstripe.track3, b.magstripe.track3)

    return changes
