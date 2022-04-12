#include "TcpSocket.h"

__attribute__((unused)) Esp32CamSocket::Esp32CamSocket(tcp_pcb *pcb) : connectPort(0) {
    selfPcb = pcb;
}

Esp32CamSocket::~Esp32CamSocket() {
    if (selfPcb) {
        close();
    }

    clearWriteBuffer();
    sendWaiting = false;
}

bool Esp32CamSocket::connect(const char *hostname, uint16_t port) {
    ip_addr_t addr;
    const auto err = dns_gethostbyname(hostname, &addr, &tcpDnsFound, this);
    if (err == ERR_INPROGRESS) {
        connectPort = port;
        return true;
    }

    if (err == ERR_OK) {
        return connectToHost(IPAddress(addr.u_addr.ip4.addr), port);
    }

    Serial.printf("Tcp dns resolve error: %s\n", esp_err_to_name(err));
    return false;
}

bool Esp32CamSocket::connectToHost(const IPAddress &ipAddr, const uint16_t port) {
    if (selfPcb) {
        Serial.printf("Tcp already connected state: %s\n", tcp_debug_state_str(selfPcb->state));
        return false;
    }

    ip_addr_t addr;
    addr.type = IPADDR_TYPE_V4;
    addr.u_addr.ip4.addr = ipAddr;

    auto *pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb) {
        return false;
    }

    tcp_arg(pcb, this);
    tcp_err(pcb, &tcpErr);
    tcp_recv(pcb, &tcpRecv);
    tcp_sent(pcb, &tcpSent);

    return tcp_connect(pcb, &addr, port, &tcpConnected) != ERR_OK;
}

err_t Esp32CamSocket::close() {
    if (!selfPcb) {
        return ERR_OK;
    }

    tcp_arg(selfPcb, nullptr);
    tcp_err(selfPcb, nullptr);
    tcp_recv(selfPcb, nullptr);
    tcp_sent(selfPcb, nullptr);

    err_t err = ERR_OK;
    if (tcp_close(selfPcb) != ERR_OK) {
        tcp_abort(selfPcb);
        err = ERR_ABRT;
    }

    selfPcb = nullptr;
#if ESP_32_CAM_PROJECT
    Serial.println("Socket disconnected!");
#endif
    return err;
}

bool Esp32CamSocket::isClosed() {
    if (!selfPcb) {
        return true;
    }

    const auto st = selfPcb->state;
    return st == CLOSED || st == CLOSE_WAIT || st == CLOSING;
}

bool Esp32CamSocket::isConnected() {
    if (!selfPcb) {
        return false;
    }

    return selfPcb->state == 4;
}

void Esp32CamSocket::appendWriteBuffer(const void *data, size_t size) {
    if (!data || !size) {
        return;
    }

    size_t oldSize;
    if (writeBuffer) {
        oldSize = writeBufferSize;
        writeBufferSize += size;
        writeBuffer = (char *) espRealloc((void *) writeBuffer, writeBufferSize);
    } else {
        oldSize = 0;
        writeBufferSize = size;
        writeBuffer = (char *) espMalloc(writeBufferSize);
    }

    if (!writeBuffer) {
        return;
    }

    void *prt = (char *) writeBuffer + oldSize;
    memcpy(prt, data, size);
}

void Esp32CamSocket::clearWriteBuffer() {
    if (writeBuffer) {
        free(writeBuffer);
    }

    writeBuffer = nullptr;
    writeBufferSize = 0;
}

size_t Esp32CamSocket::write(const void *data, size_t size) {
    if (!selfPcb || !data || !size) {
        return 0;
    }

    assert(!sendWaiting);
    appendWriteBuffer(data, size);
    if (!writeBuffer) {
        Serial.printf("Fail to allocate buffer to send %zu bytes.\n", writeBufferSize);
        clearWriteBuffer();
        return 0;
    }

    size_t written = 0;
    do {
        auto hasWritten = false;
        while (written < writeBufferSize) {
            if (isClosed()) {
                break;
            }

            const size_t remaining = writeBufferSize - written;
            const size_t nextChunkSize = std::min((size_t) tcp_sndbuf(selfPcb), remaining);
            if (!nextChunkSize) {
                break;
            }

            const void *buf = writeBuffer + written;
            uint8_t flags = 0;
            if (nextChunkSize < remaining) {
                flags |= TCP_WRITE_FLAG_MORE;
            }

            if (tcp_write(selfPcb, buf, nextChunkSize, flags) != ERR_OK) {
                break;
            }

            hasWritten = true;
            written += nextChunkSize;
        }

        if (hasWritten) {
            tcp_output(selfPcb);
        }


        tcp_output(selfPcb);
        if (isClosed() || !writeBuffer || written >= writeBufferSize) {
            break;
        }

        sendWaiting = true;
        espDelay(MAX_TIMEOUT, [this]() { return this->sendWaiting; });
        sendWaiting = false;
    } while (true);

    clearWriteBuffer();
    return written;
}