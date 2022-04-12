#ifndef ESP32_CAM_TCPSOCKET_H
#define ESP32_CAM_TCPSOCKET_H

#define MAX_TIMEOUT 3000

#include <Arduino.h>
#include <cstdint>
#include "Esp32Utils.h"
#include <lwip/dns.h>
#include <lwip/tcp.h>

class Esp32CamSocket {
public:
    static inline Esp32CamSocket *castSelf(void *arg) {
        return reinterpret_cast<Esp32CamSocket *>(arg);
    }

    __attribute__((unused)) explicit Esp32CamSocket(tcp_pcb * = nullptr);

    ~Esp32CamSocket();

    inline bool operator==(const Esp32CamSocket &other) {
        return selfPcb == other.selfPcb;
    }

    inline bool operator!=(const Esp32CamSocket &other) {
        return selfPcb != other.selfPcb;
    }

    bool connect(const char *, uint16_t);

    bool connectToHost(const IPAddress &, uint16_t);

    err_t close();

    bool isClosed();

    bool isConnected();

    size_t write(const void *, size_t);

private:
    uint16_t connectPort;
    tcp_pcb *selfPcb;

    //Calls for events
    static err_t tcpConnected(void *, tcp_pcb *, err_t);

    static void tcpDnsFound(const char *, const ip_addr_t *, void *);

    static void tcpErr(void *, err_t);

    static err_t tcpRecv(void *, tcp_pcb *, pbuf *, err_t);

    static err_t tcpSent(void *, tcp_pcb *, uint16_t);

    //Write Buffer
    void appendWriteBuffer(const void *data, size_t size);

    void clearWriteBuffer();

    bool sendWaiting = false;
    char *writeBuffer = nullptr;
    size_t writeBufferSize = 0;
};

#endif
