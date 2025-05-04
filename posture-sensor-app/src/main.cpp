#include <Arduino.h>

int flexs = A0; // flex sensor is connected with pin A0 of the arduino
int flexdata = 0;
int buzzer = 5; // a buzzer is connected with pin 5 of arduino which is the pwm pin. remove if the buzzer is not used

void setup()
{
    Serial.begin(9600);
    pinMode(flexs, INPUT);
    pinMode(buzzer, OUTPUT);
}

void loop()
{
    flexdata = analogRead(flexs);
    Serial.println("flex value;"
        + String(flexdata) );
    if( flexdata < 220) {
        analogWrite(buzzer, 150); // remove if the buzzer is not used
        Serial.println( "[WARNING] Postura incorrecta: "
            + String(flexdata) );
    }
    if( flexdata > 220) {
        analogWrite(buzzer, 0); // remove if the buzzer is not used
    }
    delay(1000);
}