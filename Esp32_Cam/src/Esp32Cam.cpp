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
    connectSocket();

    Serial.println("Setup Completed!");
}

bool Esp32Cam::captureCameraAndSend() {
    if (!isReady()) {
        Serial.println("Socket is not ready!");
        return false;
    }

#ifdef DEBUG
    //int64_t start = esp_timer_get_time();
#endif
    if (!isCameraOn && !beginCamera()) {
        Serial.println("Fail to capture camera frame. Camera is off");
        return false;
    }
#ifdef DEBUG
    //Serial.printf("%lli ms to initialize camera.\n", calculateTime(start));
    //start = esp_timer_get_time();
#endif
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return false;
    }

    uint8_t *imgBuf;
    size_t imgLen;
    if (fb->format == PIXFORMAT_JPEG) {
        imgBuf = (uint8_t *) espMalloc(fb->len + PACKET_HEADER);
        imgLen = fb->len;
        memcpy(imgBuf + PACKET_HEADER, fb->buf, imgLen);
        esp_camera_fb_return(fb);
    } else {
        bool converted = frame2jpg(fb, 80, &imgBuf, &imgLen);
        esp_camera_fb_return(fb);
        if (!converted) {
            Serial.println("Fail to convert frame to jpg.");
            return false;
        }

        imgBuf = (uint8_t *) espPacketAlloc(imgBuf, imgLen, PACKET_HEADER);
    }

#ifdef DEBUG
    //Serial.printf("%lli ms to capture and convert.\n", calculateTime(start));
    //start = esp_timer_get_time();
#endif
    imgBuf[0] = static_cast<char>(imgLen >> 24);
    imgBuf[1] = static_cast<char>(imgLen >> 16);
    imgBuf[2] = static_cast<char>(imgLen >> 8);
    imgBuf[3] = static_cast<char>(imgLen);
    imgBuf[4] = static_cast<char>(Image);
    size_t written = espSocket.write(imgBuf, imgLen + PACKET_HEADER);
#ifdef DEBUG
    //Serial.printf("%lli ms to write tcp.\n", calculateTime(start));
#endif
    free(imgBuf);
    if (written != imgLen) {
        Serial.printf("Fail to send img! Sent: %zu of %zu\n", written, imgLen);
        return false;
    }

    return true;
}

void Esp32Cam::connectSocket() {
    Serial.println("Connecting to host...");
    if (!espSocket.connect(REMOTE_HOST, REMOTE_PORT)) {
        Serial.println("Fail to connect to host.");
        restartEsp();
        return;
    }
    Serial.println("Connection requested...");
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

    esp_err_t err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("Fail to start camera error %s", esp_err_to_name(err));
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
        Serial.printf("Fail to stop camera error %s", esp_err_to_name(err));
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