#ifndef ASYNCCLIENTMOD_ASYNCCLIENTMOD_H
#define ASYNCCLIENTMOD_ASYNCCLIENTMOD_H

#include <Arduino.h>
#include <AsyncTCP.h>
#include <lwip/tcp.h>

extern esp_err_t _tcp_write(tcp_pcb *, int8_t, const char *, size_t, uint8_t); // NOLINT(bugprone-reserved-identifier)

class AsyncClientMod : public AsyncClient {
public:
    explicit AsyncClientMod(tcp_pcb * = nullptr);

    void onDisconnectCb(AcConnectHandler, void * = nullptr);

    size_t write_all(const char *);

    size_t write_all(const char *, size_t);

private:
    bool _is_closed();

    bool _is_timeout();

    void _turn_off_send_waiting();

    bool _write_some();

    const char *_datasource = nullptr;
    size_t _datalen = 0;
    bool _send_waiting = false;
    size_t _written = 0;
    uint32_t _write_start_time = 0;

    AcConnectHandler _disconnect_cb;
    void *_disconnect_cb_arg{};
};

#endif