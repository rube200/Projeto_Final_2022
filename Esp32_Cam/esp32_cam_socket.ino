#define REMOTE_HOST "192.168.1.30"
#define REMOTE_PORT 45000

static AsyncClient tcp_client;

static bool setupSocketClient() {
  Serial.println("Connecting to host...");
  if (!tcp_client.connect(REMOTE_HOST, REMOTE_PORT)) {
    Serial.println("Fail to connect socket.");
    return false;
  }

  Serial.println("Connection requested...");
  return true;
}

static bool tcp_events_subscribed = false;
static bool setupTcpEvents(emptyCallback connectedCb) {
  Serial.println("Subscribing tcp events...");
  if (tcp_events_subscribed) {
    Serial.println("Tcp events are already subscribed.");
    return false;
  }

  tcp_client.onConnect(onTcpConnect, (void *)connectedCb);
  tcp_client.onTimeout(onTcpTimeout);
  /*tcp_client.onDisconnect();
    tcp_client.onError();
    tcp_client.onData();
    tcp_client.onPacket();
    ;*/

  Serial.println("Tcp events subscribed.");
  tcp_events_subscribed = true;
  return true;
}

static bool setupSocket(emptyCallback connectedCb) {
  return setupSocketClient() && setupTcpEvents(connectedCb);
}
