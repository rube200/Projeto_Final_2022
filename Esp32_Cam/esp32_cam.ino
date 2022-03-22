#define SERIAL_BAUD 115200

typedef struct {
  const char * ssid = NULL;
  const char * password = NULL;
} wifi_config_st;


/*
  ESP.restart();
  #include <nvs_flash.h>
  nvs_flash_erase();
  nvs_flash_init();
  preferences.clear();
  preferences.putString("password", password);
*/


bool initialized = false;

void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.setDebugOutput(true);

  initialized = true;
}
