#pragma once

#include <Arduino.h>
#include "profile.h"

namespace ui {

enum class NavEvent : uint8_t {
    None = 0,
    Up,
    Down,
    Left,
    Right,
    Center,
};

enum class Screen : uint8_t {
    Splash,
    SelfTest,
    MainMenu,
    Scanning,
    LastCard,
};

void begin();
void tick();

NavEvent pollNav();

void renderSplash(uint32_t pn532_fw_version, bool pn532_ok);
void renderSelfTest(bool pn532_ok, bool oled_ok);
void renderMainMenu(uint8_t selected_index);
void renderScanning();
void renderCard(const profile::CardProfile& card);
void renderMessage(const char* line1, const char* line2);

Screen currentScreen();
void setScreen(Screen s);

constexpr uint8_t MENU_ITEMS = 4;
extern const char* const kMenuLabels[MENU_ITEMS];

}  // namespace ui
