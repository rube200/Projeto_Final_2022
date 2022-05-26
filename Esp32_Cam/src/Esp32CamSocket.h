#ifndef ESP32_CAM_ESP32CAMSOCKET_H
#define ESP32_CAM_ESP32CAMSOCKET_H

#include "Esp32CamPacket.h"
#include "Esp32Utils.h"
#include "WiFiClient.h"

#define CONNECT_TRY 5
#define STREAM_TIMEOUT 30500000//30.5s -> Py try to communicate every 10s

class Esp32CamSocket : WiFiClient {
public:
    bool connectSocket(bool should_restart_esp = false);

    void processSocket();

    void setHost(const char *, uint16_t);

    bool isRelayRequested();

    bool isStreamRequested();

    void sendBellPressed();

    void sendFrame(uint8_t *, size_t);

    void sendMotionDetected();

private:
    void processConfig(const uint8_t *, size_t);

    void processPacket();

    size_t receiveHeader(int);

    void sendPacket(const Esp32CamPacket &, const String & = String());

    void sendUuid();

    const char *host = nullptr;
    uint16_t port = 0;
    Esp32CamPacket readPacket;

    uint64_t streamUntil = 0;
    uint64_t bellCaptureDuration = 0;//0 means single frame
    bool bellSent = false;

    bool isConfigured = false;
    uint64_t openRelayUntil = 0;
    uint64_t relayOpenDuration = 5000000;//5s
};

#endif //ESP32_CAM_ESP32CAMSOCKET_H
