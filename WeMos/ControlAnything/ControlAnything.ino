#include <IRsend.h>
#include <IRrecv.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define DATA_TYPE_IR 0
#define DATA_TYPE_OTHERS 1
#define DATA_TYPE_STATUS 2

#define STATUS_UNINITIALIZED 0
#define STATUS_IDLE 1
#define STATUS_RECORDING 2

const char *id = "";             // MUST BE FILLED IN BEFORE USE

// WiFi
const char *ssid = "";           // MUST BE FILLED IN BEFORE USE
const char *password = "";       // MUST BE FILLED IN BEFORE USE

// MQTT Broker
const char *mqtt_broker = "broker.emqx.io";
const char *subscribe_topic = "group17/command";
const char *publish_topic = "group17/sensors";
const char *mqtt_username = "";  // MUST BE FILLED IN BEFORE USE
const char *mqtt_password = "";  // MUST BE FILLED IN BEFORE USE
const int mqtt_port = 1883;

const int PACKET_SIZE = 10;
const size_t CAPACITY = JSON_ARRAY_SIZE(PACKET_SIZE);
const uint16_t IRLed = 2;
const uint16_t IRReceiver = 5;
IRsend irsend(IRLed);
IRrecv irrecv(IRReceiver, 500);

WiFiClient espClient;
PubSubClient client(espClient);
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
          irsend.sendRaw(rawDataOn, expectedRawDataOnBytes, 38);
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
          irsend.sendRaw(rawDataOff, expectedRawDataOffBytes, 38);
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
  delay(2000); while (!Serial);
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
  client.loop();
}
