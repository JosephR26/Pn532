# PN532 + MSR605X Pentesting Toolkit

A two-part NFC/RFID + magstripe pentesting rig.

- **Handheld field unit:** ESP32 DevKitC-32 + PN532 + SSD1306 0.96" OLED + 5-way nav switch. Standalone menu-driven scan/dump/clone, plus tethered JSON-over-USB mode for desk work.
- **Laptop host:** Python CLI (`nfcmsr`) that drives an MSR605X magstripe reader/writer over USB serial, wraps `libnfc` / `mfcuk` / `mfoc` / `mfoc-hardnested`, and speaks to the tethered handheld.

Both halves read and write a shared `card_profile.json` record, so hybrid NFC+magstripe cards can be captured, diffed, and cloned as a single unit.

## Repo layout

```
firmware/   ESP32 + PN532 PlatformIO project
host/       Python 3.11+ CLI (nfcmsr)
shared/     card-profile JSON schema + examples
docs/       hardware wiring, workflows, legal notes
```

## Quick start

### Firmware

```
cd firmware
pio run                 # compile for esp32dev
pio run -t upload       # flash via USB
pio device monitor      # serial monitor at 115200 baud
```

### Host CLI

```
cd host
python -m venv .venv && source .venv/bin/activate
pip install -e .
nfcmsr --help
```

### System dependencies (Linux)

```
sudo apt install libnfc-bin libnfc-dev mfoc mfcuk
# mfoc-hardnested: build from https://github.com/nfc-tools/mfoc-hardnested
```

## Status

v1 scaffold. See the project plan and `docs/workflows.md` for milestones.

## Legal

This repository is for authorised security testing and research only. See `docs/legal.md`. Using this hardware to clone or relay credentials without explicit written authorisation may constitute an offence under the UK Computer Misuse Act 1990 and Fraud Act 2006, and equivalent legislation elsewhere.
