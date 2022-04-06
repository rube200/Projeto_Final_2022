#include "Esp32Cam.h"

static void restartEsp() {
    Serial.println("Restarting ESP in 3s...");
    delay(3000);
    ESP.restart();
    assert(0);
}

void Esp32Cam::begin() {
    Serial.begin(SERIAL_BAUD);
    Serial.setDebugOutput(true);

    startWifiManager();
    startCamera();
    startSocket();

    Serial.println("Setup Completed");
}

bool Esp32Cam::captureCameraAndSend() {
    int64_t st = esp_timer_get_time();
    if (!isReady()) {
        Serial.println("Socket is not ready!");
        return false;
    }

    if (!isCameraOn && !beginCamera()) {
        Serial.println("Fail to capture camera frame. Camera is off");
        return false;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return false;
    }

    uint8_t * imgBuf;
    size_t imgLen;
    if (fb->format == PIXFORMAT_JPEG) {
        imgBuf = (uint8_t *) espMalloc(fb->len);
        imgLen = fb->len;
        memcpy(imgBuf, fb->buf, imgLen);
        esp_camera_fb_return(fb);
    } else {
        bool converted = frame2jpg(fb, 80, &imgBuf, &imgLen);
        esp_camera_fb_return(fb);
        if (!converted) {
            Serial.println("Fail to convert frame to jpg.");
            return false;
        }
    }

    int64_t en = esp_timer_get_time();
    Serial.printf("Capture took %lli\n", ((en - st) / 1000));

    size_t written = tcpClient.writeAll((char *) imgBuf, imgLen, Image);
    free(imgBuf);

    if (written != imgLen) {
        Serial.printf("Fail to send img! Sent: %zu of %zu\n", written, imgLen);
        return false;
    }

    int64_t sd = esp_timer_get_time();
    Serial.printf("Capture and sent took %lli\n", ((sd - st) / 1000));
    return true;
}

bool Esp32Cam::isReady() {
    return WiFi.isConnected() && tcpClient.connected();
}

bool Esp32Cam::beginCamera() {
    if (isCameraOn) {
        Serial.println("Camera is already on.");
        return true;
    }

    esp_err_t err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("Fail to start camera error 0x%x", err);
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

    esp_err_t err = esp_camera_deinit();
    if (err != ESP_OK) {
        Serial.printf("Fail to stop camera error 0x%x", err);
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

#pragma clang diagnostic push
#pragma ide diagnostic ignored "UnreachableCallsOfFunction"
void Esp32Cam::socketSub() {
    Serial.println("Subscribing tcp events...");

    tcpClient.onConnect(onTcpConnect);
    tcpClient.onDisconnectCb(onTcpDisconnect);
    tcpClient.onError(onTcpError);
    tcpClient.onPacket(onTcpPacket);
    tcpClient.onTimeout(onTcpTimeout);

    Serial.println("Tcp events subscribed.");
}
#pragma clang diagnostic pop

void Esp32Cam::startSocket() {
    socketSub();
    Serial.println("Connecting to host...");

    if (!tcpClient.connect(REMOTE_HOST, REMOTE_PORT)) {
        Serial.println("Fail to connect to host.");
        restartEsp();
        return;
    }

    Serial.println("Connection requested...");
}

void Esp32Cam::onTcpConnect(void *, AsyncClient *) {
    Serial.println("Socket ready! Connected to host!");
}

void Esp32Cam::onTcpDisconnect(void *, AsyncClient *) {
    Serial.println("Socket disconnected!");
}

void Esp32Cam::onTcpError(void *, AsyncClient *, int8_t err) {
    Serial.printf("Tcp client error 0x%x\n", err);
}

void Esp32Cam::onTcpPacket(void * arg, AsyncClient * client, pbuf * pb) {
    Serial.println("Socket packet");//TODO
}

void Esp32Cam::onTcpTimeout(void *, AsyncClient *, uint32_t time) {
    Serial.printf("Socket timeout! Time: %u", time);
}

void Esp32Cam::startWifiManager() {
    Serial.println("Starting WiFiManager...");

    wifiManager.debugPlatformInfo();
    wifiManager.setDarkMode(true);
    if (!wifiManager.autoConnect(ACCESS_POINT_NAME)) {
        Serial.println("Failed to connect to WiFi.");
        restartEsp();
        return;
    }

    Serial.println("Successfully connected to WiFi.");
}