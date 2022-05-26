#include "Esp32CamWifi.h"

Esp32CamWifi::Esp32CamWifi() {
#if DEBUG_WIFI
    wifiManager.setDebugOutput(true);
#endif
    setDarkMode(true);

    addParameter(&socket_host_parameter);
    addParameter(&socket_port_parameter);

    setNormalMode();
    setSaveParamsCallback([this] {
#pragma clang diagnostic push
#pragma ide diagnostic ignored "UnusedValue"
        isPortalSaved = true;
#pragma clang diagnostic pop
        saveCostumeParameters();
        stopConfigPortal();
    });
}

void Esp32CamWifi::begin() {
    Serial.println("Starting WiFiManager...");

    loadCostumeParameters();

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

    while (!autoConnect(ACCESS_POINT_NAME)) {
        Serial.println("Failed to connect to WiFi.");
    }

    Serial.println("Successfully connected to WiFi.");
}

const char *Esp32CamWifi::getHostParam() const {
    return socket_host_parameter.getValue();
}

uint16_t Esp32CamWifi::getPortParam() const {
    return atoi(socket_port_parameter.getValue()); // NOLINT(cert-err34-c)
}

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

boolean Esp32CamWifi::requestConfig() {
    isPortalSaved = false;
    if (WiFiManager::startConfigPortal(ACCESS_POINT_NAME))
        return true;

    return isPortalSaved;
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

void Esp32CamWifi::setNormalMode() {
    const char *wifiMenu[] = {"wifi", "exit"};
    setMenu(wifiMenu, 2);
}

void Esp32CamWifi::setSocketMode() {
    const char *wifiMenu[] = {"param", "exit"};
    setMenu(wifiMenu, 2);
}