# CLAUDE.md

Project-level context for Claude Code sessions working on this repository.

## What this project is

A hardware-based NFC/RFID + magstripe pentesting toolkit. Two halves:

1. **Handheld field unit** — ESP32 DevKitC-32 (30-pin WROOM-32) + PN532, SSD1306 0.96" 128×64 I²C OLED, 5-way nav switch, external RESET + BOOT buttons. Standalone menu-driven; also speaks JSON over USB serial when tethered.
2. **Laptop host** — Python CLI `nfcmsr` that drives an MSR605X USB-serial magstripe reader/writer, wraps libnfc attack tooling, and orchestrates capture/clone workflows.

Integration seam: a single `shared/schemas/card_profile.schema.json` record holds NFC, magstripe, and optional EMV data for one physical card. Both firmware and host produce/consume this JSON.

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
- **Host:** Python 3.11+, `click`, `pyserial`, `jsonschema`, `rich`, `pytest`.
- **System:** `libnfc-bin`, `libnfc-dev`, `mfoc`, `mfcuk`; `mfoc-hardnested` from source.

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
- **Host:** Type hints required on public functions. `click` for CLI, `rich` for output, `pyserial` for all serial I/O. Tests use mocks for hardware — no test should require a physical card or MSR605X.
- No comments unless the WHY is non-obvious. Self-documenting names over commentary.

## What's in scope / out of scope

**In scope:**
- MIFARE Classic / Ultralight / DESFire read and (where possible) write.
- ISO 14443-A/B and FeliCa reader-mode operations.
- MSR605X track 1/2/3 read/write (hi-co + lo-co).
- Hybrid card cloning (NFC + magstripe) from a single profile.
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
