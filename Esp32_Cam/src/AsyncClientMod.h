#ifndef ESP32_CAM_ASYNCCLIENTMOD_H
#define ESP32_CAM_ASYNCCLIENTMOD_H

#include <Arduino.h>
#include <AsyncTCP.h>
#include <lwip/tcp.h>

enum packetType {
    Raw = 0,
    State = 1,
    Image = 2
};

class AsyncClientMod : public AsyncClient {
public:
    explicit AsyncClientMod(tcp_pcb * = nullptr);
    ~AsyncClientMod();

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