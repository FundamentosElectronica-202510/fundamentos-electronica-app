#include <Arduino.h>

// ============================================================
// Posture
int flexS = A0; // flex sensor is connected with pin A0 of the arduino
int flexBuzzer = 5;
int postureThreshold = 100;

// ============================================================
// Pulse
int pulseS = A1; // pulse sensor is connected with pin A1 of the arduino

// ============================================================
// Height
int trigS = 9; // ultrasonic sensor trigger pin
int echoS = 10; // ultrasonic sensor echo pin
int const SENSOR_DEFAULT_HEIGHT = 200; // default height of the ultrasonic sensor

// ============================================================
// Sweat
int sweatS = A3; // sweat sensor is connected with pin A3 of the arduino

// ============================================================
// READINGS
int flexdata = 0;
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;

void setup()
{
    Serial.begin(9600);
    pinMode(flexS, INPUT);
    pinMode(flexBuzzer, OUTPUT);
    pinMode(trigS, OUTPUT);
    pinMode(echoS, INPUT);
}

void loop()
{
    // =======================================================
    // Sensor de postura
    // =======================================================

    flexdata = analogRead(flexS);
    Serial.println("flex value;"
        + String(flexdata) );
    if ( flexdata <= postureThreshold )
    {
        digitalWrite(flexBuzzer, HIGH);
        delay(200); // Keep the buzzer on for 200 ms
        digitalWrite(flexBuzzer, LOW);

        Serial.println("Flex sensor is bent");
    }

    // =======================================================
    // Sensor de pulso
    // =======================================================

    pulsedata = analogRead(pulseS);
    Serial.println("pulse value;"
        + String(pulsedata) );

    // =======================================================
    // Sensor de temperatura corporal
    // =======================================================

    digitalWrite(trigS, LOW);
    delayMicroseconds(2);
    digitalWrite(trigS, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigS, LOW);


    const unsigned long duration = pulseIn(echoS, HIGH);

    const float distance = SENSOR_DEFAULT_HEIGHT - ( ( duration * 0.034 ) / 2 );
    Serial.println("height value;"
        + String( distance ) );

    // =======================================================
    // Sensor de sudor
    // =======================================================

    sweatdata = analogRead(sweatS);
    Serial.println("sweat value;"
        + String(sweatdata) );

    // DELAY BETWEEN LOOPS
    delay(10);

    // END SENSOR LOOP
}