#ifndef ESP32_CAM_ESP32CAMCAMERA_H
#define ESP32_CAM_ESP32CAMCAMERA_H

#include <Arduino.h>
#include <esp_camera.h>
#include "Esp32Utils.h"

class Esp32CamCamera {
public:
    void begin();

    //Need to call free
    static uint8_t *getCameraFrame(size_t *);

private:
    bool isCameraOn = false;
};

#endif //ESP32_CAM_ESP32CAMCAMERA_H
