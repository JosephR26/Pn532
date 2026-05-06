#pragma once

#include "profile.h"

namespace serial_proto {

void begin();
void tick(const profile::CardProfile& last_card);
void emitCard(const profile::CardProfile& card);
void emitStatus(bool pn532_ok, uint32_t pn532_fw_version);
bool serialModeActive();

}  // namespace serial_proto
