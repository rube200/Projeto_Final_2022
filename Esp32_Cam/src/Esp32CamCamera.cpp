#include "Esp32CamCamera.h"

void Esp32CamCamera::begin() {
    Serial.println("Starting Camera...");

    if (isCameraOn) {
        Serial.println("Camera is already on.");
        return;
    }

    const camera_config_t cameraConfig = {
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

    const auto err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("Fail to start camera error %s %i\n", esp_err_to_name(err), err);
        restartEsp();
        return;
    }

    isCameraOn = true;
    Serial.println("Camera started.");
}

//Need to call free
uint8_t *Esp32CamCamera::getCameraFrame(size_t *frame_len) {
    auto *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Fail to capture camera frame. FB is null.");
        return nullptr;
    }

    uint8_t *frame = nullptr;
    if (fb->format == PIXFORMAT_JPEG) {
        frame = espMalloc(fb->len);
        if (!frame) {
            *frame_len = 0;
            esp_camera_fb_return(fb);
            return nullptr;
        }

        memcpy((void *) frame, fb->buf, fb->len);
        *frame_len = fb->len;
        esp_camera_fb_return(fb);
        return frame;
    }

    if (frame2jpg(fb, 80, &frame, frame_len)) {
        esp_camera_fb_return(fb);
        return frame;
    }

    esp_camera_fb_return(fb);
    Serial.println("Fail to convert frame to jpg.");
    return nullptr;
}
