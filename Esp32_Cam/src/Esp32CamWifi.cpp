#include "Esp32CamWifi.h"

Esp32CamWifi::Esp32CamWifi() {
#if DEBUG_WIFI
    setDebugOutput(true);
#else
    setDebugOutput(false);
#endif
    setDarkMode(true);

    const char *wifiMenu[] = {"wifi", "exit"};
    setMenu(wifiMenu, 2);

#if DEBUG
    addParameter(&socket_host_parameter);
    addParameter(&socket_port_parameter);
#endif

    setSaveParamsCallback([this] {
#pragma clang diagnostic push
#pragma ide diagnostic ignored "UnusedValue"
        isPortalSaved = true;
#pragma clang diagnostic pop
        if (!isUsernameMode) {
            saveCostumeParameters();
        }
        stopConfigPortal();
    });
}

void Esp32CamWifi::begin() {
    Serial.println("Starting WiFiManager...");

    auto * mac = getMac();
    char tmpMacStr[13] = {0};
    sprintf(tmpMacStr, "%02X%02X%02X%02X%02X%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    auto * macStr = espRealloc(mac, 28);
    memcpy(macStr, ACCESS_POINT_PREFIX_NAME, 16);
    for (int i = 0; i < 13; ++i) {
        auto index = 15 + i;
        macStr[index] = tmpMacStr[i];
    }
    access_point_name = (char *)macStr;

#if DEBUG
    loadCostumeParameters();
#endif

    //Fix bug related to params and EEPROM save
    if (!getWiFiIsSaved()) {
        const auto ssid = getWiFiSSID().c_str();
        const auto pass = getWiFiPass().c_str();
        if (ssid && *ssid != 0x00 && strlen(ssid) <= 32) {
            wifi_config_t conf;
            memset(&conf, 0, sizeof(wifi_config_t));
            strncpy(reinterpret_cast<char *>(conf.sta.ssid), ssid, 32);

            if (pass && strlen(pass) <= 64) {
                strncpy(reinterpret_cast<char *>(conf.sta.password), pass, 64);
            }

            esp_wifi_set_config(WIFI_IF_STA, &conf);
        }
    }

    while (!autoConnect(access_point_name)) {
        Serial.println("Failed to connect to WiFi.");
    }

    Serial.println("Successfully connected to WiFi.");
}

#if DEBUG
const char *Esp32CamWifi::getHostParam() const {
    return socket_host_parameter.getValue();
}

uint16_t Esp32CamWifi::getPortParam() const {
    return atoi(socket_port_parameter.getValue()); // NOLINT(cert-err34-c)
}
#endif

bool Esp32CamWifi::isReady() {
    if (WiFi.isConnected()) {
        return true;
    }

    Serial.println("Wifi not connected! Waiting for auto reconnect");
    return espDelayUs(5000, []() { return !WiFi.isConnected(); });//wait for auto reconnect
}

void Esp32CamWifi::loadCostumeParameters() {
    if (!EEPROM.begin(64)) {
        Serial.println("Fail to begin EEPROM at loadCostumeParameters.");
        return;
    }

    const auto ip = EEPROM.readString(0);
    socket_host_parameter.setValue(ip.c_str(), 50);

    const auto port = String(EEPROM.readUShort(50));
    socket_port_parameter.setValue(port.c_str(), 5);
    EEPROM.end();
}

boolean Esp32CamWifi::requestSocketConfig() {
    isPortalSaved = false;
    setParamsMode();

    if (WiFiManager::startConfigPortal(access_point_name))
        return true;

    return isPortalSaved;
}

const char *Esp32CamWifi::requestUsername() {
    isPortalSaved = false;
    setUsernameMode();

#pragma clang diagnostic push
#pragma ide diagnostic ignored "ConstantConditionsOC"
    if (WiFiManager::startConfigPortal(access_point_name) || isPortalSaved)
        return username_parameter.getValue();
#pragma clang diagnostic pop

    return nullptr;
}

void Esp32CamWifi::saveCostumeParameters() const {
    if (!EEPROM.begin(64)) {
        Serial.println("Fail to begin EEPROM.");
        return;
    }

    EEPROM.writeString(0, socket_host_parameter.getValue());
    EEPROM.writeUShort(50, atoi(socket_port_parameter.getValue())); // NOLINT(cert-err34-c)
    EEPROM.end();
}

void Esp32CamWifi::setParamsMode() {
    const char *paramsMenu[] = {"param", "exit"};
    setMenu(paramsMenu, 2);
}

void Esp32CamWifi::setUsernameMode() {
    switch (isUsernameMode) {
        case 0:
            isUsernameMode = 1;

            setParamsMode();
            clearParams();
            if (getParametersCount() > 0) {
                getParameters()[0] = &username_parameter;
            }
            else {
                addParameter(&username_parameter);
            }
            return;

        case 1:
            isUsernameMode = 2;
            username_parameter.setLabel("Username does not exists, insert a registered username:");
            return;
    }
}

void Esp32CamWifi::clearParams() {
    const auto params_size = getParametersCount();
    const auto params = getParameters();
    for (int i = 0; i < params_size; i++) {
        auto * param = reinterpret_cast<WifiManagerParam *>(params[i]);
        param->clearParams();
    }
}
