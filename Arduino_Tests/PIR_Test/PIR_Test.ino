#define PIN_PIR 15

void low_pir() {
  Serial.println(millis());
  Serial.println("Low pir detected.");
}

void change_pir() {
  Serial.println(millis());
  Serial.println(digitalRead(PIN_PIR)); 
  Serial.println("Change pir detected.");
}

void rising_pir() {
  Serial.println(millis());
  Serial.println("Rising pir detected.");
}

void falling_pir() {
  Serial.println(millis());
  Serial.println("Falling pir detected.");
}

void high_pir() {
  Serial.println(millis());
  Serial.println("High pir detected.");
}

bool detectInLoop = false;
void setup() {
  Serial.begin(115200);
  Serial.println("Starting...");

  const int pin = digitalPinToInterrupt(PIN_PIR);
  //attachInterrupt(pin, low_pir, LOW);//Trigger when is low
  //attachInterrupt(pin, change_pir, CHANGE);//Trigger when change
  //attachInterrupt(pin, rising_pir, RISING);//Trigger when pass from low to high
  //attachInterrupt(pin, falling_pir, FALLING);//Trigger when pass from high to low
  //attachInterrupt(pin, high_pir, HIGH);//Trigger when is high

  pinMode(PIN_PIR, INPUT);
  digitalWrite(PIN_PIR, LOW);
  delay(50);
}

bool pirState = false;
void loop() {
  if (digitalRead(PIN_PIR)) {
    if (!pirState) {
      Serial.println("MOTION ON");
      pirState = true;
    }
  }
  else if (pirState) {
    Serial.println("MOTION OFF");
    pirState = false;
  }
}
