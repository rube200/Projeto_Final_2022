#define WIFI_RETRY_TIMES 3



//todo remove
#define temp_ssid "HouseOfConas";
#define temp_pass "smellslikepussy";
//todo remove



bool isSsidSetted(wifi_config_st wifi_config) {
  return wifi_config.ssid && strlen(wifi_config.ssid) > 0;
}

bool tryConnectToNetwork() {
  Serial.println("Connect to network requested.");
  wifi_config_st wifi_config = readWifiPreferences();

  if (!isSsidSetted(wifi_config)) {
    Serial.println("Preferences have no ssid.");

    //make it hotspot and request inputs
    wifi_config.ssid = temp_ssid;
    wifi_config.password = temp_pass;

    //todo call ap where
    //startAp()
  }

  return tryConnectToSta(wifi_config);
}
