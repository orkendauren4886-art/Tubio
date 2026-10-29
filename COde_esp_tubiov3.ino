#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled!
#endif

BluetoothSerial SerialBT;

const int TRACTOR_PWM_PIN = 16;
const int TRACTOR_DIR_PIN = 17;
const int CARDAN_PWM_PIN = 18;
const int CARDAN_DIR_PIN = 19;
const int CLEANING_PWM_PIN = 21;
const int CLEANING_DIR_PIN = 22;

const int PWM_FREQ = 5000;

const int SPEED_TRACTOR = 102;
const int SPEED_CARDAN = 38;
const int SPEED_CLEANING = 255;

void stopAll();

void setup() {
  Serial.begin(115200);
  SerialBT.begin("Tubio_Robot");

  pinMode(TRACTOR_DIR_PIN, OUTPUT);
  pinMode(CARDAN_DIR_PIN, OUTPUT);
  pinMode(CLEANING_DIR_PIN, OUTPUT);

  ledcAttach(TRACTOR_PWM_PIN, PWM_FREQ, 8);
  ledcAttach(CARDAN_PWM_PIN, PWM_FREQ, 8);
  ledcAttach(CLEANING_PWM_PIN, PWM_FREQ, 8);

  stopAll();
}

void loop() {
  if (SerialBT.available()) {
    char command = SerialBT.read();
    
    switch (command) {
      case 'F':
        digitalWrite(TRACTOR_DIR_PIN, HIGH);
        ledcWrite(TRACTOR_PWM_PIN, SPEED_TRACTOR);
        digitalWrite(CARDAN_DIR_PIN, HIGH);
        ledcWrite(CARDAN_PWM_PIN, SPEED_CARDAN);
        break;
      case 'B':
        digitalWrite(TRACTOR_DIR_PIN, LOW);
        ledcWrite(TRACTOR_PWM_PIN, SPEED_TRACTOR);
        digitalWrite(CARDAN_DIR_PIN, LOW);
        ledcWrite(CARDAN_PWM_PIN, SPEED_CARDAN);
        break;
      case 'L':
        digitalWrite(CARDAN_DIR_PIN, HIGH);
        ledcWrite(CARDAN_PWM_PIN, SPEED_CARDAN);
        break;
      case 'R':
        digitalWrite(CARDAN_DIR_PIN, LOW);
        ledcWrite(CARDAN_PWM_PIN, SPEED_CARDAN);
        break;
      case 'C':
        digitalWrite(CLEANING_DIR_PIN, HIGH);
        ledcWrite(CLEANING_PWM_PIN, SPEED_CLEANING);
        break;
      case 'S':
      default:
        stopAll();
        break;
    }
  }
  delay(20);
}

void stopAll() {
  ledcWrite(TRACTOR_PWM_PIN, 0);
  ledcWrite(CARDAN_PWM_PIN, 0);
  ledcWrite(CLEANING_PWM_PIN, 0);
}