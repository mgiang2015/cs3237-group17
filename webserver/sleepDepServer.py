import json
from flask import Flask, request, jsonify
from flask_mqtt import Mqtt
import requests
from io import StringIO
from PIL import Image

#database libs
import database
from datetime import datetime

#decision tree libs
import numpy as np                                                              
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from tensorflow.python.keras.models import load_model
from tensorflow.keras.callbacks import ModelCheckpoint
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
import os
import joblib
###############

IR_ON = 0
IR_OFF = 1
PACKET_SIZE = 10

STATUS_UNINITIALIZED = 0
STATUS_IDLE = 1
STATUS_RECORDING = 2

DATA_TYPE_IR = 0
DATA_TYPE_OTHERS = 1
DATA_TYPE_STATUS = 2

MODEL_NAME = 'electronics.hd5'
url = 'https://cs3237-366406.uc.r.appspot.com/classify'#'http://127.0.0.1:5000/classify'#'https://cs3237-366406.uc.r.appspot.com/classify'
img_counter = 0
done = False
photoresistorQueue = []
onCode = []
offCode = []
numOfSleepPics = 0
isSleeping = False
appliancePreviousState = False
wemosSetupStage = 0
initialised = False
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())
identifier = "17171717b"#"2ba9214cvd"


app = Flask(__name__)
app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'hello'  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = '123kek'  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True
topic = ['group17/sensors', 'group17/tvManager/Camera', 'group17/phone'];
mqtt_client = Mqtt(app)

CAMERA_TOPIC = "group17/tvManager/Camera"
SENSORS_TOPIC = "group17/sensors"
COMMAND_TV_TOPIC = "group17/command"
APP_TOPIC = "group17/phone"
APP_CMD_TOPIC = "group17/phoneCommand"

