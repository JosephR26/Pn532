#pragma once

#include <Arduino.h>
#include "profile.h"

namespace nfc {

bool begin();
uint32_t firmwareVersion();
bool readPassiveTarget(profile::CardProfile& out, uint16_t timeout_ms = 500);
bool isReady();

}  // namespace nfc
