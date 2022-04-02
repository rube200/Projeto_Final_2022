#ifndef ASYNCCLIENTMOD_ASYNCCLIENTMOD_H
#define ASYNCCLIENTMOD_ASYNCCLIENTMOD_H

#include <Arduino.h>
#include "AsyncTCP.h"
#include <cassert>
#include <functional>
#include "esp8266-compat.h"

#include <esp_priv.h>
#include <coredecls.h>

extern "C" {
#include "freertos/semphr.h"
#include "lwip/dns.h"
#include "lwip/err.h"
#include "lwip/inet.h"
#include "lwip/opt.h"
#include "lwip/pbuf.h"
#include "lwip/tcp.h"
#include "lwip/tcpip.h"
#include "lwip/priv/tcp_priv.h"
#include "lwip/priv/tcpip_priv.h"
}

#include "esp_task_wdt.h"
#include "IPAddress.h"
#include "sdkconfig.h"

extern esp_err_t _tcp_write(tcp_pcb *, int8_t, const char *, size_t, uint8_t); // NOLINT(bugprone-reserved-identifier)

class __attribute__((unused)) AsyncClientMod : public AsyncClient {
public:
    __attribute__((unused)) size_t write_all(const char * data);
    size_t write_all(const char * data, size_t size);

private:
    bool _is_closed();
    bool _is_timeout();
    bool _write_some();

    const char * _datasource = nullptr;
    size_t _datalen = 0;
    bool _send_waiting = false;
    size_t _written = 0;
    uint32_t _write_start_time = 0;
};

#endif