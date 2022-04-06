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

    Serial.println("Capturing...");
    if (!espController.captureCameraAndSend()) {
        Serial.println("Camera ERROR");
        delay(200);
    }
    delay(1000);
}
//todo add reconnect if disconnected