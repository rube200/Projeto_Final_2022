#include "Esp32Cam.h"

Esp32Cam espController; // NOLINT(cert-err58-cpp)
void setup() {
    espController.begin();
}

auto isWifiDown = false;
void loop() {
    if (!WiFi.isConnected()) {
        if (isWifiDown) {
            Esp32Cam::restartEsp();
            return;
        }

        isWifiDown = true;
        Serial.println("Wifi not connected! Waiting for auto reconnect");
        espDelay(5000, []() { return !WiFi.isConnected(); });//wait for auto reconnect
        return;
    } else if (isWifiDown) {
        isWifiDown = false;
    }

    if (espController.isDisconnected()) {
        espController.connectSocket();
        espDelay(100);
        return;
    }

    if (!espController.isReady()) {//connecting or disconnecting
        espDelay(25);
        return;
    }

    if (!espController.captureCameraAndSend()) {
        Serial.println("Camera ERROR");
    }

    espDelay(50);
}