import pytest

from nfcmsr.apdu import (
    PPSE_AID,
    PSE_AID,
    CommandAPDU,
    ResponseAPDU,
    annotate_aid,
    parse_atr,
    parse_tlv,
    read_record,
    select_aid,
)


def test_command_encode_no_data_no_le() -> None:
    cmd = CommandAPDU(cla=0x00, ins=0xA4, p1=0x04, p2=0x00)
    assert cmd.encode() == bytes([0x00, 0xA4, 0x04, 0x00])


def test_command_encode_with_data_and_le() -> None:
    cmd = CommandAPDU(cla=0x00, ins=0xA4, p1=0x04, p2=0x00, data=b"\x01\x02", le=0x00)
    assert cmd.encode() == bytes([0x00, 0xA4, 0x04, 0x00, 0x02, 0x01, 0x02, 0x00])


def test_from_bytes_case1_header_only() -> None:
    cmd = CommandAPDU.from_bytes(bytes([0x00, 0xCA, 0x9F, 0x17]))
    assert (cmd.cla, cmd.ins, cmd.p1, cmd.p2) == (0x00, 0xCA, 0x9F, 0x17)
    assert cmd.data == b""
    assert cmd.le is None


def test_from_bytes_case2_le_only() -> None:
    cmd = CommandAPDU.from_bytes(bytes([0x00, 0xB0, 0x00, 0x00, 0x10]))
    assert cmd.le == 0x10
    assert cmd.data == b""


def test_from_bytes_case3_data_no_le() -> None:
    raw = bytes([0x00, 0xA4, 0x04, 0x00, 0x02, 0xAA, 0xBB])
    cmd = CommandAPDU.from_bytes(raw)
    assert cmd.data == b"\xaa\xbb"
    assert cmd.le is None


def test_from_bytes_case4_data_and_le() -> None:
    raw = bytes([0x00, 0xA4, 0x04, 0x00, 0x02, 0xAA, 0xBB, 0x00])
    cmd = CommandAPDU.from_bytes(raw)
    assert cmd.data == b"\xaa\xbb"
    assert cmd.le == 0x00


def test_from_bytes_round_trip_select_aid() -> None:
    original = select_aid(PSE_AID)
    encoded = original.encode()
    parsed = CommandAPDU.from_bytes(encoded)
    assert parsed.encode() == encoded


def test_from_bytes_rejects_short_header() -> None:
    with pytest.raises(ValueError):
        CommandAPDU.from_bytes(bytes([0x00, 0xA4, 0x04]))


def test_from_bytes_rejects_truncated_data() -> None:
    raw = bytes([0x00, 0xA4, 0x04, 0x00, 0x05, 0xAA, 0xBB])
    with pytest.raises(ValueError):
        CommandAPDU.from_bytes(raw)


def test_from_bytes_rejects_trailing_garbage() -> None:
    raw = bytes([0x00, 0xA4, 0x04, 0x00, 0x02, 0xAA, 0xBB, 0x00, 0x00])
    with pytest.raises(ValueError):
        CommandAPDU.from_bytes(raw)


def test_select_aid_for_ppse() -> None:
    cmd = select_aid(PPSE_AID)
    encoded = cmd.encode()
    assert encoded[:4] == bytes([0x00, 0xA4, 0x04, 0x00])
    assert encoded[4] == len(bytes.fromhex(PPSE_AID))
    assert encoded[5 : 5 + encoded[4]] == bytes.fromhex(PPSE_AID)
    assert encoded[-1] == 0x00


def test_select_aid_rejects_empty() -> None:
    with pytest.raises(ValueError):
        select_aid("")


def test_read_record_p2() -> None:
    # SFI=1, record=2 → P2 = (1<<3)|0x04 = 0x0c
    cmd = read_record(record_number=2, sfi=1)
    assert cmd.p1 == 2
    assert cmd.p2 == 0x0C


def test_read_record_validates_sfi() -> None:
    with pytest.raises(ValueError):
        read_record(record_number=1, sfi=32)


def test_response_parse_ok() -> None:
    resp = ResponseAPDU.parse(bytes.fromhex("6f1a90 00".replace(" ", "")))
    assert resp.ok
    assert resp.data == bytes.fromhex("6f1a")
    assert resp.sw == 0x9000


def test_response_parse_61_xx() -> None:
    resp = ResponseAPDU.parse(bytes.fromhex("6112"))
    assert resp.has_more
    assert resp.sw1 == 0x61
    assert resp.sw2 == 0x12


def test_response_parse_too_short() -> None:
    with pytest.raises(ValueError):
        ResponseAPDU.parse(b"\x90")


def test_annotate_known_aids() -> None:
    assert annotate_aid("a0000000031010") == "Visa Credit/Debit"
    assert annotate_aid(PSE_AID).startswith("EMV PSE")
    assert annotate_aid(PPSE_AID).startswith("EMV PPSE")
    assert annotate_aid("ffffffffffff") == "unknown"


def test_annotate_extended_aid() -> None:
    label = annotate_aid("a0000000031010aa")
    assert "Visa" in label and "extended" in label


def test_parse_atr_minimal_t0() -> None:
    info = parse_atr("3b 00")
    assert info.convention == "direct"
    assert info.protocols == ["T=0"]
    assert info.historical_bytes == b""


def test_parse_atr_with_t1_protocol() -> None:
    # Common ATR for a T=1 javacard: 3B F8 13 00 00 81 31 FE 45 ...
    raw = bytes.fromhex("3bf81300008131fe454a434f5076323431b7")
    info = parse_atr(raw)
    assert info.convention == "direct"
    assert "T=1" in info.protocols
    assert info.historical_bytes  # non-empty


def test_parse_atr_rejects_bad_ts() -> None:
    with pytest.raises(ValueError):
        parse_atr("00 00")


def test_parse_atr_accepts_string_input() -> None:
    info = parse_atr("3B00")
    assert info.raw_hex == "3b00"


def test_parse_tlv_simple() -> None:
    # Tag 0x84 (DF Name), length 0x05, value 'a0001'
    raw = bytes.fromhex("84 05 a0 00 00 00 03".replace(" ", ""))
    items = list(parse_tlv(raw))
    assert items == [(0x84, bytes.fromhex("a000000003"))]


def test_parse_tlv_two_byte_tag() -> None:
    # Tag 0x9F02 (Amount Authorized), length 0x06, value 000000001000
    raw = bytes.fromhex("9F0206000000001000")
    items = list(parse_tlv(raw))
    assert items == [(0x9F02, bytes.fromhex("000000001000"))]


def test_parse_tlv_long_form_length() -> None:
    payload = b"\x00" * 130
    # Tag 0x70, long-form length 0x81 0x82 (130)
    raw = b"\x70\x81\x82" + payload
    items = list(parse_tlv(raw))
    assert items == [(0x70, payload)]


def test_parse_tlv_truncated_value() -> None:
    raw = bytes.fromhex("8410")  # claims 16 bytes, none provided
    with pytest.raises(ValueError):
        list(parse_tlv(raw))
