#include "storage.h"

#include <Preferences.h>

namespace storage {

namespace {
Preferences prefs;
constexpr const char* kNamespace = "pn532p";
constexpr const char* kLastKey = "last";
constexpr const char* kCountKey = "count";
}  // namespace

bool begin() {
    return prefs.begin(kNamespace, false);
}

bool saveLast(const profile::CardProfile& card) {
    if (!card.valid) return false;
    size_t written = prefs.putBytes(kLastKey, &card, sizeof(card));
    if (written != sizeof(card)) return false;
    uint16_t count = prefs.getUShort(kCountKey, 0);
    prefs.putUShort(kCountKey, count + 1);
    return true;
}

bool loadLast(profile::CardProfile& out) {
    size_t sz = prefs.getBytesLength(kLastKey);
    if (sz != sizeof(out)) return false;
    size_t read = prefs.getBytes(kLastKey, &out, sizeof(out));
    return read == sizeof(out) && out.valid;
}

uint16_t savedCount() {
    return prefs.getUShort(kCountKey, 0);
}

}  // namespace storage
