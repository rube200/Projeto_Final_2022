#include "esp_camera.h"

static camera_config_t camera_config;

static bool isCameraOn = false;
static bool startCamera() {
  if (isCameraOn) {
    Serial.println("Camera is already on.");
    return true;
  }

  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("Fail to start camera error 0x%x", err);
    return false;
  }

  Serial.println("Camera started.");
  isCameraOn = true;
  return true;
}

static bool stopCamera() {
  if (!isCameraOn) {
    Serial.println("Camera is already off.");
    return true;
  }


  esp_err_t err = esp_camera_deinit();
  if (err != ESP_OK) {
    Serial.printf("Fail to stop camera error 0x%x", err);
    return false;
  }

  Serial.println("Camera stoped.");
  isCameraOn = false;
  return true;
}

static bool setupCamera() {
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
  camera_config.frame_size = FRAMESIZE_SVGA;
  camera_config.jpeg_quality = 10;
  camera_config.fb_count = 2;

  //this test camera
  return startCamera() && stopCamera();
}


//todo
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

/*
    bool converted = frame2bmp(fb, &buf, &buf_len);
    int res = s->set_res_raw(s, startX, startY, endX, endY, offsetX, offsetY, totalX, totalY, outputX, outputY, scale, binning);
    int res = s->set_pll(s, bypass, mul, sys, root, pre, seld5, pclken, pclk);
    int res = s->get_reg(s, reg, mask);
    int res = s->set_reg(s, reg, mask, val);
    int res = s->set_xclk(s, LEDC_TIMER_0, xclk);
    _timestamp.tv_sec = fb->timestamp.tv_sec;
    _timestamp.tv_usec = fb->timestamp.tv_usec;
*/

static bool captureCamera(captureCameraCb capture_cb) {
  if (!capture_cb) {
    Serial.println("Capture camera callback can not be null.");
    return false;
  }

  if (!isCameraOn && !startCamera()) {
    Serial.println("Fail to capture camera frame. Camera is off");
    return false;
  }

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Fail to capture camera frame. FB is null.");
    return false;
  }

  if (fb->format == PIXFORMAT_JPEG) {
    capture_cb(fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return true;
  }

  uint8_t * img_buf;
  size_t img_len;
  if (!frame2jpg(fb, 80, &img_buf, &img_len)) {
    Serial.println("Fail to convert frame to jpg.");
    esp_camera_fb_return(fb);
    return false;
  }

  capture_cb(img_buf, img_len);
  free(img_buf);
  esp_camera_fb_return(fb);
  return true;
}
