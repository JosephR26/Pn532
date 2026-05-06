from nfcmsr.msr605x import (
    ESC,
    FS,
    STATUS_OK,
    TRACK2_ALPHABET,
    TrackData,
    build_read_iso,
    build_reset,
    build_set_hi_co,
    build_set_lo_co,
    build_write_iso,
    parse_read_iso_response,
    track2_lrc,
)


def test_reset_frame() -> None:
    assert build_reset() == bytes([ESC, ord("a")])


def test_read_iso_frame() -> None:
    assert build_read_iso() == bytes([ESC, ord("r")])


def test_coercivity_frames() -> None:
    assert build_set_hi_co() == bytes([ESC, ord("x")])
    assert build_set_lo_co() == bytes([ESC, ord("y")])


def test_write_iso_contains_all_tracks() -> None:
    frame = build_write_iso(TrackData(track1="%B123^NAME?", track2=";1234=25?", track3=None))
    assert frame.startswith(bytes([ESC, ord("w"), ESC, ord("s")]))
    assert bytes([ESC, 0x01]) + b"%B123^NAME?" in frame
    assert bytes([ESC, 0x02]) + b";1234=25?" in frame
    assert bytes([ESC, 0x03]) in frame
    assert frame.endswith(bytes([ord("?"), FS]))


def test_parse_read_iso_roundtrip() -> None:
    payload = (
        bytes([ESC, ord("s")])
        + bytes([ESC, 0x01]) + b"%B4111111111111111^DOE/JANE^25121010000?"
        + bytes([ESC, 0x02]) + b";4111111111111111=25121010000000000000?"
        + bytes([ESC, 0x03]) + b""
        + b"?"
        + bytes([FS, ESC, STATUS_OK])
    )
    tracks, status = parse_read_iso_response(payload)
    assert status == STATUS_OK
    assert tracks.track1 is not None
    assert tracks.track1.startswith("%B4111")
    assert tracks.track2 is not None
    assert tracks.track2.startswith(";4111")
    assert tracks.track3 is None


def test_parse_read_iso_error_status() -> None:
    payload = (
        bytes([ESC, ord("s")])
        + bytes([ESC, 0x01]) + b""
        + bytes([ESC, 0x02]) + b""
        + bytes([ESC, 0x03]) + b""
        + b"?"
        + bytes([FS, ESC, 0x31])
    )
    _tracks, status = parse_read_iso_response(payload)
    assert status == 0x31


def test_track2_alphabet_has_16_entries() -> None:
    assert len(TRACK2_ALPHABET) == 16


def test_track2_lrc_zero() -> None:
    assert track2_lrc("") == 0


def test_track2_lrc_symmetry() -> None:
    # Exclusive-OR of a character with itself is zero.
    assert track2_lrc(";;") == 0
    assert track2_lrc("99") == 0


def test_track2_lrc_known_value() -> None:
    # For ';1=?' → xor of (0x0B, 0x01, 0x0D, 0x0F) = 0x0B ^ 0x01 ^ 0x0D ^ 0x0F
    expected = 0x0B ^ 0x01 ^ 0x0D ^ 0x0F
    assert track2_lrc(";1=?") == expected


def test_track2_lrc_rejects_invalid_char() -> None:
    import pytest

    with pytest.raises(ValueError):
        track2_lrc("ABC")
