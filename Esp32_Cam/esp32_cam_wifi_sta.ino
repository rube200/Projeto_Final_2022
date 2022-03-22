#include <WiFi.h>

bool connectToSta(wifi_config_st wifi_config) {
  Serial.println("Enabling STA...");
  if (!WiFi.enableSTA(true)) {
    Serial.println("Fail to start STA.");
    return false;
  }

  Serial.println("Connecting to WiFi...");
  wl_status_t wf_st;
  if (wifi_config.password && strlen(wifi_config.password) > 0)
    wf_st = WiFi.begin(wifi_config.ssid, wifi_config.password);
  else
    wf_st = WiFi.begin(wifi_config.ssid);

  while (wf_st != WL_CONNECTED) {
    Serial.print('.');
    delay(500);
    wf_st = WiFi.status();
  }

  Serial.println();
  Serial.printf("WiFi connected to '%s' with ip '%s'.", wifi_config.ssid, WiFi.localIP().toString());
  Serial.println();

  return true;
}
