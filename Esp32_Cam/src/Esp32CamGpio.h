#ifndef ESP32_CAM_ESP32CAMGPIO_H
#define ESP32_CAM_ESP32CAMGPIO_H

#include <Arduino.h>
#include <driver/gpio.h>
#include "Esp32Utils.h"

#define DEBOUNCE_DELAY 50000//50ms

#define BELL_PIN 14
#define PIR_PIN 15
#define RELAY_PIN 13

class Esp32CamGpio {
public:
    void begin() const;

    void changeRelay(bool);

    bool peekBellState(bool = true);

    bool peekPirState(bool = true);

private:
    static void bellPressed(void *);

    static void movementDetected(void *);

    bool bellState = false;
    bool pirState = false;
    bool relayState = false;
};


#endif //ESP32_CAM_ESP32CAMGPIO_H
