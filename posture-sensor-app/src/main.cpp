#include <Arduino.h>

int flexS = A0; // flex sensor is connected with pin A0 of the arduino
int pulseS = A1; // pulse sensor is connected with pin A1 of the arduino
int tempS = A2; // temperature sensor is connected with pin A2 of the arduino
int sweatS = A3; // sweat sensor is connected with pin A3 of the arduino

int flexdata = 0;

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
    if( flexdata < 220) {
        Serial.println( "[WARNING];" // TODO editar mensaje de advertencia para que sea específico al test de postura
            + String(flexdata) );
    }

    // =======================================================
    // Sensor de pulso
    // =======================================================

    // TODO configurar sensor de pulso para enviar advertencias a la app de python

    // =======================================================
    // Sensor de temperatura corporal
    // =======================================================

    // TODO configurar sensor de temperatura corporal para enviar advertencias a la app de python

    // =======================================================
    // Sensor de sudor
    // =======================================================

    // TODO configurar sensor de sudor para enviar a la app de python

    delay(1000);
}