def control_tv(on):
    # Turn on the TV with True, else False
    if on is True:
        message = {
            "sensor": identifier,
            "command": "on"
        }
    else:
        message = {
            "sensor": identifier,
            "command": "off"
        }
    message = json.dumps(message)
    result = mqtt_client.publish(COMMAND_TV_TOPIC, message)

    return result[0]

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected successfully')
        for line in topic:
            mqtt_client.subscribe(line)  # subscribe topic
        control_tv(True)
        return

    print('Bad connection. Code:', rc)


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    global img_counter
    global numOfSleepPics
    global isSleeping
    global appliancePreviousState
    global onCode
    global offCode
    global wemosSetupStage
    global done
    global initialised
    global identifier

    data = dict(
        topic1=message.topic,
        payload=message.payload #.decode()
    )

    topic1 = message.topic
    #Image data from camera sent to firebase server and response obtained
    if topic1 == CAMERA_TOPIC:
        img_counter = img_counter + 1

        f = open('output.jpeg', 'wb')
        f.write(message.payload)
        f.close()
        imgFile = open(f"D:\CodeStuff\output.jpeg", 'rb')
        img_data = imgFile.read()

        # the http -> firebase straight way
        files = {'image': img_data}

        # handled the response
        response = requests.post(url, files=files)
        print(response.content)
        storedVal = json.loads(response.text)

        print(storedVal['data']['label'])
        if storedVal['data']['label'] == "sleeping":
            print("YOU HAVE BEEN DETECTED AS SLEEPING BY ML")
            numOfSleepPics = numOfSleepPics + 1
        else:
            numOfSleepPics = 0
            if (isSleeping):
                isSleeping = False
                database.add_sensor_data({
                    "sleeping_status": isSleeping,
                    "device_identifier": identifier,
                    "appliance_status": appliancePreviousState,
                })

        if numOfSleepPics == 3:
            # Notify the phone app if user is asleep or notify WeMos
            message = {
                "command": "ALERT"
            }
            message = json.dumps(message)
            print("ALERT THE MEDIA")
            mqtt_client.publish(APP_CMD_TOPIC, message) #<- message ‘{“command”:”ALERT”}’ to app
            numOfSleepPics = 0
            if (not isSleeping):
                isSleeping = True
                database.add_sensor_data({
                    "sleeping_status": isSleeping,
                    "device_identifier": identifier,
                    "appliance_status": appliancePreviousState,
                })

            for device_sensor_data in database.get_sensor_data_for_device(identifier):
                if initialised == True: #device_sensor_data["appliance_status"] == True and initialised == True:
                    message = {
                        "sensor": identifier,
                        "command": "off"
                    }
                    message = json.dumps(message)
                    mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)

    #Sensoral data sent to database + Perform ML
    elif topic1 == SENSORS_TOPIC:
        arrtemplightsound = []
        unpackedJson = json.loads(message.payload)

        if unpackedJson["packet_type"] == DATA_TYPE_STATUS:
            device = database.get_device_with_identifier(identifier)
            if unpackedJson['status'] == STATUS_UNINITIALIZED and device is not None and device["on_code"] is not None and device["off_code"] is not None:
                print("On and off code exist in DB alr")
                store_ir(identifier, device["on_code"], IR_ON)
                store_ir(identifier, device["off_code"], IR_OFF)
                initialised = True


        if unpackedJson["packet_type"] == DATA_TYPE_OTHERS and initialised == True: # <- standardise what structure of command from sensor should be
            arrtemplightsound.append(unpackedJson["temp"])
            arrtemplightsound.append(unpackedJson["light"])
            arrtemplightsound.append(unpackedJson["sound"])
            photoresistorQueue.append(arrtemplightsound) # enqueue readings from weijie's sensors
            if(len(photoresistorQueue) == 3): # check if queue size is 3, if so run the prediction
                applicationCurrState = useTheDecisionTree(photoresistorQueue[0], photoresistorQueue[1], photoresistorQueue[2])

                if (applicationCurrState != appliancePreviousState):
                    database.add_sensor_data({
                        "sleeping_status": isSleeping,
                        "device_identifier": identifier,
                        "appliance_status": applicationCurrState,
                    })
                    appliancePreviousState = applicationCurrState

                photoresistorQueue.pop(0)
            else:
                print("Unable to make prediction with Photoresistor + Temp + Sound yet")

        # 2) Receive on code from wemos
        if wemosSetupStage == 1:
            unpackedJson = json.loads(message.payload)
            if unpackedJson['packet_type'] == DATA_TYPE_STATUS:
                if unpackedJson['status'] == STATUS_RECORDING:
                    #mqtt_client.publish(APP_CMD_TOPIC, message.payload) # Inform phone app that wemos is now recording
                    toSend = {
                        "command": "IR_PRESS_1_READY"
                    }
                    toSend = json.dumps(toSend)
                    mqtt_client.publish(APP_CMD_TOPIC, toSend) # Inform phone app that wemos is now recording
                    print("STATUS RECORDING 1")
                if unpackedJson['status'] == STATUS_UNINITIALIZED:
                    #mqtt_client.publish(APP_CMD_TOPIC, message.payload) # Inform phone app that wemos is now idle
                    toSend = {
                        "command": "IR_PRESS_1_DONE"
                    }
                    toSend = json.dumps(toSend)
                    mqtt_client.publish(APP_CMD_TOPIC, toSend) # Inform phone app that wemos is now recording
                    print("STATUS UNINITIATLIZED 1")
                    wemosSetupStage += 1
                    print(wemosSetupStage)
                    setupProtocol()
            elif unpackedJson['packet_type'] == DATA_TYPE_IR:
                print("receiving data")
                print(len(onCode))
                print(unpackedJson["ir_raw_length"])

                for data in unpackedJson['ir_raw_data']:
                    onCode.append(data)

        if wemosSetupStage == 3:
            unpackedJson = json.loads(message.payload)
            print("in stage 3 and triggered sub")
            if unpackedJson['packet_type'] == DATA_TYPE_STATUS:
                if unpackedJson['status'] == STATUS_RECORDING:
                    #mqtt_client.publish(APP_CMD_TOPIC, message.payload) # Inform phone app that wemos is now recording
                    toSend = {
                        "command": "IR_PRESS_2_READY"
                    }
                    toSend = json.dumps(toSend)
                    mqtt_client.publish(APP_CMD_TOPIC, toSend) # Inform phone app that wemos is now recording
                    print("STATUS RECORDING 3")
                if unpackedJson['status'] == STATUS_UNINITIALIZED:
                    if(done == True):
                        wemosSetupStage += 1
                        setupProtocol()
                        print("STATUS UNINITIATLIZED 3_2")
                        toSend = {
                            "command": "IR_PRESS_2_DONE"
                        }
                        toSend = json.dumps(toSend)
                        mqtt_client.publish(APP_CMD_TOPIC, toSend) # Inform phone app that wemos is now recording
                        done = False
                        initialised = True
                    #mqtt_client.publish(APP_CMD_TOPIC, message.payload) # Inform phone app that wemos is now idle
                    print("STATUS UNINITIATLIZED 3")
                    if(done == False):
                        done = True
                    
            elif unpackedJson['packet_type'] == DATA_TYPE_IR:
                print("send the off code that has been read")
                for data in unpackedJson['ir_raw_data']:
                    offCode.append(data)
                

            if initialised == True:
                database.add_device_data({
                    "name": "Wemos Sensors",
                    "identifier" : identifier,
                    "off_code": offCode,
                    "on_code": onCode,
                })

    elif topic1 == APP_TOPIC:
        print(message.payload)
        unpackedJson = json.loads(message.payload)
        if unpackedJson["command"] == "SETUP_DEVICE":
            # we have to initiate setup protocol
            print("initiate setup now")
            setupProtocol()
        if "SETUP_NAME_" in unpackedJson["command"]:
            print("")
            # set new name to unpackedJson["command"]
        if unpackedJson["command"] == "PHONE_ON":
            message = {
                "sensor": identifier,
                "command": "on"
            }
            message = json.dumps(message)
            mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)

        if unpackedJson["command"] == "PHONE_OFF":
            message = {
                "sensor": identifier,
                "command": "off"
            }
            message = json.dumps(message)
            mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)
            # publish message {"sensor": "oaihdadia", "command": "on"} / off as needed
            # update to le's app that a particular device on/off state just changed with format : ‘{“command”:”<nameOfAppliance>_ON”}’ or : ‘{“command”:”<nameOfAppliance>_OFF”}’
            # update database with the on/off state by making database updates
    else:
        print('Received message on topic: {topic1} with payload: {payload}'.format(**data))


