#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#include<ADS1115_WE.h> 
#include<Wire.h>

#define DATA_TYPE_IR 0
#define DATA_TYPE_OTHERS 1
#define DATA_TYPE_STATUS 2
const char *id = "f21mcea2a1";

#define I2C_ADDRESS 0x48
ADS1115_WE adc = ADS1115_WE(I2C_ADDRESS);

#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>
#define DHTPIN D5
#define DHTTYPE DHT11 
DHT_Unified dht(DHTPIN, DHTTYPE);

#define RAW_DATA_LEN 296
#define DHTPIN D6
#define DHTTYPE    DHT11

const uint16_t kIrLed = 2;

// WiFi
const char *ssid = "";
const char *password = "";

// MQTT Broker
const char *mqtt_broker = "broker.emqx.io";
const char *topic = "group17/TVManager/temperature";
const char *mqtt_username = "emqx";
const char *mqtt_password = "public";
const int mqtt_port = 1883;

IRsend irsend(kIrLed);
WiFiClient espClient;
PubSubClient client(espClient);
DHT_Unified dht(DHTPIN, DHTTYPE);

uint32_t delayMS;
float light = 0.0;
float sound = 0.0;
float temperature = 0.0; 

void callback(char *topic, byte *payload, unsigned int length) {
    Serial.print("Message arrived in topic: ");
    Serial.println(topic);
    Serial.print("Message:");
    for (int i = 0; i < length; i++) {
        Serial.print((char) payload[i]);
    }
    Serial.println();
    Serial.println("-----------------------");
}

void setup() {
  irsend.begin();
  Serial.begin(9600);

  Wire.begin();
  if(!adc.init()){
    Serial.println("ADS1115 not connected!");
  }
  adc.setVoltageRange_mV(ADS1115_RANGE_1024);
  adc.setCompareChannels(ADS1115_COMP_0_GND);
  adc.setMeasureMode(ADS1115_CONTINUOUS);

  // Print temperature sensor details.
  sensor_t sensor;
  dht.begin();
  dht.temperature().getSensor(&sensor);
  delayMS = sensor.min_delay / 1000;

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to WiFi!");
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);
  while (!client.connected()) {
      String client_id = "esp8266-client-";
      client_id += String(WiFi.macAddress());
      Serial.printf("The client %s connects to the public mqtt broker ", client_id.c_str());
      if (client.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
        Serial.println("successfully");
      } else {
          Serial.print("failed with state ");
          Serial.println(client.state());
          delay(2000);
      }
  }
  // publish and subscribe
  client.publish(topic, "hello emqx");
  client.subscribe(topic);
}

void loop() {
  delay(500);

  // Get the light intensity from the photoresistor
  light = readChannel(ADS1115_COMP_0_GND);
  light = ((light * 13107)/65535) * 1024;
  Serial.print(light);

  // Get the sound volume from the sound sensor
  sound = readChannel(ADS1115_COMP_1_GND);
  sound = ((sound * 13107)/65535) * 1024;
  Serial.print(sound);

  // Get temperature event and print its value.
  sensors_event_t event;
  dht.temperature().getEvent(&event);
  temperature = event.temperature;
  if (isnan(event.temperature)) {
    Serial.println(F("Error reading temperature!"));
  }
  else {
    Serial.print(temperature);
  }

  StaticJsonDocument<64> status_document;
  status_document["sensor"] = id;
  status_document["packet_type"] = DATA_TYPE_OTHERS;
  status_document["temperature"] = str(temperature);
  status_document["light"] = str(light);
  status_document["sound"] = str(sound);
  char msg_out[64];
  serializeJson(status_document, msg_out);
  client.publish(publish_topic, msg_out);
  client.loop();
}

float readChannel(ADS1115_MUX channel) {
  float voltage = 0.0;
  adc.setCompareChannels(channel);
  voltage = adc.getResult_V(); // alternative: getResult_mV for Millivolt
  return voltage;
}
