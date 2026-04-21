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
2. `nfcmsr msr read --into profiles/unknown.json` (merges into existing NFC profile) or `--save profiles/mag-only.json` for a fresh record.
3. Swipe the card.
4. CLI parses Tracks 1/2/3, verifies Track 2 LRC, and stores the result.

## 3. MIFARE Classic key recovery (v2)

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

## 4. Hybrid clone — NFC + magstripe (v2)

For cards that carry correlated data on both media (older hotel keys, some legacy access badges).

```
# 1. Capture source
nfcmsr nfc read  --save profiles/src.json
nfcmsr msr read  --into profiles/src.json
nfcmsr attack mfoc --profile profiles/src.json   # if needed for full NFC dump

# 2. Write target
nfcmsr clone hybrid --from profiles/src.json
#  ├── writes NFC: prompts for magic card (Gen1a/Gen2/CUID) on the handheld
#  └── writes magstripe: prompts for blank on the MSR605X
```

## 5. Before/after audit (v2)

```
nfcmsr nfc read --save profiles/before.json
# ... issuer updates card / user re-enrols ...
nfcmsr nfc read --save profiles/after.json
nfcmsr profile diff profiles/before.json profiles/after.json
```

Highlights changed sectors, UID immutability violations, and key-source regressions.

## 6. Contactless EMV read (v2, authorisation-gated)

```
nfcmsr emv read --i-have-written-authorization --profile profiles/payment-test.json
```

Pulls PPSE, enumerates AIDs, selects the preferred application, issues GPO, reads the SFI records, extracts track-equivalent data. PAN is masked in the persisted profile unless `--store-pan` is also supplied (refused without authorisation flag).

## 7. NFC relay over Wi-Fi (v3)

Two handhelds — one near the genuine card (target), one near the reader (initiator). Relay ISO 14443-4 APDUs over TCP, with the PN532's WTX injection keeping strict readers happy.

```
# Reader-side handheld (initiator)
handheld-menu → Relay → Initiator → enter peer IP

# Card-side handheld (target)
handheld-menu → Relay → Target → await connection
```

Relay has inherent timing constraints; lossy Wi-Fi will cause failures on strict readers.
