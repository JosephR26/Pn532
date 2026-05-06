#include <Arduino.h>

#include "nfc.h"
#include "pins.h"
#include "profile.h"
#include "serial_proto.h"
#include "storage.h"
#include "ui.h"

namespace {

profile::CardProfile g_last_card;
uint8_t g_menu_index = 0;
unsigned long g_splash_started_ms = 0;
constexpr unsigned long SPLASH_HOLD_MS = 1500;

void enterScanning() {
    ui::setScreen(ui::Screen::Scanning);
    ui::renderScanning();
}

void enterMenu() {
    ui::setScreen(ui::Screen::MainMenu);
    ui::renderMainMenu(g_menu_index);
}

void tryScanOnce() {
    profile::CardProfile card;
    if (nfc::readPassiveTarget(card, 500)) {
        g_last_card = card;
        storage::saveLast(card);
        serial_proto::emitCard(card);
        ui::setScreen(ui::Screen::LastCard);
        ui::renderCard(g_last_card);
    }
}

void handleMenuNav(ui::NavEvent ev) {
    switch (ev) {
        case ui::NavEvent::Up:
            g_menu_index = (g_menu_index + ui::MENU_ITEMS - 1) % ui::MENU_ITEMS;
            ui::renderMainMenu(g_menu_index);
            break;
        case ui::NavEvent::Down:
            g_menu_index = (g_menu_index + 1) % ui::MENU_ITEMS;
            ui::renderMainMenu(g_menu_index);
            break;
        case ui::NavEvent::Center:
            switch (g_menu_index) {
                case 0: enterScanning(); break;
                case 1:
                    if (g_last_card.valid) {
                        ui::setScreen(ui::Screen::LastCard);
                        ui::renderCard(g_last_card);
                    } else if (storage::loadLast(g_last_card)) {
                        ui::setScreen(ui::Screen::LastCard);
                        ui::renderCard(g_last_card);
                    } else {
                        ui::renderMessage("No card stored.", "Scan one first.");
                    }
                    break;
                case 2:
                    ui::setScreen(ui::Screen::SelfTest);
                    ui::renderSelfTest(nfc::isReady(), true);
                    break;
                case 3:
                    ui::renderMessage("Serial JSON mode.", "Send {\"cmd\":\"ping\"}");
                    break;
            }
            break;
        default:
            break;
    }
}

void handleScanningNav(ui::NavEvent ev) {
    if (ev == ui::NavEvent::Left) {
        enterMenu();
    }
}

void handleLastCardNav(ui::NavEvent ev) {
    if (ev == ui::NavEvent::Left) {
        enterMenu();
    } else if (ev == ui::NavEvent::Center) {
        if (storage::saveLast(g_last_card)) {
            ui::renderMessage("Saved to NVS.", "");
        } else {
            ui::renderMessage("Save failed.", "");
        }
    }
}

void handleSelfTestNav(ui::NavEvent ev) {
    if (ev == ui::NavEvent::Center || ev == ui::NavEvent::Left) {
        enterMenu();
    }
}

}  // namespace

void setup() {
    pinMode(pins::STATUS_LED, OUTPUT);
    digitalWrite(pins::STATUS_LED, LOW);

    serial_proto::begin();
    storage::begin();
    ui::begin();

    bool pn532_ok = nfc::begin();
    ui::renderSplash(nfc::firmwareVersion(), pn532_ok);
    g_splash_started_ms = millis();

    if (pn532_ok) digitalWrite(pins::STATUS_LED, HIGH);
}

void loop() {
    ui::tick();
    serial_proto::tick(g_last_card);

    ui::NavEvent ev = ui::pollNav();

    switch (ui::currentScreen()) {
        case ui::Screen::Splash:
            if (ev == ui::NavEvent::Center ||
                millis() - g_splash_started_ms > SPLASH_HOLD_MS) {
                enterMenu();
            }
            break;
        case ui::Screen::MainMenu:
            handleMenuNav(ev);
            break;
        case ui::Screen::Scanning:
            handleScanningNav(ev);
            tryScanOnce();
            break;
        case ui::Screen::LastCard:
            handleLastCardNav(ev);
            break;
        case ui::Screen::SelfTest:
            handleSelfTestNav(ev);
            break;
    }

    delay(10);
}
