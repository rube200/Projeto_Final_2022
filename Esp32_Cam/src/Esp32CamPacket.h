#ifndef ESP32_CAM_ESP32CAMPACKET_H
#define ESP32_CAM_ESP32CAMPACKET_H

#include "Esp32Utils.h"

#define HEADER_SIZE 5

enum packetType {
    Invalid = 0,
    Uuid = 1,
    Config = 2,
    StartStream = 3,
    StopStream = 4,
    Image = 5,
    BellPressed = 6,
    MotionDetected = 7,
    OpenRelay = 8
};

static const char *getTypeToString(packetType type) {
    switch (type) {
        case Invalid:
            return "Invalid";
        case Uuid:
            return "Uuid";
        case Config:
            return "Config";
        case StartStream:
            return "StartStream";
        case StopStream:
            return "StopStream";
        case Image:
            return "Image";
        case BellPressed:
            return "BellPressed";
        case MotionDetected:
            return "MotionDetected";
        case OpenRelay:
            return "OpenRelay";
        default:
            return "Unknown packet type";
    }
}

class Esp32CamPacket {
public:
    Esp32CamPacket() = default;

    Esp32CamPacket(packetType, const uint8_t *, size_t);

    ~Esp32CamPacket();

    uint8_t *packet() const;

    size_t packetLen() const;

    void resetPacket();

    uint8_t *getData() const;

    size_t getDataLen() const;

    size_t getExpectedLen() const;

    packetType getPacketType() const;

    void appendData(const uint8_t *, size_t);

    void fromHeader(const uint8_t *);

private:
    void allocPacket(size_t);

    void setData(const uint8_t *) const;

    void toHeader() const;

    uint8_t *pkt = nullptr;
    size_t pkt_len = 0;

    size_t data_len = 0;
    size_t expected_len = 0;
    packetType type = Invalid;
};

#endif //ESP32_CAM_ESP32CAMPACKET_H
