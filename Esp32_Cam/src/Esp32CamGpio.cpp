#include "Esp32CamGpio.h"

void Esp32CamGpio::begin() const {
    //Config bell button using esp system
    auto pin = static_cast<gpio_num_t>(BELL_PIN);
    auto err = gpio_set_intr_type(pin, GPIO_INTR_POSEDGE);
    if (err != ESP_OK) {
        Serial.printf("Fail to set intr type - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    err = gpio_isr_handler_add(pin, bellPressed, (void *) this);
    if (err != ESP_OK) {
        Serial.printf("Fail to isr handler add - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }
    //Finish bell button config

    //Config pir sensor using esp
    pin = static_cast<gpio_num_t>(PIR_PIN);
    err = gpio_set_intr_type(pin, GPIO_INTR_POSEDGE);
    if (err != ESP_OK) {
        Serial.printf("Fail to set intr type - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    err = gpio_isr_handler_add(pin, movementDetected, (void *) this);
    if (err != ESP_OK) {
        Serial.printf("Fail to isr handler add - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }
    //Finish pir sensor config

    //Config relay using esp
    pin = static_cast<gpio_num_t>(RELAY_PIN);
    err = gpio_set_direction(pin, GPIO_MODE_INPUT_OUTPUT);
    if (err != ESP_OK) {
        Serial.printf("Fail to set direction output - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    err = gpio_set_level(pin, false);
    if (err != ESP_OK) {
        Serial.printf("Fail to set level to off - %i %s %i\n", pin, esp_err_to_name(err), err);
        restartEsp();
        return;
    }
    //Finish relay config
}

void Esp32CamGpio::changeRelay(const bool newState) {
    if (relayState == newState) {
        return;
    } else {
        relayState = newState;
    }

    const auto pin = static_cast<gpio_num_t>(RELAY_PIN);
    const auto err = gpio_set_level(pin, relayState);
    if (err != ESP_OK) {
        relayState = !newState;
        Serial.printf("Fail to changeRelay(%i) to %d - %s %i\n", pin, newState ? 1 : 0, esp_err_to_name(err), err);
        return;
    }
}

bool Esp32CamGpio::peekBellState(const bool clearState) {
    if (!clearState) {
        return bellState;
    }

    const auto state = bellState;
    bellState = false;
    return state;
}

bool Esp32CamGpio::peekPirState(const bool clearState) {
    if (!clearState) {
        return pirState;
    }

    const auto state = pirState;
    pirState = false;
    return state;
}

uint32_t bellDebounceTime = 0;

void Esp32CamGpio::bellPressed(void *arg) {
    const auto currentTime = esp_timer_get_time();
    if (bellDebounceTime >= currentTime) {
        return;
    } else {
        bellDebounceTime = currentTime + DEBOUNCE_DELAY;
    }

    const auto self = castArg<Esp32CamGpio>(arg);
    self->bellState = true;
}

uint32_t pirDebounceTime = 0;

void Esp32CamGpio::movementDetected(void *arg) {
    const auto currentTime = esp_timer_get_time();
    if (pirDebounceTime >= currentTime) {
        return;
    } else {
        pirDebounceTime = currentTime + DEBOUNCE_DELAY;
    }

    const auto self = castArg<Esp32CamGpio>(arg);
    self->pirState = true;
}