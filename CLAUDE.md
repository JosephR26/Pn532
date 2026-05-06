# CLAUDE.md

Project-level context for Claude Code sessions working on this repository.

## What this project is

A hardware-based NFC/RFID + magstripe + contact smartcard pentesting toolkit.

Three legs:

1. **Handheld field unit** — ESP32 DevKitC-32 (30-pin WROOM-32) + PN532, SSD1306 0.96" 128×64 I²C OLED, 5-way nav switch, external RESET + BOOT buttons. Covers 13.56 MHz NFC contactless. Standalone menu-driven; also speaks JSON over USB serial when tethered.
2. **Laptop magstripe leg** — MSR605X USB reader/writer, ISO 7811 Tracks 1/2/3, hi-co + lo-co.
3. **Laptop contact smartcard leg** — USB CCID reader (e.g. STW-027), driven via PC/SC. Covers ISO 7816 contact: contact EMV, PIV, OpenPGP, GIDS, JavaCard, SIM (with adapter), and the contact side of dual-interface cards.

The Python CLI `nfcmsr` orchestrates all three. Integration seam: a single `shared/schemas/card_profile.schema.json` record holds `nfc`, `magstripe`, `iso7816`, and optional `emv` blocks for one physical card. Both firmware and host produce/consume this JSON.

**Host OS:** Windows 11 is the primary target (per the user's setup). Linux works equally well; macOS untested. Driver/setup details for Windows live in `docs/windows.md`.

## Hardware pinout (ESP32 DevKitC-32)

| Function                    | GPIO          | Notes                                                       |
|-----------------------------|---------------|-------------------------------------------------------------|
| PN532 TX → ESP32 RX (UART2) | 16            | `HardwareSerial(2)` RX                                      |
| PN532 RX ← ESP32 TX (UART2) | 17            | `HardwareSerial(2)` TX                                      |
| PN532 IRQ                   | 4             | optional; pull-up for card-present interrupts               |
| PN532 RSTO / RSTPD_N        | 25            | soft reset                                                  |
| PN532 strapping             | I0=0, I1=0    | HSU (UART) mode                                             |
| OLED SDA                    | 21            | I²C addr 0x3C                                               |
| OLED SCL                    | 22            | I²C                                                         |
| Nav UP                      | 34            | input-only, external 10k pull-up REQUIRED                   |
| Nav DOWN                    | 35            | input-only, external 10k pull-up REQUIRED                   |
| Nav LEFT                    | 32            | internal pull-up OK                                         |
| Nav RIGHT                   | 33            | internal pull-up OK                                         |
| Nav CENTER                  | 27            | internal pull-up OK                                         |
| External RESET              | → EN pin      | to GND                                                      |
| External BOOT               | → GPIO0       | to GND; hold + tap RESET to enter flash mode                |
| Status LED                  | 2             | on-board; strap pin — drive only after boot                 |

Avoid using GPIO 0/2/5/12/15 for peripherals — they are boot-strap pins.

## Toolchain

- **Firmware:** PlatformIO, Arduino framework, `board = esp32dev`.
  Libraries: `elechouse/PN532` (HSU), `adafruit/Adafruit SSD1306` + `Adafruit GFX`, `bblanchon/ArduinoJson` (v6), `thomasfredericks/Bounce2`.
- **Host:** Python 3.11+, `click`, `pyserial`, `jsonschema`, `rich`, `pytest`. Optional extra: `pyscard` for the contact smartcard leg.
- **System (Linux):** `libnfc-bin`, `libnfc-dev`, `mfoc`, `mfcuk`, `pcscd`, `pcsc-lite`; `mfoc-hardnested` from source.
- **System (Windows 11):** Silicon Labs CP210x VCP driver for the ESP32, vendor driver for MSR605X (typically VCP — appears as a COM port), Windows built-in WinSCard service for the CCID smartcard reader. libnfc/mfcuk/mfoc require WSL2 with `usbipd-win` for USB passthrough.

## Build / test commands

```
# firmware
cd firmware && pio run                  # compile
cd firmware && pio run -t upload        # flash
cd firmware && pio device monitor       # 115200 baud

# host
cd host && pip install -e .[dev]
cd host && pytest
```

## Code conventions

- **Firmware:** Arduino `.cpp` + header pairs, avoid C++ features that bloat the binary. Use `ArduinoJson` `StaticJsonDocument` with sized buffers — no dynamic allocation in the hot path. Keep the UI non-blocking (state-machine loop, no `delay()` in `loop()`).
- **Host:** Type hints required on public functions. `click` for CLI, `rich` for output, `pyserial` for serial I/O, PC/SC via `pyscard` (lazy-imported). Tests use mocks/pure-Python for hardware — no test should require a physical card, MSR605X, or smartcard reader. Protocol logic (APDU encode/decode, ATR parse, MSR605X frame encode/parse, Track 2 LRC) lives in pure-Python modules so it stays testable in CI.
- No comments unless the WHY is non-obvious. Self-documenting names over commentary.

## What's in scope / out of scope

**In scope:**
- MIFARE Classic / Ultralight / DESFire read and (where possible) write.
- ISO 14443-A/B and FeliCa reader-mode operations.
- MSR605X track 1/2/3 read/write (hi-co + lo-co).
- Contact ISO 7816 via PC/SC: ATR capture, AID enumeration, raw APDU, contact-EMV / PIV / OpenPGP read flows.
- Hybrid card capture (NFC + magstripe + contact) into a single profile.
- Key recovery wrappers around libnfc tooling.
- Magic-card (Gen1a/Gen2/CUID) UID + block 0 write.
- NFC relay over Wi-Fi between two handhelds (v3).

**Out of scope:**
- 125 kHz LF cards (EM4100, HID Prox, AWID) — use a Proxmark3.
- Arbitrary NFC UID emulation from the PN532 itself — blocked by `byte[0] & 0x08 = 0x08` firmware constraint; use magic cards instead.
- USB-host MSR605X on the ESP32 — not feasible on DevKitC-32.
- Mobile/BLE control.

## Legal

All development and testing must be on hardware you own or have explicit written authorisation to test. See `docs/legal.md`. Do not commit captured credentials, track data, or real card dumps to this repo.
