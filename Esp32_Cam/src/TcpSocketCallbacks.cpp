#include "TcpSocket.h"

#pragma clang diagnostic push
#pragma ide diagnostic ignored "ConstantFunctionResult"

err_t Esp32CamSocket::tcpConnected(void *arg, tcp_pcb *pcb, const err_t) {
    castSelf(arg)->selfPcb = pcb;
#if ESP_32_CAM_PROJECT
    Serial.println("Socket ready! Connected to host!");
#endif
    return ERR_OK;
}

void Esp32CamSocket::tcpDnsFound(const char *, const ip_addr_t *ipaddr, void *arg) {
    auto *self = castSelf(arg);
    if (!ipaddr || !ipaddr->u_addr.ip4.addr) {
        self->sendWaiting = false;
        Serial.printf("Dns error: %s\n", esp_err_to_name(-55));
        return;
    }

    self->connectToHost(ipaddr->u_addr.ip4.addr, self->connectPort);
}

void Esp32CamSocket::tcpErr(void *arg, const err_t err) {
    Serial.printf("Tcp error: %s\n", esp_err_to_name(err));

    auto *self = castSelf(arg);
    self->sendWaiting = false;
    if (!self->selfPcb) {
        return;
    }

    tcp_arg(self->selfPcb, nullptr);
    if (self->selfPcb->state == LISTEN) {
        tcp_sent(self->selfPcb, nullptr);
        tcp_recv(self->selfPcb, nullptr);
        tcp_err(self->selfPcb, nullptr);
        tcp_poll(self->selfPcb, nullptr, 0);
    }
    self->selfPcb = nullptr;
#if ESP_32_CAM_PROJECT
    Serial.println("Socket disconnected!");
#endif
}

err_t Esp32CamSocket::tcpRecv(void *arg, tcp_pcb *pcb, pbuf *buf, err_t err) {
    if (err != ERR_OK) {
        Serial.printf("Tcp recv error: %s\n", esp_err_to_name(err));
    }

    auto *self = castSelf(arg);
    if (!buf) {
        self->sendWaiting = false;
        if (!self->selfPcb) {
            return ERR_OK;
        }

        if (self->selfPcb != pcb) {
            Serial.printf("Error pcd-0x%08zx != pcd-0x%08zx\n", (size_t) self->selfPcb, (size_t) pcb);
            return ERR_OK;
        }

        tcp_arg(self->selfPcb, nullptr);
        if (self->selfPcb->state == LISTEN) {
            tcp_err(self->selfPcb, nullptr);
            tcp_poll(self->selfPcb, nullptr, 0);
            tcp_recv(self->selfPcb, nullptr);
            tcp_sent(self->selfPcb, nullptr);
        }

        if (tcp_close(self->selfPcb) != ERR_OK) {
            tcp_abort(self->selfPcb);
        }

        self->selfPcb = nullptr;
#if ESP_32_CAM_PROJECT
        Serial.println("Socket disconnected!");
#endif
        return ERR_OK;
    }

    while (buf != nullptr) {
        pbuf *b = buf;
        buf = b->next;
        b->next = nullptr;

#if DEBUG
        Serial.printf("Received packet size: %i\n", b->len);
#endif

        //data cb b->payload, b->len
        if (pcb) {
            tcp_recved(pcb, b->len);
        }

        pbuf_free(b);
    }

    return ERR_OK;
}

err_t Esp32CamSocket::tcpSent(void *arg, tcp_pcb *, const uint16_t) {
    castSelf(arg)->sendWaiting = false;
    return ERR_OK;
}

#pragma clang diagnostic pop