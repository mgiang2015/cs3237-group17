#include <IRrecv.h>
#include <IRsend.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include <ADS1115_WE.h> 
#include <Wire.h>

#define DATA_TYPE_IR 0
#define DATA_TYPE_OTHERS 1
#define DATA_TYPE_STATUS 2

#define STATUS_UNINITIALIZED 0
#define STATUS_IDLE 1
#define STATUS_RECORDING 2

#define I2C_ADDRESS 0x48
ADS1115_WE adc = ADS1115_WE(I2C_ADDRESS);

#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>
#define DHTPIN D5
#define DHTTYPE DHT11

#define RAW_DATA_LEN 296
#define DHTPIN D6
#define DHTTYPE DHT11

const char *id = "f21mcea2a1";

// WiFi
const char *ssid = "Wifi1";
const char *password = "12345678";

// MQTT Broker
const char *mqtt_broker = "broker.emqx.io";
const char *subscribe_topic = "group17/command";
const char *publish_topic = "group17/sensors";
const char *mqtt_username = "emqx";
const char *mqtt_password = "public";
const int mqtt_port = 1883;

const uint16_t IRLed = 2;
const uint16_t IRReceiver = 5;
IRsend irsend(IRLed);
IRrecv irrecv(IRReceiver, 500);
const int PACKET_SIZE = 10;
const size_t CAPACITY = JSON_ARRAY_SIZE(PACKET_SIZE);

WiFiClient espClient;
PubSubClient client(espClient);
DHT_Unified dht(DHTPIN, DHTTYPE);

volatile bool isInitialized = false;

uint16_t *rawDataOn = (uint16_t *)malloc(500 * sizeof(uint16_t));
volatile bool isRawDataOnReceived = false;
int receivedRawDataOnIdx = 0;
int expectedRawDataOnBytes = 0;

uint16_t *rawDataOff = (uint16_t *)malloc(500 * sizeof(uint16_t));
volatile bool isRawDataOffReceived = false;
int receivedRawDataOffIdx = 0;
int expectedRawDataOffBytes = 0;

