#pragma once

#include "profile.h"

namespace storage {

bool begin();
bool saveLast(const profile::CardProfile& card);
bool loadLast(profile::CardProfile& out);
uint16_t savedCount();

}  // namespace storage
