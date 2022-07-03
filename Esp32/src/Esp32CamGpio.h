#ifndef ESP32_CAM_ESP32CAMGPIO_H
#define ESP32_CAM_ESP32CAMGPIO_H

#include "Esp32Utils.h"

#define DEBOUNCE_DELAY 500000//500ms

#define BELL_PIN gpio_num_t(14)
#define BELL_PIN_BIT BIT14
#define PIR_PIN gpio_num_t(15)
#define PIR_PIN_BIT BIT15
#define RELAY_PIN gpio_num_t(13)
#define RELAY_PIN_BIT BIT13

class Esp32CamGpio {
public:
    static void begin();

    void changeRelay(bool);

    static bool peekBellState();

    static bool peekPirState();

private:
    static void configGpio(gpio_config_t *, gpio_num_t);

    bool relayState = false;
};


#endif //ESP32_CAM_ESP32CAMGPIO_H
