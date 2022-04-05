#include "Esp32Cam.h"

Esp32Cam espController; // NOLINT(cert-err58-cpp)
void setup() {
    espController.begin();
}

void loop() {
    if (!espController.isReady()) {
        delay(50);
        return;
    }

    if (!espController.captureCameraAndSend()) {
        Serial.println("camera ERROR");
        delay(200);
    }
    delay(1000);
}