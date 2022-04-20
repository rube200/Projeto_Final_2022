#include "Esp32Cam.h"

#if DEBUG
bool debug = true;
#else
bool debug = false;
#endif

#if DEBUG_CAMERA
static int64_t calculateTime(int64_t start) {
    return (esp_timer_get_time() - start) / 1000;
}
#endif

void Esp32Cam::begin() {
    Serial.begin(SERIAL_BAUD);
    Serial.setDebugOutput(debug);

    startWifiManager();
    startCamera();
    connectSocket();

    Serial.println("Setup Completed!");
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

void Esp32Cam::startCamera() {
    Serial.println("Starting Camera...");

    if (isCameraOn) {
        Serial.println("Camera is already on.");
        return;
    }

    const auto err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("Fail to start camera error %s %i\n", esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    isCameraOn = true;
    Serial.println("Camera started.");
}

void Esp32Cam::connectSocket() {
    Serial.println("Connecting to host...");

    if (!socket.connected() && !socket.connect(REMOTE_HOST, REMOTE_PORT)) {
        Serial.println("Fail to connect to host.");
        restartEsp();
        return;
    }

    socket.setNoDelay(true);
    Serial.println("Connected to host!");
}

void Esp32Cam::loop() {
    if (!WiFi.isConnected()) {
        Serial.println("Wifi not connected! Waiting for auto reconnect");
        espDelayUs(5000, []() { return !WiFi.isConnected(); });//wait for auto reconnect
        if (!WiFi.isConnected()) {
            Esp32Cam::restartEsp();
            return;
        }
    }

    if (!socket.connected()) {
        connectSocket();
        espDelayUs(5000, [this]() { return !socket.connected(); });//wait for connect
        if (!socket.connected()) {
            Esp32Cam::restartEsp();
            return;
        }
    }

    const auto start = esp_timer_get_time();
    if (socket.available() > 0) {
        auto packet = socket.readString();
        processPacket(packet);
    }

    sendCamera();

    const auto delay = 100000 + start - esp_timer_get_time();
    if (delay <= 0) {
        return;
    }

    espDelayUs(delay);
}

void Esp32Cam::processPacket(const String &packet) {
    const auto len = packet.length();
    if (len < 5) {
#if DEBUG
        Serial.printf("Ignoring packet size %zu - '", len);
        Serial.print(packet);
        Serial.println("'");
#endif
        return;
    }

    const auto size = atoi(packet.substring(0, 4).c_str()); // NOLINT(cert-err34-c)
    const auto expectedSize = PACKET_HEADER + size;
    if (len != expectedSize) {
#if DEBUG
        Serial.printf("Ignoring packet size unmatch %zu - %d\n", len, expectedSize);
#endif
        return;
    }

    const auto type = byte(packet.charAt(4));
    switch (type) { // NOLINT(hicpp-multiway-paths-covered)
        case Uuid:
            sendUuid();
            break;

        default:
#if DEBUG
            Serial.printf("Unknown packet %i\n", type);
#endif
            break;
    }
}

void Esp32Cam::sendCamera() {
#if DEBUG_CAMERA
    auto start = esp_timer_get_time();
#endif
    auto *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return;
    }

    uint8_t *packet;
    size_t packetLen;
    if (fb->format == PIXFORMAT_JPEG) {
        packet = createPacket(fb->buf, fb->len, Image, PACKET_HEADER, false);
        packetLen = PACKET_HEADER + fb->len;
        esp_camera_fb_return(fb);
    } else if (frame2jpg(fb, 80, &packet, &packetLen)) {
        packet = createPacket(packet, packetLen, Image, PACKET_HEADER);
        packetLen += PACKET_HEADER;
        esp_camera_fb_return(fb);
    } else {
        esp_camera_fb_return(fb);
        Serial.println("Fail to convert frame to jpg.");
        return;
    }

#if DEBUG_CAMERA
    Serial.printf("%lli ms to capture and convert.\n", calculateTime(start));
    start = esp_timer_get_time();
#endif

    const auto written = socket.write(packet, packetLen);

#if DEBUG_CAMERA
    Serial.printf("%lli ms to write tcp.\n", calculateTime(start));
#endif

    free(packet);
    if (written != packetLen) {
        Serial.printf("Fail to send img! Sent: %zu of %zu\n", written, packetLen);
        return;
    }
}

void Esp32Cam::sendUuid() {
    auto *mac = (char *) getMacAddress();
    auto *packet = createPacket(mac, 6, Uuid, PACKET_HEADER);

    const auto written = socket.write(packet, UUID_SIZE);

    free(packet);
    if (written != UUID_SIZE) {//4 (size) + 1 (type) + 6 (mac)
        Serial.printf("Fail to send Uuid! Sent: %zu of %d\n", written, UUID_SIZE);
    }
}