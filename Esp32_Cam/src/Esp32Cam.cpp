#include "Esp32Cam.h"

#if DEBUG_CAMERA
static int64_t calculateTime(int64_t start) {
    return (esp_timer_get_time() - start) / 1000;
}
#endif

void Esp32Cam::begin() {
    Serial.begin(SERIAL_BAUD);
#if DEBUG
    Serial.setDebugOutput(true);
#else
    Serial.setDebugOutput(false);
#endif
    wifi.begin();
    camera.begin();
    startSocket();
    Esp32CamGpio::begin();

    Serial.println("Setup Completed!");
}

void Esp32Cam::startSocket() {
    socket.setHost(wifi.getHostParam(), wifi.getPortParam());

    while (!socket.connectSocket()) {
        if (!wifi.requestSocketConfig()) {
            Serial.println("Exit requested");
            restartEsp();
            return;
        }

        socket.setHost(wifi.getHostParam(), wifi.getPortParam());
    }
}

void Esp32Cam::loop() {
    if (!Esp32CamWifi::isReady()) {
        restartEsp();
        return;
    }

    //connectSocket already check if connected
    if (!socket.connectSocket(true)) {
        return;
    }

    if (socket.needUsernamePortal()) {
        const auto username = wifi.requestUsername();
        if (!username) {
            Serial.println("Exit requested");
            restartEsp();
            return;
        }

        socket.setUsername(username);
        Serial.printf("Sending username %s\n", username);
        espDelayUs(5000);
        return;
    }

    const auto start = esp_timer_get_time();
    socket.processSocket();

    if (!socket.isReady()) {
        espDelayUs(5000);//5ms
        return;
    }

    processGpio();

    if (shouldSendFrame()) {
        sendFrame();
    }

    const auto delay = 50000 + start - esp_timer_get_time();//== 50000us(50ms) - (esp_time - start)
    if (delay <= 0) {
        return;
    }

    espDelayUs(delay);
}

void Esp32Cam::processGpio() {
    if (Esp32CamGpio::peekBellState()) {
        socket.sendBellPressed();
    }

    if (Esp32CamGpio::peekPirState()) {
        socket.sendMotionDetected();
    }

    gpio.changeRelay(socket.isRelayRequested());
}

void Esp32Cam::sendFrame() {
#if DEBUG_CAMERA
    const auto start = esp_timer_get_time();
#endif

    size_t frame_len = 0;
    const auto frame = Esp32CamCamera::getCameraFrame(&frame_len);
    if (frame && frame_len) {
#if DEBUG_CAMERA
        Serial.printf("%lli ms to capture and convert.\n", calculateTime(start));
            start = esp_timer_get_time();
#endif
        socket.sendFrame(frame, frame_len);
#if DEBUG_CAMERA
        Serial.printf("%lli ms to write tcp.\n", calculateTime(start));
#endif
    }
}

bool Esp32Cam::shouldSendFrame() {
    return socket.isStreamRequested();
}