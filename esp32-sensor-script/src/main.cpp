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
const int flexBuzzer = 23; // Digital output

const int trigS = 12; // Ultrasonic trigger
const int echoS = 14; // Ultrasonic echo
const int SENSOR_DEFAULT_HEIGHT = 200;

// Thresholds
const int POSTURE_THRESHOLD = 4050;
const int POSTURE_CYCLE_THRESHOLD = 5;

/* --- BPM calculation state --- */
const int PULSE_THRESHOLD = 1200; // tweak if your sensor’s baseline is different
const int HYSTERESIS = 30; // stops double-triggering on noise
const ulong BPM_WINDOW_MS = 10000; // 10-second counting window
bool pulseLow = true; // remembers whether the last sample was “low”
ulong windowStartMs = 0; // start time of the current 10-s window
int beatCount = 0; // pulses detected in the current window

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
    if (flexdata < POSTURE_THRESHOLD) {
        postureCycleCounter++;
        if (postureCycleCounter > POSTURE_CYCLE_THRESHOLD) {
            digitalWrite(flexBuzzer, HIGH);
            delay(50);
            digitalWrite(flexBuzzer, LOW);
            postureCycleCounter = 0;
        }
    } else {
        postureCycleCounter = 0;
    }

    // --- Pulse Sensor (BPM) ---
    pulsedata = analogRead(pulseS);

    /* Rising-edge detection with hysteresis
     *  – “pulseLow” is true when we are below the threshold
     *  – we register a beat only when we cross from low → high
     */
    if (pulseLow && pulsedata > PULSE_THRESHOLD) {
        pulseLow = false; // we are now “high”
        beatCount++; // one more beat in this 10-s window
    } else if (!pulseLow && pulsedata < PULSE_THRESHOLD - HYSTERESIS) {
        pulseLow = true; // reset so we can detect the next beat
    }

    /* Every X s, convert count → BPM, transmit, and restart window */
    ulong now = millis();
    if (now - windowStartMs >= BPM_WINDOW_MS) {
        int bpm = beatCount * (60000 / BPM_WINDOW_MS); // = beatCount × 6
        BT.println("pulse value;" + String(bpm));
        Serial.println("pulse value;" + String(bpm));

        // reset for next window
        beatCount = 0;
        windowStartMs = now;
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

    delay(250);
}