@app.route('/publish', methods=['POST'])
def publish_message():
    request_data = request.get_json()
    publish_result = mqtt_client.publish(request_data['topic'], request_data['command'])
    return jsonify({'code': publish_result[0]})

def store_ir(sensor, data, store_type):
    i = 0
    current_packet = 0
    if store_type == IR_ON:
        command = "store_ir_on"
    elif store_type == IR_OFF:
        command = "store_ir_off"
    while i < len(data):
        remaining_data = len(data) - i
        if remaining_data >= PACKET_SIZE:
            size_to_process = PACKET_SIZE
        else:
            size_to_process = remaining_data
        temp = []
        for n in range(i, i + size_to_process):
            temp.append(data[n])
        message = {
            "sensor": sensor,
            "command": command,
            "ir_raw_length": len(data),
            "packet_num": current_packet,
            "ir_raw_data": temp
        }
        message = json.dumps(message)
        result = mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)
        current_packet += 1
        i += size_to_process
    #return result[0]

def setupProtocol():
    global onCode
    global offCode
    global wemosSetupStage
    global initialised

    if wemosSetupStage == 0:
        initialised = False
        # Begin Setup Protocol
        #SETUP PROTOCOL 1) Request listening Wemos for the On code
        message = {
            "sensor": identifier,
            "command": "record"
        }
        message = json.dumps(message)
        mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)
        wemosSetupStage += 1
    # 3) Send on code back to Wemos
    if wemosSetupStage == 2:
        # Update database with oncode?
        print("Received full IR message, sending back to wemos")
        store_ir(identifier, onCode, IR_ON)
        print("Sending...")
    # 4) Request wemos for off code 
        message = {
            "sensor": identifier,
            "command": "record"
        }
        message = json.dumps(message)
        mqtt_client.publish(COMMAND_TV_TOPIC, message, qos=2)
        print("Sent request to wemos to record offcode")
        wemosSetupStage += 1
        print("wemossetup stage " + str(wemosSetupStage))
    # 5) Send off code back to Wemos
    if wemosSetupStage == 4:
        # Xuhui's send off code back to Wemos
        #if is_ir_off_init is False:
        store_ir(identifier, offCode, IR_OFF)
        print("Sending off code to wemos...")
        message = {
            "command": "IR_SETUP_DONE"
        }
        message = json.dumps(message)
        mqtt_client.publish(APP_CMD_TOPIC, message)
        print("DONE WITH SETUP PROTOCOL, NOW IDLE...")
        wemosSetupStage = 0


