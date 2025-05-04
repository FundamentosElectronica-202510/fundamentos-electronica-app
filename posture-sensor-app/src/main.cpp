#include <Arduino.h>

int flexs = A0; // flex sensor is connected with pin A0 of the arduino
int flexdata = 0;

void setup()
{
    Serial.begin(9600);
    pinMode(flexs, INPUT);
}

void loop()
{
    flexdata = analogRead(flexs);
    Serial.println("flex value;"
        + String(flexdata) );
    if( flexdata < 220) {
        Serial.println( "[WARNING];"
            + String(flexdata) );
    }
    delay(1000);
}