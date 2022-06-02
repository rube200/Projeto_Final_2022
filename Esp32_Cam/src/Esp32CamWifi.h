#ifndef ESP32_CAM_ESP32CAMWIFI_H
#define ESP32_CAM_ESP32CAMWIFI_H

#include <EEPROM.h>
#include "Esp32Utils.h"
#include "WiFiManager.h"

#define ACCESS_POINT_NAME "Video-Doorbell"
#define REMOTE_HOST "192.168.137.1"
#define REMOTE_PORT "2376"

//work around for private stuff in WifiManager
//consider using libs from martong in github
class WifiManagerParam : public WiFiManagerParameter {
public:
    WifiManagerParam(const char *id, const char *label, const char *defaultValue, int length) : WiFiManagerParameter(id, label, defaultValue, length) {}

    void clearParams() {
        Serial.println(getValue());
        Serial.println(getValueLength());
        init(nullptr,  getLabel(), getValue(), getValueLength(), "", getLabelPlacement());
        Serial.println(getValue());
        Serial.println(getValueLength());
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

private:
    void setParamsMode();

    void setUsernameMode();

    void clearParams();

    void loadCostumeParameters();

    void saveCostumeParameters() const;


    bool isPortalSaved = false;
    byte isUsernameMode = 0;//0 not usernameMode, 1 first time usernameMode, 2 and above not first time in usernameMode(Used to show that last username inserted does not exist)
    WifiManagerParam socket_host_parameter = WifiManagerParam("Host", "Socket host", REMOTE_HOST, 50);
    WifiManagerParam socket_port_parameter = WifiManagerParam("Port", "Socket port", REMOTE_PORT, 5);
    WifiManagerParam username_parameter = WifiManagerParam("Username","Doorbell not registered, please insert your username:","", 50);
};

#endif //ESP32_CAM_ESP32CAMWIFI_H
