#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace profile {

constexpr size_t MAX_UID_LEN = 10;

struct CardProfile {
    bool valid = false;
    char id[37] = {0};
    uint32_t captured_at_epoch = 0;

    char technology[12] = "unknown";
    uint8_t uid[MAX_UID_LEN] = {0};
    uint8_t uid_len = 0;
    uint16_t atqa = 0;
    uint8_t sak = 0;
    char tag_type[32] = "unknown";

    void reset();
    void toJson(JsonDocument& doc) const;
    size_t toJsonLine(char* buf, size_t buf_len) const;
};

const char* inferTagType(uint16_t atqa, uint8_t sak);
void uidToHex(const uint8_t* uid, uint8_t len, char* out, size_t out_len);

}  // namespace profile
