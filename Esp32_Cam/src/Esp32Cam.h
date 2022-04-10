#ifndef ESP32_CAM_ESP32CAM_H
#define ESP32_CAM_ESP32CAM_H

#include <Arduino.h>
#include "AsyncClientMod.h"
#include <esp_camera.h>
#include <WiFiManager.h>

#define ACCESS_POINT_NAME "Video-Doorbell"
#define REMOTE_HOST "192.168.1.73"
#define REMOTE_PORT 45000
#define SERIAL_BAUD 115200

class Esp32Cam {
public:
    void begin();

    bool captureCameraAndSend();

    void connectSocket();

    template<typename T>
    static inline void espDelay(const uint32_t timeoutMs, const T &&blocked) {
        AsyncClientMod::espDelay(timeoutMs, **blocked);
    }

    static inline void espDelay(const uint32_t timeoutMs) {
        AsyncClientMod::espDelay(timeoutMs);
    }

    bool isDisconnected();

    bool isReady();

    static void restartEsp();

protected:
    camera_config_t cameraConfig = {
            .pin_pwdn = 32,
            .pin_reset = -1,
            .pin_xclk = 0,
            .pin_sscb_sda = 26,
            .pin_sscb_scl = 27,
            .pin_d7 = 35,
            .pin_d6 = 34,
            .pin_d5 = 39,
            .pin_d4 = 36,
            .pin_d3 = 21,
            .pin_d2 = 19,
            .pin_d1 = 18,
            .pin_d0 = 5,
            .pin_vsync = 25,
            .pin_href = 23,
            .pin_pclk = 22,

            .xclk_freq_hz = 20000000,
            .ledc_timer = LEDC_TIMER_0,
            .ledc_channel = LEDC_CHANNEL_0,
            .pixel_format = PIXFORMAT_JPEG,
            .frame_size = FRAMESIZE_QVGA,
            .jpeg_quality = 15,
            .fb_count = 2,
    };
    bool isCameraOn{};
    AsyncClientMod tcpClient;
    WiFiManager wifiManager;
    std::vector<const char *> wifiMenu = {"wifi", "param", "exit", "sep", "custom", "exit"};

private:
    bool beginCamera();

    bool endCamera();

    static void onTcpConnect(void *, AsyncClient *);

    static void onTcpDisconnect(void *, AsyncClient *);

    static void onTcpError(void *, AsyncClient *, int8_t);

    static void onTcpPacket(void *, AsyncClient *, pbuf *);

    static void onTcpTimeout(void *, AsyncClient *, uint32_t);

    void startCamera();

    void startSocket();

    void socketSub();

    void startWifiManager();
};

#endif