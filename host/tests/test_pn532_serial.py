import json

import pytest

from nfcmsr.pn532_serial import FirmwareError, parse_scan_line


def test_parse_scan_line_valid() -> None:
    data = parse_scan_line('{"type":"card","data":{"nfc":{"uid":"deadbeef"}}}')
    assert data["type"] == "card"
    assert data["data"]["nfc"]["uid"] == "deadbeef"


def test_parse_scan_line_rejects_array() -> None:
    with pytest.raises(FirmwareError):
        parse_scan_line("[1, 2, 3]")


def test_parse_scan_line_rejects_bad_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_scan_line("{not json")
