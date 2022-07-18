#include "Esp32Cam.h"

Esp32Cam espController; // NOLINT(cert-err58-cpp)
void setup() {
    espController.begin();
}

void loop() {
    try {
        espController.loop();
    }
    catch (const std::exception &e) {
        Serial.printf("Exception while writing to tcp.\n%s\n", e.what());
        espDelayUs(50000);//50ms
    }
}

//todo use esp32cam flash to light