#include <Arduino.h>
#include "BluetoothSerial.h"

// --- NEW: Includes for Gyroscope (MPU-6050) ---
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error "Bluetooth is not enabled in this build. Please enable it in the menuconfig. (make menuconfig)"
#endif

BluetoothSerial BT;
Adafruit_MPU6050 mpu; // NEW: MPU-6050 sensor object

// Pin assignments (GPIO)
// const int flexS = 33; // OLD: This pin is no longer used for posture
const int pulseS = 35; // Analog input (VN) --------------------------------------------------- Sensor de pulso = 35
const int sweatS = 33; // Digital input -------------------------------------------------------- Sensor de sudor = 5
const int flexBuzzer = 17; // Digital output (still used for posture alert) -------------------- Buzzer = 27

const int trigS = 21; // Ultrasonic trigger --------------------------------------------------- Sensor altura TRIGGER = 18
const int echoS = 32; // Ultrasonic echo ------------------------------------------------------ Sensor Altura ECHO = 16
const int SENSOR_DEFAULT_HEIGHT = 178;

const int postureS_SDA = 21; // GY-88 --------------------------------------------------------- Sensor Postura SDA = 32
const int postureS_SCL = 22; // GY-88 --------------------------------------------------------- Sensor Postura SCL = 13

// Thresholds
// const int POSTURE_THRESHOLD = 4050; // OLD: Flex sensor threshold
const int POSTURE_ANGLE_THRESHOLD = 25; // NEW: Angle in degrees (e.g., 25°) for "bad posture"
const int POSTURE_CYCLE_THRESHOLD = 5;

/* --- BPM calculation state --- */
const int PULSE_THRESHOLD = 1800; 
const int HYSTERESIS = 30;
const ulong BPM_WINDOW_MS = 5000; 
bool pulseLow = true; 
ulong windowStartMs = 0; 
int beatCount = 0; 

// int flexdata = 0; // OLD
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;
int postureCycleCounter = 0;
int pulseCycleCounter = 0;

void setup() {
    Serial.begin(115200);
    BT.begin("ESP32BT-NVLPZ");

    // --- NEW: Initialize I2C and MPU-6050 ---
    // Use default ESP32 I2C pins (SDA=21, SCL=22)
    // NEW line in setup()
    if (!Wire.begin(postureS_SDA, postureS_SCL)) {
        Serial.println("Failed to initialize I2C bus");
        while (1); // Stop execution
    }

    if (!mpu.begin()) {
        Serial.println("Failed to find MPU6050 chip");
        BT.println("MPU6050 Not Found");
    }
    Serial.println("MPU6050 Found!");

    // NEW: Set sensor ranges (optional but recommended)
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    // --- End of NEW MPU-6050 setup ---

    // pinMode(flexS, INPUT); // OLD
    pinMode(pulseS, INPUT);
    pinMode(sweatS, INPUT);
    pinMode(flexBuzzer, OUTPUT);
    pinMode(trigS, OUTPUT);
    pinMode(echoS, INPUT);
}

void loop() {
    // --- NEW: Posture Sensor (MPU-6050) ---
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // Calculate Pitch and Roll from accelerometer data
    // These angles represent the sensor's orientation relative to gravity
    float pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / M_PI;
    float roll = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / M_PI;

    // Send posture data over BT and Serial
    BT.println("pitch value;" + String(pitch));
    BT.println("roll value;" + String(roll));
    Serial.println("pitch value;" + String(pitch));
    Serial.println("roll value;" + String(roll));

    // Check for bad posture (e.g., slouching forward/backward)
    // We use abs() to catch tilting too far forward OR backward
    if (abs(pitch) > POSTURE_ANGLE_THRESHOLD) {
        postureCycleCounter++;
        if (postureCycleCounter > POSTURE_CYCLE_THRESHOLD) {
            digitalWrite(flexBuzzer, HIGH);
            delay(50);
            digitalWrite(flexBuzzer, LOW);
            postureCycleCounter = 0; // Reset counter after buzzing
        }
    } else {
        // Posture is good, reset the counter
        postureCycleCounter = 0;
    }
    // --- End of NEW Posture Sensor logic ---


    /* // --- OLD Posture Sensor Logic (Commented out) ---
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
    */


    // --- Pulse Sensor (BPM) ---
    pulsedata = analogRead(pulseS);

    if (pulseLow && pulsedata > PULSE_THRESHOLD) {
        pulseLow = false; 
        beatCount++; 
    } else if (!pulseLow && pulsedata < PULSE_THRESHOLD - HYSTERESIS) {
        pulseLow = true; 
    }

    ulong now = millis();
    if (now - windowStartMs >= BPM_WINDOW_MS) {
        int bpm = beatCount * (60000 / BPM_WINDOW_MS); // = beatCount × 6
        BT.println("pulse value;" + String(bpm));
        Serial.println("pulse value;" + String(bpm));
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
}