#include <Arduino.h>

int flexS = A0; // flex sensor is connected with pin A0 of the arduino
int pulseS = A1; // pulse sensor is connected with pin A1 of the arduino
int heightS = A2; // temperature sensor is connected with pin A2 of the arduino
int sweatS = A3; // sweat sensor is connected with pin A3 of the arduino

int flexdata = 0;
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;

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

    // =======================================================
    // Sensor de pulso
    // =======================================================

    pulsedata = analogRead(pulseS);
    Serial.println("pulse value;"
        + String(pulsedata) );

    // =======================================================
    // Sensor de temperatura corporal
    // =======================================================

    heightdata = analogRead(heightS);
    Serial.println("height value;"
        + String(heightdata) );

    // =======================================================
    // Sensor de sudor
    // =======================================================

    sweatdata = analogRead(sweatS);
    Serial.println("sweat value;"
        + String(sweatdata) );

    // DELAY BETWEEN LOOPS
    delay(1000);

    // END SENSOR LOOP
}