#ifndef ESP32_CAM_ESP32UTILS_H
#define ESP32_CAM_ESP32UTILS_H

#define DEBUG 1
#define DEBUG_CAMERA DEBUG & 0
#define DEBUG_WIFI DEBUG & 0

#define PACKET_HEADER 5
#define STREAM_TIMEOUT 30500000//30.5s -> Py try to communicate every 10s
#define STREAM_BELL_DURATION 5000000//5s
#define BELL_PRESS_DELAY 1000000//1s

enum packetType : char {
    Uuid = 1,
    Image = 2,
    BellPressed = 3,
    MotionDetected = 4,
    StartStream = 5,
    StopStream = 6
};

#include <cstdint>

static inline void espDelayUs(uint32_t);

template<typename T>
static inline void espDelayUs(uint32_t, const T &&blocked);

static bool espTryDelayUs(uint32_t, uint32_t);

static uint8_t *createPacket(void *, size_t, packetType, size_t = PACKET_HEADER, bool = true);

static uint8_t *espMalloc(size_t);

template<typename T>
static T * castArgSelf(void * arg) {
    return reinterpret_cast<T *>(arg);
}

static inline void espDelayUs(uint32_t timeoutUs) {
    vTaskDelay(timeoutUs * configTICK_RATE_HZ / 1000000);
}

template<typename T>
static inline void espDelayUs(const uint32_t timeoutUs, const T &&blocked) {
    const auto startUs = esp_timer_get_time();
    while (!espTryDelayUs(startUs, timeoutUs) && blocked());
}

static bool espTryDelayUs(const uint32_t startUs, const uint32_t timeoutUs) {
    if (esp_timer_get_time() >= startUs + timeoutUs) {
        return true;
    }

    vTaskDelay(configTICK_RATE_HZ / 1000);
    return false;
}

static uint8_t *createPacket(void *data, size_t size, packetType type, size_t headerSize, bool shouldFree) {
    auto *res = espMalloc(headerSize + size);
    if (!res) {
        return res;
    }

    if (data && size > 0) {
        memcpy(res + headerSize, data, size);
    }

    if (data && shouldFree) {
        free(data);
    }

    res[0] = static_cast<char>(size >> 24);
    res[1] = static_cast<char>(size >> 16);
    res[2] = static_cast<char>(size >> 8);
    res[3] = static_cast<char>(size);
    res[4] = static_cast<char>(type);

    return res;
}

static uint8_t *espMalloc(size_t size) {
    auto *res = (uint8_t *) malloc(size);
    if (res) {
        return res;
    }

    return (uint8_t *) heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

#endif
