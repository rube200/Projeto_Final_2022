#include "Esp32CamSocket.h"

void Esp32CamSocket::setHost(const char *host_ip, const uint16_t host_port) {
    host = host_ip;
    port = host_port;
}

void Esp32CamSocket::setUsername(const char *usr) {
    username = usr;
    usernamePortal = false;
}

bool Esp32CamSocket::connectSocket(const bool should_restart_esp) {
    if (connected()) {//connect should check for connected Esp32Cam::loop()
        return true;
    }

    if (!host || !port) {
        Serial.printf("Invalid host or port %s:%hu\n", host, port);
        return false;
    }

    Serial.printf("Connecting to host %s:%hu...\n", host, port);
    for (auto i = 0; i < CONNECT_TRY; i++) {
        if (connect(host, port)) {
            setNoDelay(true);
            Serial.println("Connected to host!");
            return true;
        }
    }

    Serial.println("Fail to connect to host.");
    if (should_restart_esp) {
        restartEsp();
        assert(0);
    }

    return false;
}


void Esp32CamSocket::processSocket() {
    switch (isSocketReady) {
        case Nothing:
            if (sendUuid()) {
                isSocketReady = UuidSent;
            }
            return;

        case ConfigReceived:
            if (!needUsernamePortal() && sendUsername()) {
                isSocketReady = UsernameSent;
            }
            return;
    }

    do {
        const auto av = available();
        if (av <= 0) {
            return;
        }

        auto lenLeft = receiveHeader(av) - readPacket.packetLen();
        if (lenLeft < 0) {//fail at receiveHeader()
            return;
        }

        if (lenLeft == 0) {//we already have all bytes needed
            processPacket();
            readPacket.resetPacket();
            continue;
        }

        const auto toRead = std::min((size_t) av, lenLeft);
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
            continue;
        }

        processPacket();
        readPacket.resetPacket();
    } while (true);
}

size_t Esp32CamSocket::receiveHeader(int av) {
    //If type != Invalid we already set header
    if (readPacket.getPacketType() != Invalid) {
        return HEADER_SIZE + readPacket.getExpectedLen();
    }

    //Header min size
    if (av < 5) {
        return 0;
    }

    uint8_t *header = espMalloc(5);
    if (!header) {
        return 0;
    }

    const auto headerLen = readBytes(header, 5);
    if (headerLen != 5) {
        Serial.printf("FATAL ERROR!! Fail to get header - %d\n", headerLen);
        restartEsp();
        return 0;
    }

    readPacket.fromHeader(header);
    free(header);
    return HEADER_SIZE + readPacket.getExpectedLen();
}

void Esp32CamSocket::processPacket() {
    const auto type = readPacket.getPacketType();
    if (type == Uuid) {
        Serial.printf("Received a uuid packet, something is wrong.");
        return;
    }

    switch (isSocketReady) {
        case Nothing:
        case ConfigReceived:
            Serial.printf("ERROR: This should be unreachable | State(%u): Nothing or ConfigReceived.\n", isSocketReady);
            return;

        case UuidSent:
            if (type == Config) {
                processConfig(readPacket.getData(), readPacket.getDataLen());
                return;
            }

            Serial.printf("Expected to receive a Config packet but receive {%s} instead, ignoring...\n",
                          getTypeToString(type));
            return;

        case UsernameSent:
            if (type == Username) {
                processUsername(readPacket.getData(), readPacket.getDataLen());
                return;
            }

            Serial.printf("Expected to receive a Username packet but receive {%s} instead, ignoring...\n",
                          getTypeToString(type));
            return;
    }

    switch (type) {
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
            Serial.printf("Unknown packet(%s)\n", getTypeToString(type));
            break;
    }
}


bool Esp32CamSocket::isReady() const {
    return isSocketReady == Ready;
}

bool Esp32CamSocket::isRelayRequested() {
    if (!isReady() || !openRelayUntil) {
        return false;
    }

    if (openRelayUntil < esp_timer_get_time()) {
        openRelayUntil = 0;
        return false;
    }

    return true;
}

