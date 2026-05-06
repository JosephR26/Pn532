# Windows 11 setup

The host laptop in this project runs Windows 11. This page covers driver setup,
COM-port enumeration, PC/SC for the smartcard reader, and the WSL2 path for
libnfc-based key recovery (which has no native Windows build worth using).

## Driver matrix

| Device                          | Driver                                              | Appears as |
|---------------------------------|-----------------------------------------------------|------------|
| ESP32 DevKitC-32 (CH340)        | WCH CH341SER (this project's board)                 | `COMx`     |
| ESP32 DevKitC-32 (CP2102 alt)   | Silicon Labs CP210x VCP                             | `COMx`     |
| MSR605X (typical clone)         | USB-CDC (Windows-native) or vendor pack             | `COMy`     |
| STW-027 / generic CCID reader   | Windows WinSCard service (no driver install)        | PC/SC reader |

Find COM port assignments in **Device Manager → Ports (COM & LPT)**.

## WCH CH340 (ESP32)

The DevKitC-32 board in this project uses a CH340 USB-to-UART bridge, so the
WCH driver is the one you want. (If you later swap to a CP2102-based board,
follow the Silicon Labs instructions below.)

1. Plug in the ESP32. Device Manager will show "USB-Serial CH340" or
   "USB2.0-Serial" under "Other devices" with a yellow exclamation mark if
   the driver is missing.
2. Download the latest **CH341SER** package from WCH (`wch.cn` →
   "Downloads" → "Driver"). The same driver covers CH340 / CH341 chips.
3. Run `SETUP.EXE` and click **Install**. After the device reconnects, it
   enumerates as `COMx` (check Device Manager → Ports (COM & LPT)).
4. Test in PowerShell:
   ```
   pio device list
   nfcmsr nfc read --port COM5    # adjust to your port
   ```

### Silicon Labs CP210x (alternative DevKitC variants)

If you have a different DevKitC variant with a CP2102 chip, install the
**CP210x Universal Windows Driver** from Silicon Labs instead. Same `COMx`
enumeration and same `nfcmsr` usage.

## MSR605X

The MSR605X clones in circulation typically present as USB-CDC (virtual COM
port) and are picked up automatically by Windows as `COMy`. A small number of
models present as USB-HID and need a vendor utility — if Device Manager shows
the device under "Human Interface Devices" rather than "Ports (COM & LPT)",
that's the case. The current `nfcmsr` driver assumes the COM-port (CDC)
variant.

Check it works without our CLI first:
```
# in PowerShell — simple loopback / firmware version probe
[System.IO.Ports.SerialPort]$p = New-Object System.IO.Ports.SerialPort COM6,9600,None,8,One
$p.Open(); $p.Write([byte[]]@(0x1B, 0x76), 0, 2); Start-Sleep -Milliseconds 200; $p.ReadExisting(); $p.Close()
```
You should see firmware-version bytes echoed back. Then:
```
nfcmsr msr read --port COM6
```

## CCID smartcard reader (STW-027 etc.)

Windows ships with the **Smart Card service (`SCardSvr`)** and a generic CCID
class driver. Most off-the-shelf readers (including the white STW unit) are
class-compliant and work without any installer.

1. Plug in the reader. Verify the Smart Card service is running:
   ```
   Get-Service SCardSvr
   # Status should be Running. If not:
   Start-Service SCardSvr
   ```
2. Confirm the reader is visible to PC/SC:
   ```
   nfcmsr smartcard readers
   ```
   You should see something like `[0] Generic CCID Reader 0`.
3. Insert a card and run:
   ```
   nfcmsr smartcard info --reader 0 --save profiles\unknown.json
   ```

If `pyscard` fails to import, ensure you installed with the optional extra:
```
pip install -e ".[smartcard]"
```
On Windows, `pyscard` ships pre-built wheels for CPython 3.11+ — no swig/MSVC
toolchain required for normal installs.

## libnfc / mfcuk / mfoc / mfoc-hardnested via WSL2

These tools have no maintained Windows build. The clean path is WSL2 plus
`usbipd-win` to forward the PN532 USB device into the Linux side.

1. Install WSL2 (Ubuntu 22.04 or 24.04):
   ```
   wsl --install -d Ubuntu-24.04
   ```
2. Install `usbipd-win` from <https://github.com/dorssel/usbipd-win>.
3. Plug in the ESP32+PN532 (tethered) or, for direct libnfc access, a separate
   PN532 USB module. Bind and attach it from an elevated PowerShell:
   ```
   usbipd list
   usbipd bind --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>
   ```
4. Inside WSL2:
   ```
   sudo apt update
   sudo apt install libnfc-bin libnfc-dev mfoc mfcuk pcscd pcsc-lite swig
   nfc-list                              # confirm libnfc sees the device
   mfoc -P 500 -O dump.mfd               # nested attack
   ```
5. Move recovered keys / dumps back to Windows via the WSL filesystem mount
   (`\\wsl$\Ubuntu-24.04\home\you\`) and feed them into `nfcmsr` for
   profile merging.

There is no requirement to use the same machine for the handheld + magstripe +
smartcard work and the libnfc attack work — many users keep the field-side
work on Windows and run a separate Linux VM (or a small Pi) for libnfc tooling.

## Common pitfalls

- **COM port number changes** — Windows can renumber ports across reboots,
  especially with multiple USB-serial devices. Use Device Manager to check
  before each session, or pin the port in the device's advanced properties.
- **Smart Card service stopped** — Group Policy on managed laptops sometimes
  disables `SCardSvr`. Re-enable from Services.msc; if it won't stay running,
  IT has locked it down and you'll need an exception.
- **`usbipd attach` fails after Windows sleep** — re-bind and re-attach after
  resume; the WSL2 USB forwarding doesn't survive sleep cleanly.
- **`pyscard` install errors** — only happens when no prebuilt wheel exists
  for your Python version. Use Python 3.11 or 3.12.
