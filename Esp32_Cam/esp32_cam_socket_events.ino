static void onTcpConnect(void * arg, AsyncClient * client) {
  Serial.println("Connected to host.");
  if (!arg) {
    Serial.println("OnTcpConnect do not have args.");
    return;
  }

  emptyCallback callback = (emptyCallback) arg;
  if (!callback) {
    Serial.println("OnTcpConnect do not have a callback.");
    return;
  }

  callback();
}