bool Esp32CamSocket::isStreamRequested() {
    if (!isReady()) {
        return false;
    }

    if (bellSent) {
        bellSent = false;
        return true;
    }

    if (motionSent) {
        motionSent = false;
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

bool Esp32CamSocket::needUsernamePortal() const {
    return usernamePortal;
}


bool Esp32CamSocket::sendUuid() {
    uint8_t *baseMac = espMalloc(MAC_SIZE);
    if (!baseMac) {
        return false;
    }

    esp_read_mac(baseMac, ESP_MAC_WIFI_STA);
    const auto packet = Esp32CamPacket(Uuid, baseMac, MAC_SIZE);
    const auto state = sendPacket(packet, "Uuid");
    free(baseMac);
    return state;
}

bool Esp32CamSocket::sendUsername() {
    const auto packet = Esp32CamPacket(Username, (const uint8_t *) username, strlen(username));
    return sendPacket(packet, "Username");
}

void Esp32CamSocket::processConfig(const uint8_t *data, const size_t data_len) {
    if (!data || data_len < CONFIG_RECV_SIZE) {
        Serial.printf("Invalid config received: %i\n", data_len);
        return;
    }

    const auto sendUsername = (data[0] & 1);
    bellCaptureDuration = std::max(bellCaptureDuration, (uint64_t) getIntFromBuf(data + 1) * 1000);//data + bool(byte)
    motionCaptureDuration = std::max(motionCaptureDuration,
                                     (uint64_t) getIntFromBuf(data + 5) * 1000);//data + bool(byte) + int(4 bytes)
    relayOpenDuration = std::max(relayOpenDuration, (uint64_t) getIntFromBuf(data + 9) *
                                                    1000);//data + bool(byte) + int(4 bytes) + int(4 bytes)

    if (sendUsername) {
        Serial.println("Esp32 not registered yet, requesting username.");
        isSocketReady = ConfigReceived;
        usernamePortal = true;
    } else {
        isSocketReady = Ready;
    }
}

void Esp32CamSocket::processUsername(const uint8_t *data, const size_t data_len) {
    if (!data || data_len < USERNAME_RECV_SIZE) {
        Serial.printf("Invalid username received: %i\n", data_len);
        return;
    }

    if (data[0] & 1) {
        Serial.println("Doorbell registered with success.");
        isSocketReady = Ready;
        return;
    }

    Serial.println("Inserted username is invalid, requesting username again.");
    isSocketReady = ConfigReceived;
    usernamePortal = true;
}

bool Esp32CamSocket::sendPacket(const Esp32CamPacket &packet, const String &name) {
    const auto nm = name.length() ? name.c_str() : getTypeToString(packet.getPacketType());
    const auto len = packet.packetLen();
    if (!len) {
        Serial.printf("Fail to send %s! Invalid packet.\n", nm);
        return false;
    }

    const auto written = write(packet.packet(), len);
    if (len != written) {
        Serial.printf("Fail to send %s! Sent: %zu of %zu\n", nm, len, written);
        return false;
    }

    return true;
}


void Esp32CamSocket::sendBellPressed() {
    if (!isReady()) {
        return;
    }

    const auto packet = Esp32CamPacket(BellPressed, nullptr, 0);
    sendPacket(packet, "BellPressed");
    if (bellCaptureDuration > 0) {
        streamUntil = std::max(streamUntil, (uint64_t) esp_timer_get_time() + bellCaptureDuration);
    } else {
        bellSent = true;
    }
}

void Esp32CamSocket::sendMotionDetected() {
    if (!isReady()) {
        return;
    }

    const auto packet = Esp32CamPacket(MotionDetected, nullptr, 0);
    sendPacket(packet, "MotionDetected");
    if (motionCaptureDuration > 0) {
        streamUntil = std::max(streamUntil, (uint64_t) esp_timer_get_time() + motionCaptureDuration);
    } else {
        motionSent = true;
    }
}

void Esp32CamSocket::sendFrame(uint8_t *image, const size_t image_len) {
    if (!isReady()) {
        return;
    }

    const auto packet = Esp32CamPacket(Image, image, image_len);
    free(image);
    sendPacket(packet, "SendFrame");
}