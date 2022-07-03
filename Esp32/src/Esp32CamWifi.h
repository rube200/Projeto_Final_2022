#ifndef ESP32_CAM_ESP32CAMWIFI_H
#define ESP32_CAM_ESP32CAMWIFI_H

#include <EEPROM.h>
#include "Esp32Utils.h"
#include "WiFiManager.h"

#define ACCESS_POINT_PREFIX_NAME "Video-Doorbell_"

//work around for private stuff in WifiManager
//consider using libs from martong in GitHub
class WifiManagerParam : public WiFiManagerParameter {
public:
    WifiManagerParam(const char *id, const char *label, const char *defaultValue, int length) : WiFiManagerParameter(id,
                                                                                                                     label,
                                                                                                                     defaultValue,
                                                                                                                     length) {}

    WifiManagerParam(const char *id, const char *label, const char *defaultValue, int length, const char *custom)
            : WiFiManagerParameter(id, label, defaultValue, length, custom) {}

    void clearParams() {
        init(nullptr,  getLabel(), getValue(), getValueLength(), "", getLabelPlacement());
    }

    void setLabel(const char *label) {
        init(getID(),  label, getValue(), getValueLength(), getCustomHTML(), getLabelPlacement());
    }
};

class Esp32CamWifi : private WiFiManager {
public:
    Esp32CamWifi();

    void begin();

    const char *getHostParam() const;

    uint16_t getPortParam() const;

    static bool isReady();

    boolean requestSocketConfig();

    const char *requestUsername();

    bool hasRelay() const;

private:
    void setParamsMode();

    void setUsernameMode();

    void clearParams();

    void loadCostumeParameters();

    void saveCostumeParameters() const;

    char *access_point_name = nullptr;
    bool isPortalSaved = false;
    byte wifiParamsMode = 0;//0 default (wifi and host settings), 1 just host settings, 2 register username, 3 username not exists, 4 and above nothing
    WifiManagerParam socket_host_parameter = WifiManagerParam("Host", "Socket host", REMOTE_HOST, 50);
    WifiManagerParam socket_port_parameter = WifiManagerParam("Port", "Socket port", REMOTE_PORT_STR, 5);
    WifiManagerParam username_parameter = WifiManagerParam("Username",
                                                           "Doorbell not registered, please insert your username:", "",
                                                           50);
    WifiManagerParam relay_check_parameter = WifiManagerParam("Relay_Check", "Have relay?", "", 1,
                                                              "checked type=\"checkbox\"");
    bool relay = true;
};

#endif //ESP32_CAM_ESP32CAMWIFI_H
