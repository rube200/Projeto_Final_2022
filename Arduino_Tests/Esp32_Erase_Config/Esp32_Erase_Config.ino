#include <nvs_flash.h>
#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  Serial.println("Erasing Wifi Config...");
  //From github
  WiFi.mode(WIFI_AP_STA); // cannot erase if not in STA mode !
  WiFi.persistent(true);
  bool ret = WiFi.disconnect(true, true);
  delay(500);
  WiFi.persistent(false);
  Serial.print("Wifi erasing result: ");
  Serial.println(ret);
  Serial.println("Initing nvs...");
  esp_err_t err = nvs_flash_init();
  Serial.print("NVS init err: ");
  Serial.println(err);
  Serial.println("Erasing nvs...");
  err = nvs_flash_erase();
  Serial.print("NVS erase err: ");
  Serial.println(err);
  Serial.println("Rebooting in 5s.");
  delay(5000);
  ESP.restart();
}

void loop() {

}
