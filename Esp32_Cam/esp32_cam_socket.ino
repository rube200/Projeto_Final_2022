#include <WiFi.h>

#define REMOTE_HOST "192.168.1.50"
#define REMOTE_PORT 45000

WiFiClient socket_client;

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
