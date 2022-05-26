#include "Esp32CamGpio.h"

void Esp32CamGpio::begin() {
    gpio_config_t io_conf {
        .pin_bit_mask = BELL_PIN_BIT,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };

    //Config bell button and pir sensor using esp system
    //configGpio(&io_conf, BELL_PIN);
    io_conf.pin_bit_mask = PIR_PIN_BIT;
    configGpio(&io_conf, PIR_PIN);
    //Finish bell button and pir sensor config

    //Config relay using esp
    io_conf.pin_bit_mask = RELAY_PIN_BIT;
    io_conf.mode = GPIO_MODE_OUTPUT;
    configGpio(&io_conf, RELAY_PIN);
    //Finish relay config
}

void Esp32CamGpio::configGpio(gpio_config_t * io_conf, gpio_num_t pin) {
    auto err = gpio_config(io_conf);
    if (err != ESP_OK) {
        Serial.printf("Fail to set gpio config - %llu %s %i\n", io_conf->pin_bit_mask, esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    err = gpio_set_level(pin, false);
    if (err != ESP_OK) {
        Serial.printf("Fail to set level to off - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }
}

void Esp32CamGpio::changeRelay(const bool newState) {
    if (relayState == newState) {
        return;
    } else {
        relayState = newState;
    }

#if DEBUG
    Serial.printf("changeRelay %i\n", relayState);
#endif
    const auto pin = static_cast<gpio_num_t>(RELAY_PIN);
    const auto err = gpio_set_level(pin, relayState);
    if (err != ESP_OK) {
        relayState = !newState;
        Serial.printf("Fail to changeRelay(%i) to %d - %s %i\n", pin, newState ? 1 : 0, esp_err_to_name(err), err);
        return;
    }
}

uint32_t bellDebounceTime = 0;
bool Esp32CamGpio::peekBellState() {
    const auto currentTime = esp_timer_get_time();
    if (gpio_get_level(BELL_PIN) && bellDebounceTime < currentTime) {
        bellDebounceTime = currentTime + DEBOUNCE_DELAY;
#if DEBUG
        Serial.println("Bell pressed");
#endif
        return true;
    }

    return false;
}

bool pirLastState = true;//default sensor state if missing
bool Esp32CamGpio::peekPirState() {
    if (gpio_get_level(PIR_PIN)) {
        if (pirLastState) {
            return false;
        }

        pirLastState = true;
#if DEBUG
        Serial.println("Movement detected");
#endif
        return true;
    }

    if (pirLastState) {
        pirLastState = false;
    }

    return false;
}