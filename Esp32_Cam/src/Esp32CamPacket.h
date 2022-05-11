#ifndef ESP32_CAM_ESP32CAMPACKET_H
#define ESP32_CAM_ESP32CAMPACKET_H

#include "Esp32Utils.h"

#define HEADER_SIZE 5

enum packetType : char {
    Invalid = 0,
    HandShake = 1,
    StartStream = 2,
    StopStream = 3,
    Image = 4,
    BellPressed = 5,
    MotionDetected = 6,
    OpenRelay = 7,
    Test = 8
};

static const char *getTypeToString(packetType type) {
    static auto unknown_type = String("Unknown type: 0");
    switch (type) {
        case Invalid:
            return "Invalid";
        case HandShake:
            return "HandShake";
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
    }

    unknown_type[14] = (char)type;
    return unknown_type.c_str();
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
    packetType type = Invalid;
};

#endif //ESP32_CAM_ESP32CAMPACKET_H
