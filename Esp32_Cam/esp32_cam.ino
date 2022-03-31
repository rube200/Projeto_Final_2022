#include <AsyncTCP.h>
#include <WiFiManager.h>

#define ACCESS_POINT_NAME "Video-Doorbell"
#define DEFAULT_TIMEOUT 3000//not used yet
#define SERIAL_BAUD 115200

//Need to declared here or in a .h file
typedef void (*captureCameraCb)(uint8_t *, size_t);
typedef void (*emptyCallback)(void);

static void setupSerial() {
  Serial.begin(SERIAL_BAUD);
  Serial.setDebugOutput(true);
}

static bool setupWifi() {
  static WiFiManager wifiManager;

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

static void image_captured_cb(uint8_t * buf, size_t len) {
  Serial.println("Image captured");
}

static bool initialized = false;
static void setupCompleted() {
  /*if (initialized) {
    return;
    }*/

  Serial.println("Setup Completed");
  initialized = true;
}

void setup() {
  setupSerial();

  if (!setupWifi()) {
    Serial.println("Restarting ESP in 3s...");
    delay(3000);
    ESP.restart();
    return;
  }

  setupCamera();

  if (!setupSocket(setupCompleted)) {
    Serial.println("Restarting ESP in 3s...");
    delay(3000);
    ESP.restart();
    return;
  }
}
/*  Serial.println(tcp_client.connecting());
  Serial.println(tcp_client.connected());*/

void loop() {
  delay(1000);
  if (!initialized)
    return;

  return;
}

/*  startCamera();
  Serial.println("Capture Camera");
  captureCamera(image_captured_cb);*/