########## DECISION TREE CODE ####################
def create_dt(train_path):
    # Load the dataset
    elec = pd.read_csv(train_path, sep='\s*,\s*', engine = 'python')
    elec.head()

    labels = np.concatenate((elec['temperature'].values.reshape(-1, 1),
                            elec['light'].values.reshape(-1, 1),
                            elec['sound'].values.reshape(-1, 1)), axis=1)

    targets = elec['on'].values.reshape(-1, 1)

    X_train, X_test, Y_train, Y_test = train_test_split(labels, targets, test_size = 0.3, random_state = 1)                    
                        
    # Create Decision Tree classifer
    clf = DecisionTreeClassifier()

    clf.fit(X_train, Y_train)

    train_predict = clf.predict(X_train).reshape(-1,1)
    test_predict = clf.predict(X_test).reshape(-1,1)                        

    train_perf = accuracy_score(Y_train, train_predict)
    test_perf = accuracy_score(Y_test, test_predict)

    return clf

def get_dt(model_file, train_path):
    if os.path.exists(model_file):
        print("\n*** Existing model found at %s. Loading.***\n\n" % model_file)
        model = joblib.load(model_file)
    else:
        print("\n*** Creating new model ***\n\n")
        model = create_dt(train_path)
        joblib.dump(model, MODEL_NAME)
    
    return model

def classify_state(model, data):
    with session.graph.as_default():
        set_session(session)
        data.reshape(-1, 1)
        state_of_elec = model.predict(data).reshape(-1, 1) # The state will be either 0 (off) or 1 (on)
    return {"state": state_of_elec}

def useTheDecisionTree(arr1, arr2, arr3):
    model = get_dt(MODEL_NAME, train_path="D:\CodeStuff\sleepDep\cs3237-group17\camlogic\electronics.csv")
    arr = np.array([arr1, arr2, arr3]) #[[33.3, 1024, 53], [38.4, 512, 1024], [33.3, 908, 1024]])
    state = classify_state(model, arr)
    onOrOff = tellMeIfOnOrNot(state)
    print("The current state of the electronic is %s." %(onOrOff))

    if (onOrOff == "on"):
        message = {
            "name": "TV",
            "command": "SENSE_ON"
        }
        message = json.dumps(message)
        mqtt_client.publish(APP_CMD_TOPIC, message)
    else:
        message = {
            "name": "TV",
            "command": "SENSE_OFF"
        }
        message = json.dumps(message)
        mqtt_client.publish(APP_CMD_TOPIC, message)
    return True if onOrOff == "on" else False

def tellMeIfOnOrNot(state):
    label = "off"
    temp = state["state"][0]
    light = state["state"][1]
    sound = state["state"][2]
    if temp==[0] and light==[0] and sound==[0]:
        label = "off"
    else:
        label = "on"
    return label

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
