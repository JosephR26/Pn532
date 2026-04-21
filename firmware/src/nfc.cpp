#include "nfc.h"

#include <PN532.h>
#include <PN532_HSU.h>

#include "pins.h"

namespace nfc {

namespace {
HardwareSerial pn532_uart(2);
PN532_HSU pn532_hsu(pn532_uart);
PN532 pn532(pn532_hsu);
uint32_t fw_version = 0;
bool ready = false;

const char* inferFromUidLen(uint8_t uid_len) {
    if (uid_len == 4) return "mifare_classic_1k";
    if (uid_len == 7) return "mifare_ultralight";
    if (uid_len == 10) return "iso14443a_double";
    return "unknown";
}
}  // namespace

bool begin() {
    pn532_uart.begin(pins::PN532_SERIAL_BAUD, SERIAL_8N1, pins::PN532_RX, pins::PN532_TX);
    pn532.begin();
    fw_version = pn532.getFirmwareVersion();
    if (!fw_version) {
        ready = false;
        return false;
    }
    pn532.SAMConfig();
    pn532.setPassiveActivationRetries(0x05);
    ready = true;
    return true;
}

uint32_t firmwareVersion() { return fw_version; }

bool isReady() { return ready; }

bool readPassiveTarget(profile::CardProfile& out, uint16_t timeout_ms) {
    if (!ready) return false;

    uint8_t uid[profile::MAX_UID_LEN] = {0};
    uint8_t uid_len = 0;

    bool found = pn532.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uid_len, timeout_ms);
    if (!found) return false;

    out.reset();
    out.valid = true;
    std::memcpy(out.uid, uid, uid_len);
    out.uid_len = uid_len;
    std::strcpy(out.technology, "iso14443a");

    // ATQA/SAK require the lower-level inListPassiveTarget response parsing that
    // elechouse/PN532 does not expose. v1 leaves them zero; the host CLI via
    // libnfc fills them in on the desk-side path.
    out.atqa = 0;
    out.sak = 0;

    const char* tag = profile::inferTagType(out.atqa, out.sak);
    if (std::strcmp(tag, "unknown") == 0) tag = inferFromUidLen(out.uid_len);
    std::strncpy(out.tag_type, tag, sizeof(out.tag_type) - 1);
    out.captured_at_epoch = millis() / 1000;
    return true;
}

}  // namespace nfc
