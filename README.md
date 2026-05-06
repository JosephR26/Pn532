# PN532 + MSR605X + Smartcard Pentesting Toolkit

A three-leg NFC/RFID + magstripe + contact-smartcard pentesting rig.

- **Handheld field unit:** ESP32 DevKitC-32 + PN532 + SSD1306 0.96" OLED + 5-way nav switch. Standalone menu-driven scan/dump/clone, plus tethered JSON-over-USB mode for desk work. Covers 13.56 MHz contactless.
- **Laptop magstripe leg:** MSR605X USB reader/writer for ISO 7811 Tracks 1/2/3 (hi-co + lo-co).
- **Laptop contact smartcard leg:** USB CCID reader (e.g. STW-027) over PC/SC for ISO 7816: contact EMV, PIV, OpenPGP, GIDS, JavaCard, SIM (with adapter), and the contact side of dual-interface cards.

The Python CLI (`nfcmsr`) ties all three together. A shared `card_profile.json` schema holds NFC + magstripe + contact data for one physical card, so hybrid cards can be captured, diffed, and cloned as a single unit.

Primary target host OS is **Windows 11** — see `docs/windows.md`. Linux works equally well.

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
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -e ".[smartcard]"   # smartcard extra pulls in pyscard
nfcmsr --help
```

`pyscard` is optional — install only if you want the contact smartcard leg. The MSR605X and PN532 paths work without it.

### System dependencies (Linux)

```
sudo apt install libnfc-bin libnfc-dev mfoc mfcuk pcscd pcsc-lite swig
# mfoc-hardnested: build from https://github.com/nfc-tools/mfoc-hardnested
```

### System dependencies (Windows 11)

- **ESP32:** install the WCH CH341SER driver (the DevKitC variant in this project uses a CH340 USB-to-UART bridge). Device shows up as `COMx`.
- **MSR605X:** the typical clone is USB-CDC; Windows usually picks it up automatically as `COMy`. If not, install the vendor driver.
- **CCID smartcard reader:** Windows includes WinSCard; no driver install needed for standards-compliant readers. Verify with `Get-Service SCardSvr`.
- **libnfc / mfcuk / mfoc / mfoc-hardnested:** install inside WSL2 and forward USB devices with `usbipd-win`.

See `docs/windows.md` for full setup steps.

## Status

v1 scaffold. See the project plan and `docs/workflows.md` for milestones.

## Legal

This repository is for authorised security testing and research only. See `docs/legal.md`. Using this hardware to clone or relay credentials without explicit written authorisation may constitute an offence under the UK Computer Misuse Act 1990 and Fraud Act 2006, and equivalent legislation elsewhere.
