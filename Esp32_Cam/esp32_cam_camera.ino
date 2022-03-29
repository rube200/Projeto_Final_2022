#include "esp_camera.h"

static camera_config_t camera_config;

static void setupCamera() {
  camera_config.ledc_channel = LEDC_CHANNEL_0;
  camera_config.ledc_timer = LEDC_TIMER_0;
  camera_config.pin_d0 = 5;
  camera_config.pin_d1 = 18;
  camera_config.pin_d2 = 19;
  camera_config.pin_d3 = 21;
  camera_config.pin_d4 = 36;
  camera_config.pin_d5 = 39;
  camera_config.pin_d6 = 34;
  camera_config.pin_d7 = 35;
  camera_config.pin_xclk = 0;
  camera_config.pin_pclk = 22;
  camera_config.pin_vsync = 25;
  camera_config.pin_href = 23;
  camera_config.pin_sscb_sda = 26;
  camera_config.pin_sscb_scl = 27;
  camera_config.pin_pwdn = 32;
  camera_config.pin_reset = -1;
  camera_config.xclk_freq_hz = 20000000;
  camera_config.pixel_format = PIXFORMAT_JPEG;
  camera_config.frame_size = FRAMESIZE_UXGA;
  camera_config.jpeg_quality = 10;
  camera_config.fb_count = 2;
}

static bool startCamera() {
  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("Fail to start camera error 0x%x", err);
    return false;
  }

  return true;
}

static void enable_flash(bool enable) {
  /*
    ledc_set_duty(CONFIG_LED_LEDC_SPEED_MODE, CONFIG_LED_LEDC_CHANNEL, CONFIG_LED_MAX_INTENSITY);
    ledc_update_duty(CONFIG_LED_LEDC_SPEED_MODE, CONFIG_LED_LEDC_CHANNEL);
    CONFIG_LED_LEDC_LOW_SPEED_MODE
    LEDC_LOW_SPEED_MODE
    LEDC_HIGH_SPEED_MODE

    vTaskDelay(150 / portTICK_PERIOD_MS); // The LED needs to be turned on ~150ms before the call to esp_camera_fb_get()
  */
}

/*uint8_t * buf = NULL;
    size_t buf_len = 0;
    fb = esp_camera_fb_get();
    bool converted = frame2bmp(fb, &buf, &buf_len);
    free(buf);
        sensor_t *s = esp_camera_sensor_get();
    int res = s->set_res_raw(s, startX, startY, endX, endY, offsetX, offsetY, totalX, totalY, outputX, outputY, scale, binning);
        sensor_t *s = esp_camera_sensor_get();
    int res = s->set_pll(s, bypass, mul, sys, root, pre, seld5, pclken, pclk);

        sensor_t *s = esp_camera_sensor_get();
    int res = s->get_reg(s, reg, mask);
    int res = s->set_reg(s, reg, mask, val);
    int res = s->set_xclk(s, LEDC_TIMER_0, xclk);
            if (fb->format == PIXFORMAT_JPEG)
        {
            fb->len;
            fb->buf
        }
        else
        {
            frame2jpg_cb(fb, 80, jpg_encode_stream, &jchunk)
        }
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
                    _timestamp.tv_sec = fb->timestamp.tv_sec;
            _timestamp.tv_usec = fb->timestamp.tv_usec;
*/

static void captureCamera() {
  sensor_t * sensor = esp_camera_sensor_get();
  if (sensor != NULL) {
    return;
  }

  if (sensor->id.PID == OV3660_PID) {
    sensor->set_vflip(sensor, 1); // flip it back
    sensor->set_brightness(sensor, 1); // up the brightness just a bit
    sensor->set_saturation(sensor, -2); // lower the saturation
  }

  sensor->set_framesize(sensor, FRAMESIZE_QVGA);
  Serial.println(sensor->id.PID);
  Serial.println(OV3660_PID);
  Serial.println("Capture");
  Serial.println("Capture2");
}
