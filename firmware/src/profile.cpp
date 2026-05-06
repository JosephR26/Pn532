#include "profile.h"

#include <cstdio>
#include <cstring>

namespace profile {

void CardProfile::reset() {
    valid = false;
    id[0] = '\0';
    captured_at_epoch = 0;
    std::strcpy(technology, "unknown");
    std::memset(uid, 0, MAX_UID_LEN);
    uid_len = 0;
    atqa = 0;
    sak = 0;
    std::strcpy(tag_type, "unknown");
}

void uidToHex(const uint8_t* uid, uint8_t len, char* out, size_t out_len) {
    static const char kHex[] = "0123456789abcdef";
    size_t written = 0;
    for (uint8_t i = 0; i < len && written + 2 < out_len; ++i) {
        out[written++] = kHex[(uid[i] >> 4) & 0xF];
        out[written++] = kHex[uid[i] & 0xF];
    }
    if (written < out_len) out[written] = '\0';
}

const char* inferTagType(uint16_t atqa, uint8_t sak) {
    switch (sak) {
        case 0x00:
            if (atqa == 0x0044) return "mifare_ultralight";
            return "unknown";
        case 0x08:
            return "mifare_classic_1k";
        case 0x09:
            return "mifare_mini";
        case 0x18:
            return "mifare_classic_4k";
        case 0x10:
        case 0x11:
            return "mifare_plus";
        case 0x20:
            return "desfire_ev1";
        case 0x28:
            return "desfire_ev2";
        default:
            return "unknown";
    }
}

void CardProfile::toJson(JsonDocument& doc) const {
    doc["schema_version"] = "1.0.0";
    doc["source"] = "firmware";
    if (id[0]) doc["id"] = id;
    if (captured_at_epoch) doc["captured_at_epoch"] = captured_at_epoch;

    JsonObject nfc = doc.createNestedObject("nfc");
    nfc["technology"] = technology;

    char uid_hex[MAX_UID_LEN * 2 + 1];
    uidToHex(uid, uid_len, uid_hex, sizeof(uid_hex));
    nfc["uid"] = uid_hex;

    char atqa_hex[5];
    std::snprintf(atqa_hex, sizeof(atqa_hex), "%04x", atqa);
    nfc["atqa"] = atqa_hex;

    char sak_hex[3];
    std::snprintf(sak_hex, sizeof(sak_hex), "%02x", sak);
    nfc["sak"] = sak_hex;

    nfc["tag_type"] = tag_type;
}

size_t CardProfile::toJsonLine(char* buf, size_t buf_len) const {
    StaticJsonDocument<512> doc;
    toJson(doc);
    size_t n = serializeJson(doc, buf, buf_len);
    if (n + 1 < buf_len) {
        buf[n++] = '\n';
        buf[n] = '\0';
    }
    return n;
}

}  // namespace profile
