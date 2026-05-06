# Hardware

Wiring, pinout, and assembly notes for the handheld field unit.

## Bill of materials

| Part                           | Notes                                               |
|--------------------------------|-----------------------------------------------------|
| ESP32 DevKitC-32 (30-pin)      | WROOM-32 module; 3.3V logic; USB-UART (CP2102/CH340)|
| PN532 breakout (Elechouse v3)  | Set DIP switches for HSU/UART mode                  |
| SSD1306 0.96" OLED             | 128×64, I²C, address 0x3C                           |
| 5-way nav switch               | 4 directions + centre press; common pin to GND      |
| 2× N.O. momentary buttons      | External RESET and BOOT                             |
| 5× 10kΩ resistors              | Pull-ups for input-only GPIOs that lack internal    |
| 2× 0.1µF capacitors            | Decoupling across PN532 3V3/GND and OLED 3V3/GND    |
| (optional) LiPo 1S + TP4056    | For untethered field use (v3)                       |

## PN532 DIP switch: HSU mode

The Elechouse PN532 has a mode-select DIP. For UART (HSU) mode:

```
SEL0 = 0
SEL1 = 0
```

(I²C is `SEL0=1, SEL1=0`; SPI is `SEL0=0, SEL1=1`. We're not using those.)

## Pinout

| Function                    | ESP32 GPIO    | Notes                                                       |
|-----------------------------|---------------|-------------------------------------------------------------|
| PN532 TX → ESP32 RX (UART2) | GPIO16        | `HardwareSerial(2)` RX                                      |
| PN532 RX ← ESP32 TX (UART2) | GPIO17        | `HardwareSerial(2)` TX                                      |
| PN532 IRQ                   | GPIO4         | optional; pull-up for card-present interrupt                |
| PN532 RSTO / RSTPD_N        | GPIO25        | soft reset                                                  |
| PN532 3V3                   | 3V3 rail      | DO NOT use 5V — breakout accepts 3.3V directly              |
| PN532 GND                   | GND           |                                                             |
| OLED SDA                    | GPIO21        | I²C addr 0x3C                                               |
| OLED SCL                    | GPIO22        | I²C                                                         |
| OLED VCC                    | 3V3           |                                                             |
| OLED GND                    | GND           |                                                             |
| Nav UP                      | GPIO34        | **input-only — external 10kΩ pull-up to 3V3 required**      |
| Nav DOWN                    | GPIO35        | **input-only — external 10kΩ pull-up to 3V3 required**      |
| Nav LEFT                    | GPIO32        | internal pull-up OK (`INPUT_PULLUP`)                        |
| Nav RIGHT                   | GPIO33        | internal pull-up OK                                         |
| Nav CENTER                  | GPIO27        | internal pull-up OK                                         |
| Nav common                  | GND           | shared common leg                                           |
| External RESET button       | → EN pin      | other leg to GND                                            |
| External BOOT button        | → GPIO0       | other leg to GND                                            |
| Status LED                  | GPIO2         | on-board blue LED; strap pin — drive only after boot        |

## Bootstrapping pins — avoid

Do not use for peripherals: **GPIO0, GPIO2, GPIO5, GPIO12, GPIO15**. Driving these low/high at boot changes the boot mode or SDIO strap voltage. GPIO0 and GPIO2 appear in the pinout above only because they are the official BOOT pin and on-board status LED — both are safe in those roles because the board is already designed around them.

## Flashing procedure

Auto-reset via USB-UART DTR/RTS normally works on the DevKitC, so `pio run -t upload` will just work. If auto-reset fails (or you are flashing via a battery-powered enclosure without access to the on-board RST/BOOT), use the externals:

1. Hold **BOOT** (GPIO0 → GND).
2. Tap **RESET** (EN → GND).
3. Release **BOOT**.
4. ESP32 is now in serial bootloader mode; run `pio run -t upload`.

## Wiring notes

- PN532 UART lines (TX/RX) are 3.3V logic. No level shifting needed with ESP32.
- The PN532's on-board regulator accepts 3.3V directly. **Do not feed the breakout 5V** — some clones route 5V straight to the PN532 chip, which is a 3.3V part.
- Keep the PN532 antenna away from large metal surfaces and the ESP32 module itself — metal detunes the 13.56 MHz loop and kills read range.
- The OLED and PN532 share the 3V3 rail; add a 10µF bulk cap near the PN532 if you see brown-outs on card presentation.
- Nav-switch common goes to GND. Each direction line is pulled up (external 10k for GPIO34/35; internal for the others) and reads LOW when pressed.

## Host platform (Windows 11)

The handheld talks to the laptop over USB serial. On Windows 11 it enumerates as a `COMx` port after the Silicon Labs CP210x VCP driver is installed. The MSR605X and CCID smartcard reader add their own ports (`COMy`) and PC/SC reader entries respectively. See `docs/windows.md` for full driver and WSL2 instructions.

## Power

- **Tethered:** USB via the DevKitC's on-board UART bridge. 500 mA from the host is enough for normal operation (PN532 peaks ~150 mA on card read).
- **Untethered (v3):** 1S LiPo (3.7V nominal) → TP4056 charger → boost to 5V (MT3608) → DevKitC VIN, or direct 3.7V → 3V3 rail via LDO. Battery level monitoring via ADC on GPIO35 (switch nav-DOWN to another pin if you go this route).

## Enclosure placement

- PN532 antenna on the back face so the card is presented to the back of the unit.
- OLED on the front, nav switch below it, external RESET + BOOT on the side (recessed to avoid accidental press).
- Keep a 10+ mm air gap between the PN532 antenna and any battery or ESP32 module.
