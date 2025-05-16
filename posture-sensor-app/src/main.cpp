#include <Arduino.h>
#include <SoftwareSerial.h> // Incluimos la librería  SoftwareSerial

// Bluethooth
SoftwareSerial BT(10,11);    // Definimos los pines RX y TX del Arduino conectados al Bluetooth
 
// ============================================================
// Posture
int flexS = A0; // flex sensor is connected with pin A0 of the arduino
int flexBuzzer = 5;
int postureThreshold = 100;
int cycleCounter = 0;
int cycleThreshold = 50; // Number of cycles before the buzzer is activated

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
int sweatS = 2; // sweat sensor is connected with pin A3 of the arduino

// ============================================================
// READINGS
int flexdata = 0;
int pulsedata = 0;
int heightdata = 0;
int sweatdata = 0;

void setup()
{
    BT.begin(9600);
    Serial.begin(9600);
    // Posture
    pinMode(flexS, INPUT);
    pinMode(flexBuzzer, OUTPUT);
    // Height
    pinMode(trigS, OUTPUT);
    pinMode(echoS, INPUT);
    // Sweat
    pinMode(sweatS, INPUT);
}

void loop()
{
    // =======================================================
    // Sensor de postura
    // =======================================================

    flexdata = analogRead(flexS);
    Serial.println("flex value;"
        + String(flexdata) );
    if ( flexdata <= postureThreshold ) {
        // Increment the cycle counter
        cycleCounter++;
        // Check if the cycle counter has reached the threshold
        if ( cycleCounter >= cycleThreshold )
        {
            // Activate the buzzer
            digitalWrite(flexBuzzer, HIGH);
            delay(200); // Keep the buzzer on for 200 ms
            digitalWrite(flexBuzzer, LOW);
        }
    } else {
        // Reset the cycle counter if the flex sensor is not bent
        cycleCounter = 0;
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

    sweatdata = digitalRead(sweatS);
    if ( sweatdata == HIGH ) {
        Serial.println("sweat value;1"); // Sweat detected
    } else {
        Serial.println("sweat value;0"); // No sweat detected
    }

    // DELAY BETWEEN LOOPS
    delay(10);

    // END SENSOR LOOP
}