#include <WiFi.h>

#define AP_SSID "RANDOM";

bool startAP() {
  Serial.println("Enbling AP...");
  if (!WiFi.enableAP(true)) {
    Serial.println("Fail to start AP.");
    return false;
  }

  return true;
}
