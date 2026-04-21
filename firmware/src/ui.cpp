#include "ui.h"

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Bounce2.h>
#include <Wire.h>

#include "pins.h"

namespace ui {

const char* const kMenuLabels[MENU_ITEMS] = {
    "Scan card",
    "Last card",
    "Self-test",
    "Serial mode",
};

namespace {

Adafruit_SSD1306 oled(pins::OLED_WIDTH, pins::OLED_HEIGHT, &Wire, -1);

Bounce btn_up;
Bounce btn_down;
Bounce btn_left;
Bounce btn_right;
Bounce btn_center;

Screen screen = Screen::Splash;
bool oled_ok = false;

constexpr unsigned long DEBOUNCE_MS = 25;

void configureNavPins() {
    pinMode(pins::NAV_UP, INPUT);       // external pull-up on GPIO34
    pinMode(pins::NAV_DOWN, INPUT);     // external pull-up on GPIO35
    pinMode(pins::NAV_LEFT, INPUT_PULLUP);
    pinMode(pins::NAV_RIGHT, INPUT_PULLUP);
    pinMode(pins::NAV_CENTER, INPUT_PULLUP);

    btn_up.attach(pins::NAV_UP);
    btn_up.interval(DEBOUNCE_MS);
    btn_down.attach(pins::NAV_DOWN);
    btn_down.interval(DEBOUNCE_MS);
    btn_left.attach(pins::NAV_LEFT);
    btn_left.interval(DEBOUNCE_MS);
    btn_right.attach(pins::NAV_RIGHT);
    btn_right.interval(DEBOUNCE_MS);
    btn_center.attach(pins::NAV_CENTER);
    btn_center.interval(DEBOUNCE_MS);
}

void drawHeader(const char* title) {
    oled.setTextSize(1);
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(0, 0);
    oled.print(title);
    oled.drawFastHLine(0, 10, pins::OLED_WIDTH, SSD1306_WHITE);
    oled.setCursor(0, 14);
}

}  // namespace

void begin() {
    Wire.begin(pins::OLED_SDA, pins::OLED_SCL);
    oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, pins::OLED_ADDR);
    if (oled_ok) {
        oled.clearDisplay();
        oled.display();
    }
    configureNavPins();
}

void tick() {
    btn_up.update();
    btn_down.update();
    btn_left.update();
    btn_right.update();
    btn_center.update();
}

NavEvent pollNav() {
    if (btn_up.fell()) return NavEvent::Up;
    if (btn_down.fell()) return NavEvent::Down;
    if (btn_left.fell()) return NavEvent::Left;
    if (btn_right.fell()) return NavEvent::Right;
    if (btn_center.fell()) return NavEvent::Center;
    return NavEvent::None;
}

Screen currentScreen() { return screen; }

void setScreen(Screen s) { screen = s; }

void renderSplash(uint32_t pn532_fw_version, bool pn532_ok) {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("PN532 Pentest");
    oled.setCursor(0, 20);
    oled.print("PN532: ");
    if (pn532_ok) {
        oled.print("OK v");
        oled.print((pn532_fw_version >> 16) & 0xFF);
        oled.print(".");
        oled.print((pn532_fw_version >> 8) & 0xFF);
    } else {
        oled.print("NOT FOUND");
    }
    oled.setCursor(0, 32);
    oled.print("OLED : OK");
    oled.setCursor(0, 50);
    oled.print("[CTR] to continue");
    oled.display();
}

void renderSelfTest(bool pn532_ok, bool oled_test_ok) {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("Self-test");
    oled.setCursor(0, 20);
    oled.print("PN532: ");
    oled.print(pn532_ok ? "OK" : "FAIL");
    oled.setCursor(0, 32);
    oled.print("OLED : ");
    oled.print(oled_test_ok ? "OK" : "FAIL");
    oled.setCursor(0, 50);
    oled.print("[CTR] menu");
    oled.display();
}

void renderMainMenu(uint8_t selected_index) {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("Main menu");
    for (uint8_t i = 0; i < MENU_ITEMS; ++i) {
        oled.setCursor(0, 16 + i * 12);
        oled.print(i == selected_index ? "> " : "  ");
        oled.print(kMenuLabels[i]);
    }
    oled.display();
}

void renderScanning() {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("Scanning");
    oled.setCursor(0, 24);
    oled.print("Present card to");
    oled.setCursor(0, 36);
    oled.print("PN532 antenna");
    oled.setCursor(0, 54);
    oled.print("[LEFT] cancel");
    oled.display();
}

void renderCard(const profile::CardProfile& card) {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("Card");
    oled.setCursor(0, 14);
    oled.print("UID: ");
    char hex[profile::MAX_UID_LEN * 2 + 1];
    profile::uidToHex(card.uid, card.uid_len, hex, sizeof(hex));
    oled.print(hex);
    oled.setCursor(0, 26);
    oled.print("Tech: ");
    oled.print(card.technology);
    oled.setCursor(0, 38);
    oled.print("Type: ");
    oled.print(card.tag_type);
    oled.setCursor(0, 54);
    oled.print("[LEFT] back  [CTR] save");
    oled.display();
}

void renderMessage(const char* line1, const char* line2) {
    if (!oled_ok) return;
    oled.clearDisplay();
    drawHeader("PN532 Pentest");
    oled.setCursor(0, 24);
    if (line1) oled.print(line1);
    oled.setCursor(0, 40);
    if (line2) oled.print(line2);
    oled.display();
}

}  // namespace ui
