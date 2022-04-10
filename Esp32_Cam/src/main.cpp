#include "Esp32Cam.h"

Esp32Cam espController; // NOLINT(cert-err58-cpp)
void setup() {
    espController.begin();
}

bool isWifiDown = false;
void loop() {
    if (!WiFi.isConnected()) {
        if (isWifiDown) {
            Esp32Cam::restartEsp();
            return;
        }

        isWifiDown = true;
        Serial.println("Wifi not connected! Waiting for auto reconnect");
        Esp32Cam::espDelay(5000, []() { return !WiFi.isConnected(); });//wait for auto reconnect
        return;
    } else if (isWifiDown) {
        isWifiDown = false;
    }

    espController.isDisconnected();
    Esp32Cam::espDelay(50);
    return;
    if (espController.isDisconnected()) {
        espController.connectSocket();
        Esp32Cam::espDelay(50);
        return;
    }

    if (!espController.isReady()) {//connecting or disconnecting
        Esp32Cam::espDelay(5);
        return;
    }

    Serial.println("Capturing...");
    if (!espController.captureCameraAndSend()) {
        Serial.println("Camera ERROR");
    }

    Esp32Cam::espDelay(50);
}