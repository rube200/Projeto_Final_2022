#include "Esp32CamPacket.h"

Esp32CamPacket::Esp32CamPacket(const packetType packet_type, const uint8_t *data, const size_t data_len) {
    type = packet_type;
    this->data_len = data_len;
    expected_len = data_len;

    allocPacket(data_len);
    setData(data);
    toHeader();
}

Esp32CamPacket::~Esp32CamPacket() {
    resetPacket();
}

uint8_t *Esp32CamPacket::packet() const {
    return pkt;
}

size_t Esp32CamPacket::packetLen() const {
    return pkt_len;
}

void Esp32CamPacket::resetPacket() {
    if (pkt) {
        free(pkt);
        pkt = nullptr;
    }

    data_len = 0;
    expected_len = 0;
    pkt_len = 0;
    type = Invalid;
}

uint8_t *Esp32CamPacket::getData() const {
    if (!pkt || pkt_len <= HEADER_SIZE) {
        return nullptr;
    }

    return pkt + HEADER_SIZE;
}

size_t Esp32CamPacket::getDataLen() const {
    return data_len;
}

size_t Esp32CamPacket::getExpectedLen() const {
    return expected_len;
}

packetType Esp32CamPacket::getPacketType() const {
    return type;
}

void Esp32CamPacket::appendData(const uint8_t *dt, const size_t len) {
    if (!dt || !len) {
        return;
    }

    const auto new_data_len = data_len + len;
    if (!pkt || pkt_len < HEADER_SIZE + new_data_len) {
        allocPacket(new_data_len);
    }

    if (!pkt_len) {
        return;
    }

    memcpy(pkt + HEADER_SIZE + data_len, dt, len);
    data_len = new_data_len;
}

void Esp32CamPacket::fromHeader(const uint8_t *header) {
    if (!header) {
        return;
    }

    data_len = expected_len = getIntFromBuf(header);//Data len need to be set for header
    type = static_cast<packetType>(header[4]);
    allocPacket(0);
    toHeader();
    data_len = 0;
}

void Esp32CamPacket::allocPacket(const size_t data_size) {
    const auto len = HEADER_SIZE + data_size;

    pkt = espRealloc(pkt, len);
    if (!pkt) {
        Serial.println("Fail to alloc packet");
        pkt_len = 0;
        return;
    }

    pkt_len = len;
}

void Esp32CamPacket::setData(const uint8_t *data) const {
    if (!data || !data_len) {
        return;
    }

    if (!pkt || pkt_len < HEADER_SIZE + data_len) {
        return;
    }

    memcpy(pkt + HEADER_SIZE, data, data_len);
}

void Esp32CamPacket::toHeader() const {
    if (!pkt || pkt_len < HEADER_SIZE) {
        return;
    }

    pkt[0] = static_cast<char>(data_len >> 24);
    pkt[1] = static_cast<char>(data_len >> 16);
    pkt[2] = static_cast<char>(data_len >> 8);
    pkt[3] = static_cast<char>(data_len);
    pkt[4] = static_cast<char>(type);
}