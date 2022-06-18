#ifndef ESP32_CAM_ESP32CAMSOCKET_H
#define ESP32_CAM_ESP32CAMSOCKET_H

#include "Esp32CamPacket.h"
#include "Esp32Utils.h"
#include "WiFiClient.h"

#define CONNECT_TRY 5
#define CONFIG_RECV_SIZE 13
#define USERNAME_RECV_SIZE 1
#define STREAM_TIMEOUT 30500000//30.5s -> Py try to communicate every 10s

enum socketState {
    Nothing = 0,
    UuidNeeded = 1,
    UuidSent = 2,
    ConfigReceived = 3,
    UsernameSent = 4,
    Ready = 5
};

class Esp32CamSocket : private WiFiClient {
public:
    void setHost(const char *, uint16_t);

    void setUsername(const char *);

    bool connectSocket(bool should_restart_esp = false);


    void processSocket();


    bool isReady() const;

    bool isRelayRequested();

    bool isStreamRequested();

    bool needUsernamePortal() const;


    void sendBellPressed();

    void sendMotionDetected();

    void sendFrame(uint8_t *, size_t);


private:
    void resetValues();

    size_t receiveHeader(int);

    void processPacket();


    bool sendUuid();

    bool sendUsername();

    void processConfig(const uint8_t *, size_t);

    void processUsername(const uint8_t *, size_t);

    bool sendPacket(const Esp32CamPacket &, const String & = String());


    const char *host = REMOTE_HOST;
    uint16_t port = REMOTE_PORT;
    const char *username = nullptr;


    Esp32CamPacket readPacket;
    bool usernamePortal = false;
    socketState isSocketReady = Nothing;


    uint64_t streamUntil = 0;
    uint64_t bellCaptureDuration = 0;//0 means single frame
    uint64_t motionCaptureDuration = 0;//0 means single frame
    bool bellSent = false;
    bool motionSent = false;
    uint64_t openRelayUntil = 0;
    uint64_t relayOpenDuration = 5000000;//5s
};

#endif //ESP32_CAM_ESP32CAMSOCKET_H
