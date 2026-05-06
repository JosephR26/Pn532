# Workflows

End-to-end operational workflows the toolkit supports. Each assumes authorised testing — see `legal.md`.

## 1. Quick card fingerprint (v1)

Tethered handheld. Good first check on any unknown card.

1. Power the handheld over USB.
2. Open host CLI: `nfcmsr nfc read --save profiles/unknown.json`.
3. Present card to the PN532 antenna.
4. CLI prints UID / ATQA / SAK / inferred tag type and saves a profile.
5. `nfcmsr profile show profiles/unknown.json` for a pretty view.

Standalone variant: on the handheld menu, pick **Scan card**. UID and tag type render on the OLED; the profile is persisted to NVS and can be pulled later with `nfcmsr nfc dump-nvs`.

## 2. Magstripe capture (v1)

1. Plug MSR605X into the laptop.
2. `nfcmsr msr read --port COM6 --into profiles/unknown.json` (Windows) or `--port /dev/ttyACM0` (Linux). Use `--save` for a fresh profile.
3. Swipe the card.
4. CLI parses Tracks 1/2/3, verifies Track 2 LRC, and stores the result.

## 3. Contact smartcard snapshot (v1)

1. Plug the CCID reader (e.g. STW-027) into the laptop and insert a card.
2. List readers: `nfcmsr smartcard readers`.
3. Capture: `nfcmsr smartcard info --reader 0 --into profiles/unknown.json`.
4. CLI records ATR + ISO 7816-3 protocol(s) + a sweep of well-known AIDs (PSE, PPSE, Visa, Mastercard, PIV, OpenPGP, etc.) and notes which ones the card responds to.

Raw APDU when you want to drive the card by hand:

```
nfcmsr smartcard apdu 00A4040007A0000000031010
#                     │  │  │  │  │  │
#                     │  │  │  │  │  └─ AID (Visa)
#                     │  │  │  │  └──── Lc
#                     │  │  │  └─────── P2
#                     │  │  └────────── P1 (SELECT by name)
#                     │  └───────────── INS (SELECT)
#                     └──────────────── CLA
```

## 5. MIFARE Classic key recovery (v2)

Fastest path when at least one key is default:

```
nfcmsr attack mfoc --profile profiles/target.json        # nested attack
```

When no default keys are present:

```
nfcmsr attack mfcuk --profile profiles/target.json       # darkside, slow
nfcmsr attack hardnested --profile profiles/target.json  # statistical, offline
```

Recovered keys are merged into the profile's `nfc.sectors[].key_a/key_b` with `key_source` set appropriately. Full sector dumps are pulled in the same run.

## 6. Hybrid clone — NFC + magstripe + contact (v2)

For cards that carry correlated data across media (older hotel keys, some legacy access badges, dual-interface EMV).

```
# 1. Capture source — all three legs
nfcmsr nfc read         --save profiles/src.json
nfcmsr msr read         --into profiles/src.json
nfcmsr smartcard info   --into profiles/src.json
nfcmsr attack mfoc --profile profiles/src.json   # if needed for full NFC dump

# 2. Write target
nfcmsr clone hybrid --from profiles/src.json
#  ├── writes NFC: prompts for magic card (Gen1a/Gen2/CUID) on the handheld
#  └── writes magstripe: prompts for blank on the MSR605X
#  (contact-EMV write is out of scope — chip personalisation requires issuer keys)
```

## 7. Before/after audit (v2)

```
nfcmsr nfc read --save profiles/before.json
# ... issuer updates card / user re-enrols ...
nfcmsr nfc read --save profiles/after.json
nfcmsr profile diff profiles/before.json profiles/after.json
```

Highlights changed sectors, UID immutability violations, and key-source regressions.

## 8. EMV read — contact or contactless (v2, authorisation-gated)

```
# contactless via PN532
nfcmsr emv read --interface contactless --i-have-written-authorization \
                --profile profiles/payment-test.json

# contact via CCID smartcard reader
nfcmsr emv read --interface contact --reader 0 --i-have-written-authorization \
                --profile profiles/payment-test.json
```

Pulls PPSE (contactless) or PSE (contact), enumerates AIDs, selects the preferred application, issues GPO, reads the SFI records, extracts track-equivalent data. PAN is masked in the persisted profile unless `--store-pan` is also supplied (refused without authorisation flag). Reading both interfaces and diffing them is a useful test for dual-interface card consistency.

## 9. NFC relay over Wi-Fi (v3)

Two handhelds — one near the genuine card (target), one near the reader (initiator). Relay ISO 14443-4 APDUs over TCP, with the PN532's WTX injection keeping strict readers happy.

```
# Reader-side handheld (initiator)
handheld-menu → Relay → Initiator → enter peer IP

# Card-side handheld (target)
handheld-menu → Relay → Target → await connection
```

Relay has inherent timing constraints; lossy Wi-Fi will cause failures on strict readers.
