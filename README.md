# pn532

Hardware-based NFC/RFID + magstripe + contact smartcard pentesting toolkit.

Active development happens on feature branches. See the
[`claude/pn532-nfc-pentesting-MVIdL`](../../tree/claude/pn532-nfc-pentesting-MVIdL)
branch and its associated pull request for the current scaffold:

- ESP32 DevKitC-32 + PN532 handheld firmware (PlatformIO).
- Python `nfcmsr` CLI driving an MSR605X magstripe reader/writer and a
  PC/SC CCID smart card reader.
- Shared `card_profile.json` schema tying NFC, magstripe, and contact
  smartcard data into a single record per physical card.

Authorised security testing only.
