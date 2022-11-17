/*
  Rui Santos
  Complete project details at https://RandomNerdTutorials.com/esp8266-nodemcu-mqtt-publish-bme680-arduino/
  
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files.
  
  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.
*/

#include <ESP8266WiFi.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Ticker.h>
#include <AsyncMqttClient.h>
#include <Wire.h>
#include <SPI.h>
#include <Servo.h>

Servo servo;

#define WIFI_SSID "yor"
#define WIFI_PASSWORD "abhinav123"
#define i2c_address 0x3c
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SH1106G display = Adafruit_SH1106G(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
// Raspberry Pi Mosquitto MQTT Broker
#define MQTT_HOST IPAddress(192, 168, 91, 98)
// For a cloud MQTT broker, type the domain name
//#define MQTT_HOST "example.com"
#define MQTT_PORT 1883

// Temperature MQTT Topics
#define MQTT_PUB_PROXIMITY "esp/hcsr04/distance"

AsyncMqttClient mqttClient;
Ticker mqttReconnectTimer;

WiFiEventHandler wifiConnectHandler;
WiFiEventHandler wifiDisconnectHandler;
Ticker wifiReconnectTimer;

unsigned long previousMillis = 0;   // Stores last time temperature was published
const long interval = 10000;        // Interval at which to publish sensor readings
const int trigPin = 2;  //D4
const int echoPin = 0;  //D3

long duration;
int distance, degrees;
String degreesString;
String disp_message;

void getBME680Readings(){
  Serial.println('Getting readings....');
}

void connectToWifi() {
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void onWifiConnect(const WiFiEventStationModeGotIP& event) {
  Serial.println("Connected to Wi-Fi.");
  connectToMqtt();
}

void onWifiDisconnect(const WiFiEventStationModeDisconnected& event) {
  Serial.println("Disconnected from Wi-Fi.");
  mqttReconnectTimer.detach(); // ensure we don't reconnect to MQTT while reconnecting to Wi-Fi
  wifiReconnectTimer.once(2, connectToWifi);
}

void connectToMqtt() {
  Serial.println("Connecting to MQTT...");
  mqttClient.connect();
}

void onMqttConnect(bool sessionPresent) {
  Serial.println("Connected to MQTT.");
  Serial.print("Session present: ");
  Serial.println(sessionPresent);
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  Serial.println("Disconnected from MQTT.");

  if (WiFi.isConnected()) {
    mqttReconnectTimer.once(2, connectToMqtt);
  }
}

void onMqttSubscribe(uint16_t packetId, uint8_t qos) {
  Serial.println("Subscribe acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
  Serial.print("  qos: ");
  Serial.println(qos);
}

void onMqttUnsubscribe(uint16_t packetId) {
  Serial.println("Unsubscribe acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
}

void onMqttPublish(uint16_t packetId) {
  Serial.print("Publish acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
}

void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total) {
  Serial.println("Publish received.");
  Serial.print("  topic: ");
  Serial.println(topic);

  String strtopic = String(topic);
  
  if(strtopic.equalsIgnoreCase("esp/servo/gate")){
    String message = "";

    for (unsigned int i=0; i< len; i++) {
      message = message + (char)payload[i];
    }  

    Serial.print("Moving servo by: ");
    Serial.print(message);
    Serial.print(" degrees");
    degreesString = message;    
  }

  if(strtopic.equalsIgnoreCase("esp/oled/display")){
    String message = "";

    for(unsigned int i = 0; i < len; i++){
      message = message + (char)payload[i];
    }
    disp_message = message;
  }
}


void setup() {
  Serial.begin(115200);
  Serial.println();

  servo.attach(14);
  servo.write(90);

  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input

  wifiConnectHandler = WiFi.onStationModeGotIP(onWifiConnect);
  wifiDisconnectHandler = WiFi.onStationModeDisconnected(onWifiDisconnect);

  mqttClient.onConnect(onMqttConnect);
  mqttClient.onDisconnect(onMqttDisconnect);
  // mqttClient.onSubscribe(onMqttSubscribe);
  mqttClient.onMessage(onMqttMessage);
  //mqttClient.onUnsubscribe(onMqttUnsubscribe);
  mqttClient.onPublish(onMqttPublish);
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  // If your broker requires authentication (username and password), set them below
  //mqttClient.setCredentials("REPlACE_WITH_YOUR_USER", "REPLACE_WITH_YOUR_PASSWORD");
  connectToWifi();

  delay(1000);
  display.begin(i2c_address, true);
  display.clearDisplay();
  display.display();
}

void loop() {
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(0, 0);
  display.clearDisplay();
  display.print("---Parking System---");
  display.display();
  unsigned long currentMillis = millis();
  // Every X number of seconds (interval = 10 seconds) 
  // it publishes a new MQTT message
  if (currentMillis - previousMillis >= interval) {
    // Save the last time a new reading was published
    previousMillis = currentMillis;
    
    // Clears the trigPin
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);

    // Sets the trigPin on HIGH state for 10 micro seconds
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Reads the echoPin, returns the sound wave travel time in microseconds
    duration = pulseIn(echoPin, HIGH);

    // Calculating the distance
    distance= duration*0.034/2;
    // Prints the distance on the Serial Monitor
    Serial.print("Distance: ");
    Serial.println(distance);
    delay(2000);
    
    // Publish an MQTT message on topic esp/bme680/temperature
    uint16_t packetIdPub1 = mqttClient.publish(MQTT_PUB_PROXIMITY, 1, true, String(distance).c_str());
    Serial.printf("Publishing on topic %s at QoS 1", MQTT_PUB_PROXIMITY);
    Serial.printf("Message: %i \n");
    uint16_t packetIdSub = mqttClient.subscribe("esp/servo/gate", 2);
    uint16_t packetIdSub2 = mqttClient.subscribe("esp/oled/display", 2);
    
    degrees = degreesString.toInt();
    if(disp_message != ""){
      display.println();
      display.println();
      display.print(disp_message);
      display.display();
      if(distance <= 10){
        servo.write(degrees);
        delay(8000);
        servo.write(90);
        degrees = 0;
      }
      delay(6000);      
    }
    disp_message = "";
    degrees = 90;
  }
}