volatile int currentState;
volatile int previousState;

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
  DynamicJsonDocument rx_document(2048);
  deserializeJson(rx_document, payload);
  const char* targetSensor = rx_document["sensor"];
  if (strcmp(targetSensor, id) == 0) {
    Serial.println("Message received is intended for device");
    const char* cmd = rx_document["command"];
    DynamicJsonDocument tx_document(2048);
    if (strcmp(cmd, "record") == 0) {
      Serial.println("Command RECORD received");
      previousState = currentState;
      currentState = STATUS_RECORDING;
      notify_status();
      decode_results *result = new decode_results;
      DynamicJsonDocument tx_document(6000);
      DynamicJsonDocument json_document(6000);
      JsonArray arr = json_document.to<JsonArray>();
      
      irrecv.enableIRIn();
      while (!irrecv.decode(result)) {
        Serial.println("Waiting for IR data...");
        yield();
      }
      
      int i = 1;
      int currentPacket = 0;
      int remainingData = 0;
      while (i < result->rawlen) {
        int sizeToProcess;
        tx_document["sensor"] = id;
        tx_document["packet_type"] = DATA_TYPE_IR;
        tx_document["ir_raw_length"] = result->rawlen;
        remainingData = result->rawlen - i;
        if (remainingData >= PACKET_SIZE) {
          sizeToProcess = PACKET_SIZE;
        } else {
          sizeToProcess = remainingData;
        }
        for (int n = i; n < i + sizeToProcess; n++) {
          arr.add(result->rawbuf[n] * 2);
          yield();
        }
        i += sizeToProcess;
        currentPacket += 1;
        if (i == result->rawlen) {
           Serial.println("Reached the end. Appending 1000");
           arr.add(1000);
        }
        tx_document["packet_num"] = currentPacket;
        tx_document["ir_raw_data"] = arr;
        char msg_out[256];
        serializeJson(tx_document, msg_out);
        client.publish(publish_topic, msg_out);
        arr.clear();
        yield();
      }
      irrecv.disableIRIn();
      currentState = previousState;
      notify_status();
      Serial.println("Command RECORD completed");
    } else if (strcmp(cmd, "store_ir_on") == 0) {
      Serial.println("Command STORE IR ON received");
      expectedRawDataOnBytes = rx_document["ir_raw_length"];
      StaticJsonDocument<200> json_document;
      JsonArray array = json_document.as<JsonArray>();
      array = rx_document["ir_raw_data"];
      for (JsonVariant v : array) {
        Serial.print(v.as<int>());
        rawDataOn[receivedRawDataOnIdx] = v.as<int>();
        receivedRawDataOnIdx++;
      }
      Serial.println(receivedRawDataOnIdx);
      Serial.println(expectedRawDataOnBytes);
      if (receivedRawDataOnIdx == expectedRawDataOnBytes) {
        Serial.println("Received complete raw data on");
        isRawDataOnReceived = true;
        verify_initialization();
      }
      Serial.println("Command STORE IR ON completed");
    } else if (strcmp(cmd, "store_ir_off") == 0) {
      Serial.println("Command STORE IR OFF received");
      expectedRawDataOffBytes = rx_document["ir_raw_length"];
      StaticJsonDocument<200> json_document;
      JsonArray array = json_document.as<JsonArray>();
      array = rx_document["ir_raw_data"];
      for (JsonVariant v : array) {
        rawDataOff[receivedRawDataOffIdx] = v.as<int>();
        receivedRawDataOffIdx++;
      }
      
      if (receivedRawDataOffIdx == expectedRawDataOffBytes) {
        Serial.println(receivedRawDataOffIdx);
        Serial.println(expectedRawDataOffBytes);
        Serial.println("Received complete raw data off");
        isRawDataOffReceived = true;
        verify_initialization();
      }
      Serial.println("Command STORE IR OFF completed");
    } else if (strcmp(cmd, "on") == 0) {
      Serial.println("Command TURN ON APPLIANCE received");
      if (expectedRawDataOnBytes > 0) {
        for (int i = 0; i < 3; i++) {
          irsend.sendRaw(rawDataOn, expectedRawDataOnBytes, 36);
          yield();
        }
        Serial.println("Command TURN ON APPLIANCE completed");
      } else {
        Serial.println("Not initialized yet. Failed to complete command TURN ON APPLIANCE");
      }
    } else if (strcmp(cmd, "off") == 0) {
      Serial.println("Command TURN OFF APPLIANCE received");
      if (expectedRawDataOffBytes > 0) {
        for (int i = 0; i < 3; i++) {
          irsend.sendRaw(rawDataOff, expectedRawDataOffBytes, 36);
          yield();
        }
        Serial.println("Command TURN OFF APPLIANCE completed");
      } else {
        Serial.println("Not initialized yet. Failed to complete command TURN OFF APPLIANCE");
      }
    }
  }
}

void verify_initialization() {
  Serial.println("Verifying initialization");
  if (isRawDataOnReceived && isRawDataOffReceived) {
    Serial.println("Initialization complete!");
    isInitialized = true;
  }
}

void notify_status() {
  StaticJsonDocument<64> status_document;
  status_document["sensor"] = id;
  status_document["packet_type"] = DATA_TYPE_STATUS;
  status_document["status"] = currentState;
  char msg_out[64];
  serializeJson(status_document, msg_out);
  client.publish(publish_topic, msg_out);
}

void setup() {
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
  client.setBufferSize(512);
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
  currentState = STATUS_UNINITIALIZED;
  notify_status();
  client.subscribe(subscribe_topic);
  irsend.begin();
  while (!isInitialized) {
    client.loop();
  }
  previousState = currentState;
  currentState = STATUS_IDLE;
  notify_status();
}

void loop() {
  delay(5000);

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
    Serial.println(temperature);
  }

  DynamicJsonDocument tx_document(2048);
  tx_document["sensor"] = id;
  tx_document["packet_type"] = DATA_TYPE_OTHERS;
  tx_document["temp"] = round2(temperature);
  tx_document["light"] = round2(light);
  tx_document["sound"] = round2(sound);
  char msg_out[256];
  serializeJson(tx_document, msg_out);
  client.publish(publish_topic, msg_out);
  client.loop();
}

float readChannel(ADS1115_MUX channel) {
  float voltage = 0.0;
  adc.setCompareChannels(channel);
  voltage = adc.getResult_V(); // alternative: getResult_mV for Millivolt
  return voltage;
}

double round2(float value) {
   return (int)(value * 100 + 0.5) / 100.0;
}
