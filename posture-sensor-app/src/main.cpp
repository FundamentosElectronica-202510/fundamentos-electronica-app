#include <Arduino.h>

int flexS = A0; // flex sensor is connected with pin A0 of the arduino
int pulseS = A1; // pulse sensor is connected with pin A1 of the arduino
int tempS = A2; // temperature sensor is connected with pin A2 of the arduino
int sweatS = A3; // sweat sensor is connected with pin A3 of the arduino

int flexdata = 0;
int pulsedata = 0;
int tempdata = 0;
int sweatdata = 0;

int flexThreshold = 220; // threshold for flex sensor
int pulseThreshold = 220; // threshold for pulse sensor
int tempThreshold = 220; // threshold for temperature sensor
int sweatThreshold = 220; // threshold for sweat sensor

void setup()
{
    Serial.begin(9600);
    pinMode(flexS, INPUT);
}

void loop()
{
    // =======================================================
    // Sensor de postura
    // =======================================================

    flexdata = analogRead(flexS);
    Serial.println("flex value;"
        + String(flexdata) );

    if( flexdata < flexThreshold ) {
        Serial.println( "[FLEX WARNING];"
            + String(flexdata) );
    }

    // =======================================================
    // Sensor de pulso
    // =======================================================

    pulsedata = analogRead(pulseS);
    Serial.println("pulse value;"
        + String(pulsedata) );

    if ( pulsedata < pulseThreshold ) {
        Serial.println( "[PULSE WARNING];"
            + String(pulsedata) );
    }

    // =======================================================
    // Sensor de temperatura corporal
    // =======================================================

    tempdata = analogRead(tempS);
    Serial.println("temp value;"
        + String(tempdata) );

    if ( tempdata < tempThreshold ) {
        Serial.println( "[TEMP WARNING];"
            + String(tempdata) );
    }

    // =======================================================
    // Sensor de sudor
    // =======================================================

    sweatdata = analogRead(sweatS);
    Serial.println("sweat value;"
        + String(sweatdata) );

    if ( sweatdata < sweatThreshold ) {
        Serial.println( "[SWEAT WARNING];"
            + String(sweatdata) );
    }

    // DELAY BETWEEN LOOPS
    delay(1000);

    // END SENSOR LOOP
}