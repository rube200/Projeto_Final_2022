#ifndef ESP32_CAM_ESP32CAM_H
#define ESP32_CAM_ESP32CAM_H

#include "Esp32CamCamera.h"
#include "Esp32CamGpio.h"
#include "Esp32CamSocket.h"
#include "Esp32CamWifi.h"

#define SERIAL_BAUD 115200

class Esp32Cam {
public:
    void begin();

    void loop();

private:
    void processGpio();

    void sendFrame();

    bool shouldSendFrame();

    void startSocket();

    Esp32CamCamera camera;
    Esp32CamGpio gpio;
    Esp32CamSocket socket;
    Esp32CamWifi wifi;
};

#endif