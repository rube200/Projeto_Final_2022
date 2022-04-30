#include "Esp32Cam.h"

#if DEBUG_CAMERA
static int64_t calculateTime(int64_t start) {
    return (esp_timer_get_time() - start) / 1000;
}
#endif

void Esp32Cam::begin() {
    Serial.begin(SERIAL_BAUD);

#if DEBUG
    Serial.setDebugOutput(true);
#endif

    startWifiManager();
    startCamera();
    //startSocket();
    setupPins();

    Serial.println("Setup Completed!");
}

void Esp32Cam::bellPressed(void * arg) {
    const auto self = castArgSelf<Esp32Cam>(arg);
    const auto current = esp_timer_get_time();

    self->bellPressedUntil = current + BELL_PRESS_DELAY;
    self->bellRecordUntil = current + STREAM_BELL_DURATION;
    if (!self->bellNeedSend) {
        self->bellNeedSend = true;
    }
}

void Esp32Cam::setupPins() {
    const auto pin = static_cast<gpio_num_t>(BELL_PIN);
    auto err = gpio_set_intr_type(pin, GPIO_INTR_POSEDGE);
    if (err != ESP_OK) {
        Serial.printf("Fail to set intr type %s %i\n", esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    err = gpio_isr_handler_add(pin, bellPressed, (void *)this);
    if (err != ESP_OK) {
        Serial.printf("Fail to set intr type %s %i\n", esp_err_to_name(err), err);
        restartEsp();
        return;
    }

}

void Esp32Cam::startWifiManager() {
    Serial.println("Starting WiFiManager...");

#if DEBUG_WIFI
    wifiManager.setDebugOutput(true);
#endif

    wifiManager.setDarkMode(true);

    if (EEPROM.begin(64)) {
        const auto ip = EEPROM.readString(0);
        if (ip)
            socket_host_parameter.setValue(ip.c_str(), 50);

        const auto port = String(EEPROM.readUShort(50));
        if (port)
            socket_port_parameter.setValue(port.c_str(), 5);
        EEPROM.end();
    }
    else {
        Serial.println("Fail to begin EEPROM.");
    }

    wifiManager.addParameter(&socket_host_parameter);
    wifiManager.addParameter(&socket_port_parameter);
    wifiManager.setMenu(wifiMenu);

    //fix eeprom save
    if (!wifiManager.getWiFiIsSaved()) {
        const auto ssid = wifiManager.getWiFiSSID().c_str();
        const auto pass = wifiManager.getWiFiPass().c_str();
        saveWifiConfig(ssid, pass);
    }

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

bool isSetupHost;
void Esp32Cam::saveParamsCallback() {
    isSetupHost = true;
    wifiManager.stopConfigPortal();
}

void Esp32Cam::saveWifiConfig(const char * ssid, const char * pass) {
    if(!ssid || *ssid == 0x00 || strlen(ssid) > 32) {
        return;
    }

    if(pass && strlen(pass) > 64) {
        return;
    }

    wifi_config_t conf;
    memset(&conf, 0, sizeof(wifi_config_t));
    strcpy(reinterpret_cast<char*>(conf.sta.ssid), ssid);

    if (strlen(pass) == 64){
        memcpy(reinterpret_cast<char*>(conf.sta.password), pass, 64);
    } else {
        strcpy(reinterpret_cast<char*>(conf.sta.password), pass);
    }

    esp_wifi_set_config(WIFI_IF_STA, &conf);
}

void Esp32Cam::startSocket() {
    wifiManager.setMenu(wifiMenuParam);
    wifiManager.setSaveParamsCallback([this] { saveParamsCallback(); });

    while (!connectSocket()) {
        isSetupHost = false;
        wifiManager.startConfigPortal(ACCESS_POINT_NAME);

        if (!isSetupHost) {
            Serial.println("Exit requested");
            restartEsp();
            return;
        }
    }

    //online save valid connection to host
    if (!EEPROM.begin(64)) {
        Serial.println("Fail to begin EEPROM.");
        return;
    }

    EEPROM.writeString(0, socket_host_parameter.getValue());
    EEPROM.writeUShort(50, atoi(socket_port_parameter.getValue())); // NOLINT(cert-err34-c)
    EEPROM.end();
}

void Esp32Cam::tryConnectSocket() {
    if (connectSocket()) {
        return;
    }

    Serial.println("Fail to connect to host.");
    restartEsp();
}

bool Esp32Cam::connectSocket() {
    Serial.println("Connecting to host...");

    if (!socket.connected() && !socket.connect(socket_host_parameter.getValue(), atoi(socket_port_parameter.getValue()))) { // NOLINT(cert-err34-c)
        return false;
    }

    socket.setNoDelay(true);
    Serial.println("Connected to host!");
    return true;
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

    /*if (!socket.connected()) {
        tryConnectSocket();
        espDelayUs(5000, [this]() { return !socket.connected(); });//wait for connect
        if (!socket.connected()) {
            Esp32Cam::restartEsp();
            return;
        }
    }*/

    const auto start = esp_timer_get_time();
    /*if (socket.available() > 0) {
        const auto bytes = socket.readString();
        processRecvBytes(bytes);
    }*/

    processSensors();

    /*if (shouldSendCamera()) {
        sendCamera();
    }*/

    const auto delay = 50000 + start - esp_timer_get_time();
    if (delay <= 0) {
        return;
    }

    espDelayUs(delay);
}

void Esp32Cam::processRecvBytes(const String &packet) {
    const auto maxLen = packet.length();
    auto offSet = 0;

#pragma clang diagnostic push
#pragma ide diagnostic ignored "EndlessLoop"
    do {
        const auto len = maxLen - offSet;
        if (len < 5) {
#if DEBUG
            Serial.printf("Ignoring packet size %zu - '", len);
            Serial.print(packet);
            Serial.println("'");
#endif
            return;
        }

        const auto dataSize = atoi(packet.substring(offSet, offSet + 4).c_str()); // NOLINT(cert-err34-c)
        offSet += 4;

        const auto packetSize = PACKET_HEADER + dataSize;
        if (len < packetSize) {
#if DEBUG
            Serial.printf("Ignoring packet size unmatch %zu - %d\n", len, packetSize);
#endif
            return;
        }

        const auto type = byte(packet.charAt(offSet++));
        switch (type) {
            case Uuid:
                sendUuid();
                break;

            case StartStream:
                streamUntil = esp_timer_get_time() + STREAM_TIMEOUT;
                break;

            case StopStream:
                streamUntil = 0;
                break;

            default:
#if DEBUG
                Serial.printf("Unknown packet %i\n", type);
#endif
                break;
        }

        offSet += dataSize;
    } while (true);
#pragma clang diagnostic pop
}

void Esp32Cam::processSensors() {
    if (bellNeedSend && sendBellPressed()) {
        bellNeedSend = false;
    }


}

inline bool Esp32Cam::shouldSendCamera() {
    const auto current = esp_timer_get_time();
    if (streamUntil) {
        if (streamUntil >= current) {
            return true;
        }

        streamUntil = 0;
    }

    if (bellRecordUntil) {
        if (bellRecordUntil >= current) {
            return true;
        }

        bellNeedSend = false;
        bellPressedUntil = 0;
        bellRecordUntil = 0;
    }

    return false;
}

bool Esp32Cam::sendCamera() {
    if (!socket.connected()) {
        return false;
    }

#if DEBUG_CAMERA
    auto start = esp_timer_get_time();
#endif
    auto *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return false;
    }

    uint8_t *packet;
    size_t packetLen;
    if (fb->format == PIXFORMAT_JPEG) {
        packet = createPacket(fb->buf, fb->len, Image, PACKET_HEADER, false);
        packetLen = PACKET_HEADER + fb->len;
        esp_camera_fb_return(fb);
    } else if (frame2jpg(fb, 80, &packet, &packetLen)) {
        packet = createPacket(packet, packetLen, Image);
        packetLen += PACKET_HEADER;
        esp_camera_fb_return(fb);
    } else {
        esp_camera_fb_return(fb);
        Serial.println("Fail to convert frame to jpg.");
        return false;
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
        return false;
    }

    return true;
}

bool Esp32Cam::sendBellPressed() {
    if (!socket.connected()) {
        return false;
    }

    auto *packet = createPacket(nullptr, 0, BellPressed);
    const auto written = socket.write(packet, PACKET_HEADER);

    free(packet);
    if (written != PACKET_HEADER) {
        Serial.printf("Fail to send Uuid! Sent: %zu of %d\n", written, PACKET_HEADER);
        return false;
    }

    return true;
}

bool Esp32Cam::sendUuid() {
    if (!socket.connected()) {
        return false;
    }

    auto *mac = (char *) getMacAddress();
    auto *packet = createPacket(mac, 6, Uuid);
    const auto written = socket.write(packet, UUID_SIZE);

    free(packet);
    if (written != UUID_SIZE) {//4 (size) + 1 (type) + 6 (mac)
        Serial.printf("Fail to send Uuid! Sent: %zu of %d\n", written, UUID_SIZE);
        return false;
    }

    return true;
}
