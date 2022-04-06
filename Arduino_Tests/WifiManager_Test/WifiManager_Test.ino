#include <WiFiManager.h>

#define WM_FIXERASECONFIG
#define WM_ERASE_NVS


WiFiManager wifiManager;

void setup() {
  Serial.begin(115200);
  wifiManager.setDarkMode(true);
  Serial.println("Before autoconnect");
  bool connected = wifiManager.autoConnect("Video-Doorbell");
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
