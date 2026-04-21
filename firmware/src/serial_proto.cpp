#include "serial_proto.h"

#include <Arduino.h>
#include <ArduinoJson.h>

#include "nfc.h"
#include "pins.h"
#include "storage.h"

namespace serial_proto {

namespace {

constexpr size_t RX_BUF_LEN = 128;
char rx_buf[RX_BUF_LEN];
size_t rx_pos = 0;
bool active = false;

void handleLine(const char* line, const profile::CardProfile& last_card) {
    StaticJsonDocument<192> doc;
    DeserializationError err = deserializeJson(doc, line);
    if (err) {
        Serial.printf("{\"type\":\"error\",\"msg\":\"bad_json\",\"detail\":\"%s\"}\n", err.c_str());
        return;
    }
    const char* cmd = doc["cmd"] | "";
    if (!std::strcmp(cmd, "ping")) {
        Serial.println("{\"type\":\"pong\"}");
    } else if (!std::strcmp(cmd, "status")) {
        emitStatus(nfc::isReady(), nfc::firmwareVersion());
    } else if (!std::strcmp(cmd, "scan")) {
        profile::CardProfile card;
        if (nfc::readPassiveTarget(card, doc["timeout_ms"] | 1000)) {
            emitCard(card);
        } else {
            Serial.println("{\"type\":\"scan_timeout\"}");
        }
    } else if (!std::strcmp(cmd, "last")) {
        if (last_card.valid) {
            emitCard(last_card);
        } else {
            profile::CardProfile stored;
            if (storage::loadLast(stored)) {
                emitCard(stored);
            } else {
                Serial.println("{\"type\":\"no_card\"}");
            }
        }
    } else if (!std::strcmp(cmd, "nvs_count")) {
        Serial.printf("{\"type\":\"nvs_count\",\"count\":%u}\n", storage::savedCount());
    } else {
        Serial.printf("{\"type\":\"error\",\"msg\":\"unknown_cmd\",\"cmd\":\"%s\"}\n", cmd);
    }
}

}  // namespace

void begin() {
    Serial.begin(pins::USB_SERIAL_BAUD);
    rx_pos = 0;
    active = true;
    Serial.println("{\"type\":\"ready\",\"fw\":\"pn532-pentest-v1\"}");
}

bool serialModeActive() { return active; }

void tick(const profile::CardProfile& last_card) {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (rx_pos == 0) continue;
            rx_buf[rx_pos] = '\0';
            handleLine(rx_buf, last_card);
            rx_pos = 0;
        } else if (rx_pos + 1 < RX_BUF_LEN) {
            rx_buf[rx_pos++] = c;
        } else {
            rx_pos = 0;  // overflow — drop the line
            Serial.println("{\"type\":\"error\",\"msg\":\"line_too_long\"}");
        }
    }
}

void emitCard(const profile::CardProfile& card) {
    StaticJsonDocument<512> doc;
    doc["type"] = "card";
    JsonObject data = doc.createNestedObject("data");
    // reuse profile's serializer by temporarily filling a sub-document
    StaticJsonDocument<384> inner;
    card.toJson(inner);
    data.set(inner.as<JsonObject>());

    char buf[600];
    size_t n = serializeJson(doc, buf, sizeof(buf));
    if (n && n + 1 < sizeof(buf)) {
        buf[n++] = '\n';
        buf[n] = '\0';
        Serial.write(reinterpret_cast<uint8_t*>(buf), n);
    }
}

void emitStatus(bool pn532_ok, uint32_t pn532_fw_version) {
    Serial.printf("{\"type\":\"status\",\"pn532_ok\":%s,\"pn532_fw\":%lu,\"nvs_count\":%u}\n",
                  pn532_ok ? "true" : "false",
                  static_cast<unsigned long>(pn532_fw_version),
                  storage::savedCount());
}

}  // namespace serial_proto
