#include "AsyncClientMod.h"

const uint32_t delayIntervalMs = 1;
static bool espTryDelay(const uint32_t startMs, const uint32_t timeoutMs) {
    const uint32_t expired = millis() - startMs;
    if (expired >= timeoutMs) {
        return true;
    }

    vTaskDelay((std::min(timeoutMs - expired, delayIntervalMs) / portTICK_PERIOD_MS));
    return false;
}

template<typename T>
static inline void espDelay(const uint32_t timeoutMs, const T &&blocked) {
    const auto startMs = millis();
    while (espTryDelay(startMs, timeoutMs) && blocked());
}

AsyncClientMod::AsyncClientMod(tcp_pcb *pcb) : AsyncClient(pcb), disconnectCb(nullptr), disconnectCbArg(nullptr) {
    onAck([this](...) { turnOffSendWaiting(); });
    onDisconnect([this](void *arg, AsyncClient *) {
        turnOffSendWaiting();

        if (!disconnectCb) {
            return;
        }

        disconnectCb(disconnectCbArg, this);
    });
    onPoll([this](...) { turnOffSendWaiting(); });
}

AsyncClientMod::~AsyncClientMod() {
    dataSource = nullptr;
    dataLen = 0;
    sendWaiting = false;
    written = 0;
    writeStartTime = 0;
}

size_t AsyncClientMod::add(const char * data, size_t size, uint8_t) {
    return writeAll(data, size);
}

void AsyncClientMod::onDisconnectCb(AcConnectHandler cb, void *arg) {
    disconnectCb = std::move(cb);
    disconnectCbArg = arg;
}

size_t AsyncClientMod::write(const char * data) {
    return write(data, strlen(data));
}

size_t AsyncClientMod::write(const char * data, size_t size, uint8_t) {
    return writeAll(data, size);
}

size_t AsyncClientMod::writeAll(const char * data, size_t size, packetType type) {
    if (data == nullptr || size == 0) {
        return 0;
    }

    assert(dataSource == nullptr);
    assert(!sendWaiting);

    dataSource = (int) size + type + data;
    dataLen = size + 8;//4(size) + 4(type)
    Serial.printf("Sending %zu", dataLen);//todo
    Serial.printf("Type %i", type);//todo
    written = 0;
    writeStartTime = millis();

    do {
        if (writeSome()) {
            writeStartTime = millis();
        }

        if (written == dataLen || isTimeout() || isClosed()) {
            dataSource = nullptr;
            dataLen = 0;
            break;
        }

        sendWaiting = true;
        espDelay(_ack_timeout, [this]() { return this->sendWaiting; });
        sendWaiting = false;
    } while (true);

    return written;
}

bool AsyncClientMod::isClosed() {
    if (!_pcb) {
        return true;
    }

    uint8_t st = state();
    return st == CLOSED || st == CLOSE_WAIT || st == CLOSING;
}

bool AsyncClientMod::isTimeout() {
    return millis() - writeStartTime > _ack_timeout;
}

void AsyncClientMod::turnOffSendWaiting() {
    if (!sendWaiting) {
        return;
    }

    sendWaiting = false;
}

bool AsyncClientMod::writeSome() {
    if (!_pcb || !dataSource) {
        return false;
    }

    bool hasWritten = false;
    while (written < dataLen) {
        if (isClosed())
            return false;

        const auto remaining = dataLen - written;
        size_t nextChunkSize = std::min(space(), remaining);
        if (!nextChunkSize)
            break;

        const char * buf = dataSource + written;
        uint8_t flags = 0;
        if (nextChunkSize < remaining) {
            flags |= TCP_WRITE_FLAG_MORE;
        }

        nextChunkSize = AsyncClient::add(buf, nextChunkSize, flags);
        if (!nextChunkSize) {
            break;
        }

        written += nextChunkSize;
        hasWritten = true;
    }

    if (!hasWritten) {
        return false;
    }

    return send();
}