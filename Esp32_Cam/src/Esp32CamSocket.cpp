#include "Esp32CamSocket.h"

bool Esp32CamSocket::connectSocket(const bool should_restart_esp) {
    if (connected()) {//connect should check for connected Esp32Cam::loop()
        return true;
    }

    if (!host || !port) {
        Serial.printf("Invalid host or port %s:%hu\n", host, port);
        return false;
    }

    Serial.printf("Connecting to host %s:%hu...\n", host, port);
    if (!connect(host, port)) {
        Serial.println("Fail to connect to host.");
        if (should_restart_esp) {
            restartEsp();
            assert(0);
        }

        return false;
    }

    setNoDelay(true);
    Serial.println("Connected to host!");
    return true;
}

bool Esp32CamSocket::isRelayRequested() {
    if (!openRelayUntil) {
        return false;
    }

    if (openRelayUntil < esp_timer_get_time()) {
        openRelayUntil = 0;
        return false;
    }

    return true;
}

bool Esp32CamSocket::isStreamRequested() {
    if (!bellSent) {
        bellSent = false;
        return true;
    }

    if (!streamUntil) {
        return false;
    }

    if (streamUntil < esp_timer_get_time()) {
        streamUntil = 0;
        return false;
    }

    return true;
}

void Esp32CamSocket::precessPacket() {
    const auto type = readPacket.getPacketType();
    switch (type) {
        case HandShake:
            processHandShake(readPacket.getData(), readPacket.getDataLen());
            break;

        case StartStream:
            streamUntil = esp_timer_get_time() + STREAM_TIMEOUT;
            break;

        case StopStream:
            streamUntil = 0;
            break;

        case OpenRelay:
            openRelayUntil = esp_timer_get_time() + relayOpenDuration;
            break;

        default:
#if DEBUG
            Serial.printf("Unknown packet %i\n", type);
#endif
            break;
    }
}

void Esp32CamSocket::processSocket() {
    if (available() <= 0) {
        return;
    }

    do {
        auto lenLeft = receiveHeader() - readPacket.packetLen();
        if (lenLeft < 0) {//fail at receiveHeader()
            return;
        }

        if (lenLeft == 0) {//we already have all bytes needed
            precessPacket();
            readPacket.resetPacket();
            continue;
        }

        const auto toRead = std::min((size_t) available(), lenLeft);
        if (toRead <= 0) {
            return;
        }

        uint8_t *data = espMalloc(toRead);
#pragma clang diagnostic push
#pragma ide diagnostic ignored "DanglingPointer"
        if (!data) {
            return;
        }

        const auto recvLen = readBytes(data, toRead);
        readPacket.appendData(data, recvLen);
        free(data);
#pragma clang diagnostic pop

        if (recvLen < lenLeft) {
            return;
        }
    } while (true);
}

size_t Esp32CamSocket::receiveHeader() {
    //If type != Invalid we already set header
    if (readPacket.getPacketType() != Invalid) {
        return HEADER_SIZE + readPacket.getDataLen();
    }

    //Header min size
    if (available() < 5) {
        return 0;
    }

    uint8_t *data = espMalloc(5);
    if (!data) {
        return 0;
    }

    const auto headerLen = readBytes(data, 5);
    if (headerLen != 5) {
        Serial.printf("FATAL ERROR!! Fail to get header - %d\n", headerLen);
        restartEsp();
        return 0;
    }

    readPacket.fromHeader(data);
    free(data);
    return HEADER_SIZE + readPacket.getDataLen();
}

void Esp32CamSocket::setHost(const char *host_ip, const uint16_t host_port) {
    host = host_ip;
    port = host_port;
}

#define MAC_SIZE 6
#define HANDSHAKE_RECV_SIZE 1

void Esp32CamSocket::processHandShake(const uint8_t *data, const size_t data_len) {
    if (!data || data_len < HANDSHAKE_RECV_SIZE) {
        const auto packet = Esp32CamPacket(Invalid, nullptr, 0);
        sendPacket(packet, "Invalid HandShake data");
        return;
    }

    bellCaptureDuration = std::max(bellCaptureDuration, getIntFromBuf(data));
    relayOpenDuration = std::max(relayOpenDuration, getIntFromBuf(data + 4));//4 size of int

    uint8_t *baseMac = espMalloc(MAC_SIZE);
    if (!baseMac) {
        return;
    }

    esp_read_mac(baseMac, ESP_MAC_WIFI_STA);
    const auto packet = Esp32CamPacket(HandShake, baseMac, MAC_SIZE);
    sendPacket(packet, "HandShake");
    free(baseMac);
}

void Esp32CamSocket::sendBellPressed() {
    const auto packet = Esp32CamPacket(BellPressed, nullptr, 0);
    sendPacket(packet, "BellPressed");
    if (bellCaptureDuration > 0) {
        streamUntil = std::max(streamUntil, (uint64_t) esp_timer_get_time() + bellCaptureDuration);
    } else {
        bellSent = true;
    }
}

void Esp32CamSocket::sendFrame(uint8_t *image, const size_t image_len) {
    const auto packet = Esp32CamPacket(Image, image, image_len);
    free(image);
    sendPacket(packet, "SendFrame");
}

void Esp32CamSocket::sendMotionDetected() {
    const auto packet = Esp32CamPacket(MotionDetected, nullptr, 0);
    sendPacket(packet, "MotionDetected");
}

void Esp32CamSocket::sendPacket(const Esp32CamPacket &packet, const String &name) {
    const auto nm = name.length() ? name.c_str() : getTypeToString(packet.getPacketType());
    const auto len = packet.packetLen();
    if (!len) {
        Serial.printf("Fail to send %s! Invalid packet.\n", nm);
        return;
    }

    const auto written = write(packet.packet(), len);
    if (len != written) {
        Serial.printf("Fail to send %s! Sent: %zu of %zu\n", nm, len, written);
        return;
    }
}