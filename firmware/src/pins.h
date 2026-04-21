#pragma once

namespace pins {

constexpr int PN532_RX = 16;
constexpr int PN532_TX = 17;
constexpr int PN532_IRQ = 4;
constexpr int PN532_RST = 25;

constexpr int OLED_SDA = 21;
constexpr int OLED_SCL = 22;
constexpr uint8_t OLED_ADDR = 0x3C;
constexpr int OLED_WIDTH = 128;
constexpr int OLED_HEIGHT = 64;

constexpr int NAV_UP = 34;
constexpr int NAV_DOWN = 35;
constexpr int NAV_LEFT = 32;
constexpr int NAV_RIGHT = 33;
constexpr int NAV_CENTER = 27;

constexpr int STATUS_LED = 2;

constexpr unsigned long USB_SERIAL_BAUD = 115200;
constexpr unsigned long PN532_SERIAL_BAUD = 115200;

}  // namespace pins
