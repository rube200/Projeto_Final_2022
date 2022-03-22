#include <WiFi.h>

//todo remove
#define temp_ssid "HouseOfConas";
#define temp_pass "smellslikepussy";
//todo remove

bool isValidWifiConfig(wifi_config_st wifi_config) {
  return wifi_config.ssid && strlen(wifi_config.ssid) > 0;
}

bool connectToNetwork() {
  Serial.println("Connect to network requested.");
  wifi_config_st wifi_config = readWifiPreferences();

  if (!isValidWifiConfig(wifi_config)) {
    Serial.println("Preferences have no ssid.");

    //make it hotspot and request inputs
    wifi_config.ssid = temp_ssid;
    wifi_config.password = temp_pass;

    //todo call ap where
    //startAp()
  }

  if (!connectToSta(wifi_config))
    return false;

  return true;
}
