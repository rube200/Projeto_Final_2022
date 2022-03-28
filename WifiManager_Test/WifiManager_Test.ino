#include <WiFiManager.h>

WiFiManager wifiManager;

void setup() {
  wifiManager.debugPlatformInfo();
  wifiManager.setDarkMode(true);
  Serial.println("Before autoconnect");
  bool connected = wifiManager.autoConnect("AP-NAME");
  if (connected) {
    Serial.println("Connected");
  }
  else {
    Serial.println("Not Connected");
  }
  Serial.println("After autoconnect");
  /* std::vector<const char *> menu = {"wifi","wifinoscan","info","param","close","sep","erase","update","restart","exit"};
  wm.setMenu(menu); // custom menu, pass vector*/
}

void loop() {
  Serial.println("Looping??");
  delay(1000);
}
