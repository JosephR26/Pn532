# firmware/

ESP32 DevKitC-32 + PN532 handheld firmware. PlatformIO + Arduino framework.

## Build

```
pio run
```

## Flash

```
pio run -t upload
```

If auto-reset fails (enclosed unit, LiPo-powered), use the external buttons:
hold **BOOT**, tap **RESET**, release **BOOT**, then `pio run -t upload`.

## Serial

```
pio device monitor   # 115200 baud
```

## Serial JSON command protocol

One command per line, JSON-encoded. Responses are also line-delimited JSON.

| Command                      | Response                                                |
|------------------------------|---------------------------------------------------------|
| `{"cmd":"ping"}`             | `{"type":"pong"}`                                       |
| `{"cmd":"status"}`           | `{"type":"status","pn532_ok":bool,"pn532_fw":uint,...}` |
| `{"cmd":"scan","timeout_ms":1000}` | `{"type":"card","data":{...card_profile...}}` or `{"type":"scan_timeout"}` |
| `{"cmd":"last"}`             | Last card as `{"type":"card","data":{...}}` or `{"type":"no_card"}` |
| `{"cmd":"nvs_count"}`        | `{"type":"nvs_count","count":N}`                        |

The host CLI (`nfcmsr`) uses this protocol over `/dev/ttyUSB*`.

## Layout

- `src/main.cpp` — setup, loop, UI state machine.
- `src/nfc.{h,cpp}` — PN532 wrapper via elechouse HSU library.
- `src/ui.{h,cpp}` — SSD1306 rendering + 5-way nav debounce and events.
- `src/profile.{h,cpp}` — in-memory card profile + JSON serialiser.
- `src/serial_proto.{h,cpp}` — line-delimited JSON command loop over USB serial.
- `src/storage.{h,cpp}` — NVS (`Preferences`) persistence of last-seen card.
- `src/pins.h` — single source of truth for all GPIO assignments.
