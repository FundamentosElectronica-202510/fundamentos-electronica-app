#include <Arduino.h>

// Use Serial2 for Bluetooth (RX = GPIO16, TX = GPIO17, change if needed)
#define BT_RX 16
#define BT_TX 17
HardwareSerial BT(2); // UART2

// Pin assignments (GPIO)
const int flexS = 36; // Analog input (VP)
const int pulseS = 39; // Analog input (VN)
const int sweatS = 19; // Digital input
const int flexBuzzer = 18; // Digital output

const int trigS = 4; // Ultrasonic trigger
const int echoS = 5; // Ultrasonic echo
const int SENSOR_DEFAULT_HEIGHT = 200;

// Thresholds
int postureThreshold = 100;
int cycleThreshold = 50;

int flexdata = 0;
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;
int cycleCounter = 0;

void setup() {
    Serial.begin(115200);
    BT.begin(9600, SERIAL_8N1, BT_RX, BT_TX); // UART2 with defined RX/TX

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
    Serial.println("flex value;" + String(flexdata));
    if (flexdata <= postureThreshold) {
        cycleCounter++;
        if (cycleCounter >= cycleThreshold) {
            digitalWrite(flexBuzzer, HIGH);
            delay(200);
            digitalWrite(flexBuzzer, LOW);
        }
    } else {
        cycleCounter = 0;
    }

    // --- Pulse Sensor ---
    pulsedata = analogRead(pulseS);
    Serial.println("pulse value;" + String(pulsedata));

    // --- Height Sensor (Ultrasonic) ---
    digitalWrite(trigS, LOW);
    delayMicroseconds(2);
    digitalWrite(trigS, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigS, LOW);

    unsigned long duration = pulseIn(echoS, HIGH, 30000); // 30ms timeout
    float distance = SENSOR_DEFAULT_HEIGHT - ((duration * 0.034) / 2);
    Serial.println("height value;" + String(distance));

    // --- Sweat Sensor ---
    sweatdata = digitalRead(sweatS);
    Serial.println("sweat value;" + String(sweatdata));

    delay(10);
}
