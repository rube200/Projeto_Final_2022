#include <AsyncTCP.h>
#include <WiFiManager.h>

#define ACCESS_POINT_NAME "Video-Doorbell"
#define DEFAULT_TIMEOUT 5000
#define SERIAL_BAUD 115200

/*
  ESP.restart();
  ESP.eraseConfig()
  
  #include <nvs_flash.h>
  nvs_flash_init();
  nvs_flash_erase();
  
*/

void setupSerial() {
  Serial.begin(SERIAL_BAUD);
  Serial.setDebugOutput(true);
}

bool setupWifi() {
  WiFiManager wifiManager;
  
  wifiManager.debugPlatformInfo();
  wifiManager.setDarkMode(true);

  Serial.println("Starting WiFiManager...");
  if (!wifiManager.autoConnect(ACCESS_POINT_NAME)) {
        Serial.println("Failed to connect to WiFi.");
    return false;
    
  }
  
  Serial.println("Successfully connected to WiFi.");
    return true;
}

bool initialized = false;
void setup() {
  setupSerial();
  
  if (!setupWifi()) {
    Serial.println("Restarting ESP...");
    ESP.restart();
    return;
  }

  initialized = true;
}
