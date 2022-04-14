#ifndef ESP32_CAM_ESP32UTILS_H
#define ESP32_CAM_ESP32UTILS_H

#ifndef PACKET_HEADER
#define PACKET_HEADER 5
#endif

#define DEBUG 1
#define ESP_32_CAM_PROJECT 1

enum packetType : char {
    Raw = 0,
    Uuid = 1,
    Image = 2,
    CloseCamera = 3
};

#include <Arduino.h>
#include <cstdint>

static inline void espDelay(uint32_t);

template<typename T>
static inline void espDelay(uint32_t, const T &&blocked);

static bool espTryDelay(uint32_t, uint32_t);

static void *createPacket(void *, size_t, packetType, size_t = PACKET_HEADER, bool shouldFree = true);

static void *espMalloc(size_t);

static void *espRealloc(void *ptr, size_t size);

static inline void espDelay(uint32_t timeoutMs) {
    vTaskDelay((timeoutMs / portTICK_PERIOD_MS));
}

template<typename T>
static inline void espDelay(const uint32_t timeoutMs, const T &&blocked) {
    const auto startMs = millis();
    while (espTryDelay(startMs, timeoutMs) && blocked());
}

static bool espTryDelay(const uint32_t startMs, const uint32_t timeoutMs) {
    const auto timeLeft = millis() - startMs - timeoutMs;
    if (timeLeft >= 0) {
        return true;
    }

    vTaskDelay(std::min(timeLeft, 1ul) / portTICK_PERIOD_MS);
    return false;
}

static void *createPacket(void *data, size_t size, packetType type, size_t headerSize, bool shouldFree) {
    const auto allocSize = size + headerSize;

    char *res;
    if ((res = (char *) malloc(allocSize)) ||
        (res = (char *) heap_caps_malloc(allocSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT))) {

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

    return res;
}

static void *espMalloc(size_t size) {
    auto *res = malloc(size);
    if (res) {
        return res;
    }

    return heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

static void *espRealloc(void *ptr, size_t size) {
    if (!ptr) {
        return espMalloc(size);
    }

    auto *res = realloc(ptr, size);
    if (res) {
        return res;
    }

    return heap_caps_realloc(ptr, size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

#endif
