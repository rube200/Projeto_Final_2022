#include <Preferences.h>
#include <WiFi.h>

#define SERIAL_BAUD 115200

#define PROG_NAME "Video-Doorbell"
#define PREF_SSID "WIFI_SSID"
#define PREF_PASS "WIFI_PASSWORD"

#define REMOTE_HOST "192.168.1.50"
#define REMOTE_PORT 45000

#define temp_ssid "HERE";
#define temp_pass "HERE";
/*
  #include <nvs_flash.h>
  nvs_flash_erase();
  nvs_flash_init();
  preferences.clear();
  preferences.putString("password", password);
 */

const char* ssid = NULL;
const char* password = NULL;

bool readPreferences() {
    Preferences preferences;

    Serial.println("Starting preferences...");
    if (!preferences.begin(PROG_NAME, false)){
      Serial.println("Fail to start preferences.");
      return false;
    }

    Serial.println("Reading preferences...");
    ssid = preferences.getString(PREF_SSID).c_str();
    password = preferences.getString(PREF_PASS).c_str();
    Serial.println("Preferences:");
    Serial.printf("\tSSID: '%s'", ssid);
    Serial.println();
    Serial.printf("\tPassword: '%s'", password);
    Serial.println();
    
    Serial.println("Closing preferences...");
    preferences.end();
    return true;
}

bool setupAP() {
  Serial.println("Starting AP...");
  if (!WiFi.enableAP(true)) {
    Serial.println("Fail to start AP.");
    return false;
  }

  //todo finish
  return true;
}

bool setupSTA() {//todo adding timeout
  Serial.println("Starting STA...");
  if (!WiFi.enableSTA(true)) {
    Serial.println("Fail to start STA.");
    return false;
  }

  Serial.println("Connecting to WiFi...");
  wl_status_t wf_st;
  if (password && strlen(password))
    wf_st = WiFi.begin(ssid, password);
  else
    wf_st = WiFi.begin(ssid);

  while (wf_st != WL_CONNECTED) {
    Serial.print('.');
    delay(500);
    wf_st = WiFi.status();
  }
  
  Serial.println();
  Serial.printf("WiFi connected to '%s' with ip '%s'.", ssid, WiFi.localIP().toString());
  Serial.println();
  
  return true;
}

bool connectSocket() {
  WiFiClient socket_client;
  Serial.println("Connecting to socket...");
  if (!socket_client.connect(REMOTE_HOST, REMOTE_PORT)) {
    Serial.println("Fail to connect socket.");
    delay(1000);
    return false;
  }
  else {
    Serial.println("connect");
  }
  delay(1000);
  return true;
}

bool initialized = false;

void setup() {
    Serial.begin(SERIAL_BAUD);
    Serial.setDebugOutput(true);

    if (!readPreferences())
      return;
    
    if (!ssid || strlen(ssid) == 0) {
      Serial.println("Preferences have no ssid.");
      //make it hotspot and request inputs
      ssid = temp_ssid;
      password = temp_pass;
    }

    if (!setupSTA())
      return;
      
    initialized = true;
}

void loop() {
  if (!initialized)
    return;

  Serial.println(WiFi.status());
  Serial.println(WiFi.localIP());
  WiFiClient client;
 
    if (!client.connect(REMOTE_HOST, REMOTE_PORT)) {
        Serial.println("Falha de conexao");
        delay(1000);
        return;
    }
 
    Serial.println("Conectado!");
    client.stop();
    delay(1000);
}
