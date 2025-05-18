#include <Arduino.h>
#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error "Bluetooth is not enabled in this build. Please enable it in the menuconfig. (make menuconfig)"
#endif

BluetoothSerial BT;

// Pin assignments (GPIO)
const int flexS = 33; // Analog input (VP)
const int pulseS = 35; // Analog input (VN)
const int sweatS = 26; // Digital input
const int flexBuzzer = 18; // Digital output

const int trigS = 12; // Ultrasonic trigger
const int echoS = 14; // Ultrasonic echo
const int SENSOR_DEFAULT_HEIGHT = 200;

// Thresholds
int postureThreshold = 100;
int postureCycleThreshold = 50;
int pulseThreshold = 1000;
int pulseCycleThreshold = 10;

int flexdata = 0;
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;
int postureCycleCounter = 0;
int pulseCycleCounter = 0;

void setup() {
    Serial.begin(115200);
    BT.begin("ESP32BT-NVLPZ");

    pinMode(flexS, INPUT);
    pinMode(pulseS, INPUT);
    pinMode(sweatS, INPUT);
    pinMode(flexBuzzer, OUTPUT);
    pinMode(trigS, OUTPUT);
    pinMode(echoS, INPUT);
}

void loop() {
    // --- Posture Sensor ---
    flexdata = analogRead(flexS);
    BT.println("flex value;" + String(flexdata));
    Serial.println("flex value;" + String(flexdata));
    if (flexdata <= postureThreshold) {
        postureCycleThreshold++;
        if (postureCycleThreshold >= postureCycleThreshold) {
            digitalWrite(flexBuzzer, HIGH);
            delay(200);
            digitalWrite(flexBuzzer, LOW);
        }
    } else {
        postureCycleThreshold = 0;
    }

    // --- Pulse Sensor ---
    pulsedata = analogRead(pulseS);

    if (pulsedata > pulseThreshold) {
        pulseCycleCounter++;
        if (pulseCycleCounter >= pulseCycleThreshold) {
            BT.println("pulse value;" + String(1));
            Serial.println("pulse value;" + String(1));
            pulseCycleCounter = 0;
        }
    } else {
        pulseCycleCounter = 0;
    }
    

    // --- Height Sensor (Ultrasonic) ---
    digitalWrite(trigS, LOW);
    delayMicroseconds(2);
    digitalWrite(trigS, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigS, LOW);

    unsigned long duration = pulseIn(echoS, HIGH, 30000); // 30ms timeout
    float distance = SENSOR_DEFAULT_HEIGHT - ((duration * 0.034) / 2);
    BT.println("height value;" + String(distance));
    Serial.println("height value;" + String(distance));

    // --- Sweat Sensor ---
    sweatdata = digitalRead(sweatS);
    BT.println("sweat value;" + String(sweatdata));
    Serial.println("sweat value;" + String(sweatdata));

    delay(10);
}
