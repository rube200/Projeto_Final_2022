bool tryConnectToSta(wifi_config_st wifi_config) {
  if (WiFi.isConnected()) {
    return true;
  }

  Serial.println("Connecting to WiFi...");

  int numOfTries = max(1, WIFI_RETRY_TIMES);//ensure to try connect at least one time
  wl_status_t wf_st;

  for (int i = 0; i < numOfTries; i++) {
    wf_st = WiFi.begin(wifi_config.ssid, wifi_config.password);
    if (WiFi.waitForConnectResult(DEFAULT_TIMEOUT) == WL_CONNECTED) {
      Serial.println();
      Serial.printf("WiFi connected to '%s' with ip '%s'.", wifi_config.ssid, WiFi.localIP().toString());
      Serial.println();
      return true;
    }
  }

  Serial.println();
  Serial.printf("Failed to connect to SSID: %s - Status: %s", wifi_config.ssid, wf_st);
  Serial.println();
  return false;
}
