#ifndef ESP32_CAM_ESP32UTILS_H
#define ESP32_CAM_ESP32UTILS_H

#include <cstdint>
#include <Esp.h>

#define DEBUG 1
#define DEBUG_CAMERA (DEBUG & 0)
#define DEBUG_WIFI (DEBUG & 1)

#define REMOTE_HOST "proj47-ipl-2022.duckdns.org"
#define REMOTE_PORT_STR "2376"
#define REMOTE_PORT 2376

#define MAC_SIZE 6
/*
 * Delays explanation
 * ms -> milliseconds
 * portTICK_PERIOD_MS(const) ->  1000 / configTICK_RATE_HZ
 *
 * vTaskDelay(ms / portTICK_PERIOD_MS)
 * ms / portTICK_PERIOD_MS == ms / (1000 / configTICK_RATE_HZ) ==
 * ms * configTICK_RATE_HZ / 1000
 *
 * μs/us -> microseconds
 * us / 1000 -> ms
 *
 * vTaskDelay(ms / portTICK_PERIOD_MS)
 * ms / portTICK_PERIOD_MS == (us / 1000) / portTICK_PERIOD_MS ==
 * (us / 1000) / (1000 / configTICK_RATE_HZ) ==
 * us * configTICK_RATE_HZ / 1000000
*/

#define microSecondTicks (configTICK_RATE_HZ / 1000000)

static inline void espDelayUs(const uint64_t timeoutUs) {
    vTaskDelay(timeoutUs * microSecondTicks);
}

template<typename T>
static inline bool espDelayUs(const size_t timeoutUs, const T &&blocked, const uint64_t intervalUs = 50) {
    const auto endAtUs = esp_timer_get_time() + timeoutUs;
    const auto intervalTicks = intervalUs * microSecondTicks;

    while (blocked()) {//Means it should continue delaying
        const auto timeLeftUs = endAtUs - esp_timer_get_time();
        if (timeLeftUs <= 0) {//Delay ended
            return false;//timeout reached
        }

        if (timeLeftUs < intervalUs) {//Wait only for left time
            espDelayUs(timeLeftUs);
            return false;//timeout reached
        }

        vTaskDelay(intervalTicks);//Delay interval before next check
    }

    return true;
}


#define MALLOC_CAPS (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)

static inline uint8_t *espMalloc(const size_t size) {
    const auto prt = (uint8_t *) malloc(size);
    if (prt) {
        return prt;
    }

    return (uint8_t *) heap_caps_malloc(size, MALLOC_CAPS);
}

static inline uint8_t *espRealloc(uint8_t *prt, const size_t size) {
    if (!prt) {
        prt = espMalloc(size);
        return prt;
    }

    prt = (uint8_t *) realloc(prt, size);
    if (prt) {
        return prt;
    }

    return (uint8_t *) heap_caps_realloc(prt, size, MALLOC_CAPS);
}

static inline int getIntFromBuf(const uint8_t buf[4]) {
    return buf[0] << 24 | buf[1] << 16 | buf[2] << 8 | buf[3];
}

static inline void restartEsp() {
    Serial.println("Restarting ESP in 3s...");
    vTaskDelay(3 * configTICK_RATE_HZ);
    esp_restart();
    assert(0);
}

static uint8_t *getMac() {
    auto *macPointer = espMalloc(MAC_SIZE);
    if (!macPointer) {
        Serial.println("Fail to malloc mac");
        return nullptr;
    }

    if (esp_read_mac(macPointer, ESP_MAC_WIFI_STA) != ESP_OK) {
        Serial.println("Fail to read mac");
        return nullptr;
    }

    return macPointer;
}
#endif
