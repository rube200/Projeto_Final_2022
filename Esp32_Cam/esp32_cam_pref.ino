#define PROG_NAME "Video-Doorbell"
#define PREF_SSID "WIFI_SSID"
#define PREF_PASS "WIFI_PASSWORD"

wifi_config_st readWifiPreferences() {
  Preferences preferences;
  wifi_config_st wifi_config;

  Serial.println("Starting preferences...");
  if (!preferences.begin(PROG_NAME, false)) {
    Serial.println("Fail to start preferences.");
    return wifi_config;
  }

  Serial.println("Reading preferences...");
  wifi_config.ssid = preferences.getString(PREF_SSID).c_str();
  wifi_config.password = preferences.getString(PREF_PASS).c_str();
  Serial.println("Preferences:");
  Serial.printf("\tSSID: '%s'", wifi_config.ssid);
  Serial.println();
  Serial.printf("\tPassword: '%s'", wifi_config.password);
  Serial.println();

  Serial.println("Closing preferences...");
  preferences.end();
  return wifi_config;
}
