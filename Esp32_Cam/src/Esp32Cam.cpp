#include "Esp32Cam.h"


#ifdef DEBUG
bool debug = true;
static int64_t calculateTime(int64_t start) {
    return (esp_timer_get_time() - start) / 1000;
}
#else
bool debug = false;
#endif

void Esp32Cam::begin() {
    Serial.begin(SERIAL_BAUD);
    Serial.setDebugOutput(debug);

    startWifiManager();
    startCamera();
    setupSocket();

    Serial.println("Setup Completed!");
}

bool Esp32Cam::captureCameraAndSend() {
    if (!isReady()) {
        Serial.println("Socket is not ready!");
        return false;
    }

#ifdef DEBUG
    auto start = esp_timer_get_time();
#endif
    if (!isCameraOn && !beginCamera()) {
        Serial.println("Fail to capture camera frame. Camera is off");
        return false;
    }
#ifdef DEBUG
    Serial.printf("%lli ms to initialize camera.\n", calculateTime(start));
    start = esp_timer_get_time();
#endif
    auto *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return false;
    }

    char *packet;
    size_t packetLen;
    if (fb->format == PIXFORMAT_JPEG) {
        packet = (char *) createPacket(fb->buf, fb->len, Image, PACKET_HEADER, false);
        packetLen = PACKET_HEADER + fb->len;
        esp_camera_fb_return(fb);
    } else {
        uint8_t *imgBuf;
        size_t imgLen;
        const auto converted = frame2jpg(fb, 80, &imgBuf, &imgLen);
        esp_camera_fb_return(fb);

        if (!converted) {
            Serial.println("Fail to convert frame to jpg.");
            return false;
        }

        packet = (char *) createPacket(imgBuf, imgLen, Image, PACKET_HEADER);
        packetLen = PACKET_HEADER + imgLen;
    }

#ifdef DEBUG
    Serial.printf("%lli ms to capture and convert.\n", calculateTime(start));
    start = esp_timer_get_time();
#endif

    size_t written = espSocket.write(packet, packetLen);
#ifdef DEBUG
    Serial.printf("%lli ms to write tcp.\n", calculateTime(start));
#endif

    free(packet);
    if (written != packetLen) {
        Serial.printf("Fail to send img! Sent: %zu of %zu\n", written, packetLen);
        return false;
    }

    return true;
}

void Esp32Cam::connectSocket() {
    if (espSocket.connect(REMOTE_HOST, REMOTE_PORT)) {
        return;
    }

    Serial.println("Fail to connect to host.");
    restartEsp();
}

void Esp32Cam::processData(void *arg, void *dt, size_t len) {//todo maybe need changes to read buffer
    const auto data = (char *) dt;
    if (len < 5) {
#if DEBUG
        Serial.printf("Ignoring packet size %zu - %s\n", len, data);
#endif
        return;
    }

    const auto msgLen = data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3];
    if (msgLen + PACKET_HEADER != len) {
#if DEBUG
        Serial.printf("Ignoring packet size unmatch %zu - %d\n", len, msgLen + PACKET_HEADER);
#endif
        return;
    }

    auto *self = reinterpret_cast<Esp32Cam *>(arg);
    const auto type = static_cast<packetType>(data[4]);

    switch (type) { // NOLINT(hicpp-multiway-paths-covered)
        case Uuid:
            self->sendUuid();
            break;

        default:
#if DEBUG
            Serial.printf("Unknown packet %i\n", type);
#endif
            break;
    }
}

void Esp32Cam::sendUuid() {
    auto *mac = (char *) getMacAddress();
    auto *packet = (char *) createPacket(mac, 6, Uuid, PACKET_HEADER);
    const auto packetSize = PACKET_HEADER + 6;
    const auto written = espSocket.write(packet, packetSize);

    free(packet);
    if (written != packetSize) {
        Serial.printf("Fail to send img! Sent: %zu of %d\n", written, packetSize);
    }
}

void Esp32Cam::setupSocket() {
    espSocket.onData(processData, this);
    connectSocket();
}

bool Esp32Cam::isDisconnected() {
    return espSocket.isClosed();
}

bool Esp32Cam::isReady() {
    return espSocket.isConnected();
}

void Esp32Cam::restartEsp() {
    Serial.println("Restarting ESP in 3s...");
    delay(3000);
    ESP.restart();
    assert(0);
}

bool Esp32Cam::beginCamera() {
    if (isCameraOn) {
        Serial.println("Camera is already on.");
        return true;
    }

    const auto err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("Fail to start camera error %s %i\n", esp_err_to_name(err), err);
        return false;
    }

    Serial.println("Camera started.");
    isCameraOn = true;
    return true;
}

bool Esp32Cam::endCamera() {
    if (!isCameraOn) {
        Serial.println("Camera is already off.");
        return true;
    }

    const auto err = esp_camera_deinit();
    if (err != ESP_OK) {
        Serial.printf("Fail to stop camera error %s %i\n", esp_err_to_name(err), err);
        return false;
    }

    Serial.println("Camera stopped.");
    isCameraOn = false;
    return true;
}

void Esp32Cam::startCamera() {
    Serial.println("Testing Camera...");

    if (!beginCamera() || !endCamera()) {
        Serial.println("Failed to test camera.");
        restartEsp();
        return;
    }

    Serial.println("Camera is fine.");
}

void *Esp32Cam::getMacAddress() {
    auto *baseMac = espMalloc(6);
    esp_read_mac((uint8_t *) baseMac, ESP_MAC_WIFI_STA);
    return baseMac;
}

void Esp32Cam::startWifiManager() {
    Serial.println("Starting WiFiManager...");

    wifiManager.setDebugOutput(debug);
    wifiManager.setDarkMode(true);
    wifiManager.setMenu(wifiMenu);

    if (!wifiManager.autoConnect(ACCESS_POINT_NAME)) {
        Serial.println("Failed to connect to WiFi.");
        restartEsp();
        return;
    }

    Serial.println("Successfully connected to WiFi.");
}