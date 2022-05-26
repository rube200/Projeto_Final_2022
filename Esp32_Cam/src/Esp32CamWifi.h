#ifndef ESP32_CAM_ESP32CAMWIFI_H
#define ESP32_CAM_ESP32CAMWIFI_H

#include <EEPROM.h>
#include "Esp32Utils.h"
#include "WiFiManager.h"

#define ACCESS_POINT_NAME "Video-Doorbell"
#define REMOTE_HOST "192.168.137.1"
#define REMOTE_PORT "1352"

class Esp32CamWifi : WiFiManager {
public:
    Esp32CamWifi();

    void begin();

    const char *getHostParam() const;

    uint16_t getPortParam() const;

    static bool isReady();

    void setNormalMode();

    void setSocketMode();

    boolean requestConfig();

private:
    void loadCostumeParameters();

    void saveCostumeParameters() const;

    bool isPortalSaved = false;
    WiFiManagerParameter socket_host_parameter = WiFiManagerParameter("Host", "Socket host", REMOTE_HOST, 50);
    WiFiManagerParameter socket_port_parameter = WiFiManagerParameter("Port", "Socket port", REMOTE_PORT, 5);
};

#endif //ESP32_CAM_ESP32CAMWIFI_H
