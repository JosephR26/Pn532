import json
from pathlib import Path

import pytest

from nfcmsr.profile import CardProfile, Iso7816Data, MagstripeData, NfcData, diff, validate


def test_roundtrip_empty_profile(tmp_path: Path) -> None:
    profile = CardProfile(source="host", label="test")
    out = tmp_path / "p.json"
    profile.save(out)

    loaded = CardProfile.load(out)
    assert loaded.id == profile.id
    assert loaded.label == "test"
    assert loaded.source == "host"
    assert loaded.updated_at is not None


def test_profile_with_nfc_validates() -> None:
    profile = CardProfile(source="firmware", label="demo")
    profile.nfc = NfcData(
        technology="iso14443a",
        uid="deadbeef",
        atqa="0004",
        sak="08",
        tag_type="mifare_classic_1k",
    )
    assert validate(profile) == []


def test_profile_with_magstripe_validates() -> None:
    profile = CardProfile(source="host")
    profile.magstripe = MagstripeData(
        coercivity="hi",
        track2=";1234567890123456=25121010000000000000?",
        track2_lrc_ok=True,
        read_device="MSR605X",
    )
    assert validate(profile) == []


def test_profile_rejects_bad_uid() -> None:
    profile = CardProfile(source="firmware")
    profile.nfc = NfcData(technology="iso14443a", uid="ZZ")
    errors = validate(profile)
    assert any("uid" in e.lower() for e in errors)


def test_sample_profile_validates() -> None:
    sample_path = Path(__file__).resolve().parents[2] / "shared" / "examples" / "sample_profile.json"
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    errors = validate(data)
    assert errors == []


def test_diff_detects_uid_change() -> None:
    a = CardProfile()
    a.nfc = NfcData(uid="aabbccdd", technology="iso14443a")
    b = CardProfile()
    b.nfc = NfcData(uid="ffffffff", technology="iso14443a")

    changes = diff(a, b)
    assert any("nfc.uid" in c for c in changes)


def test_profile_with_iso7816_validates() -> None:
    profile = CardProfile(source="host")
    profile.iso7816 = Iso7816Data(
        reader_name="STW Smart Card Reader 0",
        atr="3b00",
        atr_decoded={"convention": "direct", "ts": "3b", "t0": "00", "historical_bytes_hex": "", "protocols": ["T=0"]},
        applications=[{"aid": "a0000000031010", "label": "Visa Credit/Debit"}],
        apdu_log=[{"command_hex": "00a4040007a0000000031010", "response_hex": "6f1a", "sw1": "90", "sw2": "00"}],
    )
    errors = validate(profile)
    assert errors == []


def test_iso7816_rejects_bad_atr() -> None:
    profile = CardProfile(source="host")
    profile.iso7816 = Iso7816Data(atr="not-hex!")
    errors = validate(profile)
    assert any("atr" in e.lower() for e in errors)


def test_load_schema_returns_expected_top_level() -> None:
    from nfcmsr.profile import load_schema

    schema = load_schema()
    assert schema["title"] == "CardProfile"
    assert "nfc" in schema["properties"]
    assert "magstripe" in schema["properties"]
    assert "iso7816" in schema["properties"]


def test_load_schema_missing_resource_raises_schema_load_error(monkeypatch) -> None:
    import nfcmsr.profile as profile_mod
    from nfcmsr.profile import SchemaLoadError

    monkeypatch.setattr(profile_mod, "SCHEMA_RESOURCE", "schemas/does_not_exist.json")
    with pytest.raises(SchemaLoadError, match="packaging problem"):
        profile_mod.load_schema()


def test_load_schema_corrupt_json_raises_schema_load_error(monkeypatch) -> None:
    import nfcmsr.profile as profile_mod
    from nfcmsr.profile import SchemaLoadError

    class _FakeResource:
        def read_text(self, encoding: str = "utf-8") -> str:
            return "{ this is not json"

    class _FakeFiles:
        def joinpath(self, _name: str) -> _FakeResource:
            return _FakeResource()

    monkeypatch.setattr(profile_mod, "files", lambda _pkg: _FakeFiles())
    with pytest.raises(SchemaLoadError, match="not valid JSON"):
        profile_mod.load_schema()


def test_diff_detects_sector_change() -> None:
    a = CardProfile()
    a.nfc = NfcData(sectors=[{"index": 0, "key_a": "ffffffffffff"}])
    b = CardProfile()
    b.nfc = NfcData(sectors=[{"index": 0, "key_a": "a0a1a2a3a4a5"}])

    changes = diff(a, b)
    assert any("nfc.sector[0]" in c for c in changes)
