#ifndef ESP32_CAM_ASYNCCLIENTMOD_H
#define ESP32_CAM_ASYNCCLIENTMOD_H

#include <Arduino.h>
#include <AsyncTCP.h>
#include <lwip/tcp.h>

enum packetType : char {
    Raw = 0,
    RequestName = 1,
    Name = 2,
    RequestImage,
    Image = 4,
    CloseCamera = 5
};

class AsyncClientMod : public AsyncClient {
public:
    explicit AsyncClientMod(tcp_pcb * = nullptr);

    ~AsyncClientMod();

    static inline void espDelay(uint32_t timeoutMs){
        vTaskDelay((timeoutMs / portTICK_PERIOD_MS));
    }

    template<typename T>
    static inline void espDelay(const uint32_t timeoutMs, const T &&blocked) {
        const auto startMs = millis();
        while (espTryDelay(startMs, timeoutMs) && blocked());
    }

    static bool espTryDelay(const uint32_t startMs, const uint32_t timeoutMs) {
        const uint32_t expired = millis() - startMs;
        if (expired >= timeoutMs) {
            return true;
        }

        vTaskDelay((std::min(timeoutMs - expired, (uint32_t)5) / portTICK_PERIOD_MS));
        return false;
    }

    static void * espMalloc(size_t size) {
        void * res = malloc(size);
        if (res) {
            return res;
        }
        return heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    }

#pragma clang diagnostic push
#pragma ide diagnostic ignored "HidingNonVirtualFunction"

    size_t add(const char *data, size_t size, uint8_t);

    void onDisconnectCb(AcConnectHandler, void * = nullptr);

    size_t write(const char *);

    size_t write(const char *, size_t, uint8_t = ASYNC_WRITE_FLAG_COPY);

#pragma clang diagnostic pop

    size_t writeAll(const char *, size_t, packetType = Raw);

private:
    bool isClosed();

    bool isTimeout();

    void turnOffSendWaiting();

    bool writeSome();

    const char * dataSource = nullptr;
    size_t dataLen = 0;
    bool sendWaiting = false;
    size_t written = 0;
    uint32_t writeStartTime = 0;

    AcConnectHandler disconnectCb;
    void * disconnectCbArg{};
};

#endif