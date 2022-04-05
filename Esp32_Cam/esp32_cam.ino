#include "esp_camera.h"

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
