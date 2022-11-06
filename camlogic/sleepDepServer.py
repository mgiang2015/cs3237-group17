import json
from flask import Flask, request, jsonify
from flask_mqtt import Mqtt
import requests
from io import StringIO
from PIL import Image

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
###############3

MODEL_NAME = 'electronics.hd5'
url = 'https://cs3237-366406.uc.r.appspot.com/classify'
img_counter = 0
photoresistorQueue = []
onCode = []
offCode = []
numOfSleepPics = 0
wemosSetupStage = 0
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())


app = Flask(__name__)
app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'hello'  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = '123kek'  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True
topic = ['group17/tvManager/sensors', 'group17/tvManager/Photoresistor', 'group17/tvManager/Camera', 'group17/tvManager/command'];
mqtt_client = Mqtt(app)

CAMERA_TOPIC = "group17/tvManager/Camera"
SENSORS_TOPIC = "group17/tvManager/sensors"
COMMAND_TV_TOPIC = "group17/tvManager/command"
APP_TOPIC = "group17/tvManager/fromApp"


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
        imgFile = open(f"D:/CodeStuff/output.jpeg", 'rb')
        img_data = imgFile.read()
        # the http -> firebase straight way
        files = {'image': img_data}

        response = requests.post(url, files=files)
        print(response.content)
        storedVal = json.loads(response.text)
        print(storedVal['data']['label'])
        if storedVal['data']['label'] == "sleeping":
            print("YOU HAVE BEEN DETECTED AS SLEEPING BY ML")
            numOfSleepPics = numOfSleepPics + 1
        if numOfSleepPics == 3:
            # Notify the phone app if user is asleep or notify WeMos
            mqtt_client.publish(COMMAND_TV_TOPIC, message) #<- message ‘{“msg”:”ALERT”}’ to app
            #do some cool stuff
    #Sensoral data sent to database + Perform ML
    elif topic1 == SENSORS_TOPIC:
        global onCode
        global offCode
        unpackedJson = json.loads(message.payload)
        if unpackedJson["id"] == "photempsound": # <- standardise what structure of command from sensor should be
            photoresistorQueue.append(unpackedJson["msg"]) # enqueue readings from weijie's sensors
            if(len(photoresistorQueue) == 3): # check if queue size is 3, if so run the prediction
                useTheDecisionTree(photoresistorQueue[0], photoresistorQueue[1], photoresistorQueue[2])
                photoresistorQueue.pop(0)
            else:
                print("Unable to make prediction with Photoresistor + Temp + Sound yet")
            # after running the predicition and printing the state dequeue the oldest reading
        
        # TODO: Add sensor data to database and perform ML as required
        # 2) Receive on code from wemos
        if wemosSetupStage == 1:
            if (len(onCode) == unpackedJson["ir_raw_length"]) # <- indicator of last pkt
                wemosSetupStage += 1
            for data in unpackedJson['ir_raw_data']:
                onCode.append(data)
            setupProtocol()
        if wemosSetupStage == 3:
            if (len(offCode) == unpackedJson["ir_raw_length"]) # <- indicator of last pkt
                wemosSetupStage += 1
            for data in unpackedJson['ir_raw_data']:
                offCode.append(data)
            setupProtocol()

        print(message.payload)
    elif topic1 == APP_TOPIC:
        unpackedJson = json.loads(message.payload)
        if unpackedJson["msg"] == "SETUP_DEVICE":
            # we have to initiate setup protocol
            setupProtocol()
        if "SETUP_NAME_" in unpackedJson["msg"]:
            # set new name to unpackedJson["msg"]
        # if unpackedJson["id"] == IR on and off command
            # publish message {"sensor": "oaihdadia", "command": "on"} / off as needed
            # update to le's app that a particular device on/off state just changed with format : ‘{“msg”:”<nameOfAppliance>_ON”}’ or : ‘{“msg”:”<nameOfAppliance>_OFF”}’
            # update database with the on/off state by making database updates
    else:
        print('Received message on topic: {topic1} with payload: {payload}'.format(**data))


@app.route('/publish', methods=['POST'])
def publish_message():
    request_data = request.get_json()
    publish_result = mqtt_client.publish(request_data['topic'], request_data['msg'])
    return jsonify({'code': publish_result[0]})

def setupProtocol():
    global onCode
    global offCode
    global wemosSetupStage
    if wemosSetupStage == 0:
        # Begin Setup Protocol
        #SETUP PROTOCOL 1) Request listening Wemos for the On code
        message = {
            "command": "RECORD"
        }
        mqtt_client.publish(COMMAND_TV_TOPIC, message)
        wemosSetupStage += 1
    # 3) Send on code back to Wemos
    if wemosSetupStage == 2:
        # Xu Hui's way of sending back!!
        # Update database with oncode?
    # 4) Request wemos for off code 
        message = {
            "command": "RECORD"
        }
        mqtt_client.publish(COMMAND_TV_TOPIC, message)
        wemosSetupStage += 1
    # 5) Send off code back to Wemos
    if wemosSetupStage == 4:
        # Xuhui's send off code back to Wemos
        # publish ‘{“msg”:”IR_SETUP_DONE”}’ to app

        wemosSetupStage = 0 #is this it?

def control_tv(on):
    # Turn on the TV with True, else False
    if on is True:
        message = {
            "command": "on"
        }
    else:
        message = {
            "command": "off"
        }
    message = json.dumps(message)
    result = mqtt_client.publish(COMMAND_TV_TOPIC, message)

    return result[0]



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
    model = get_dt(MODEL_NAME, train_path="C:/CS3237/electronics.csv")
    arr = np.array([arr1, arr2, arr3]) #[[33.3, 1024, 53], [38.4, 512, 1024], [33.3, 908, 1024]])
    state = classify_state(model, arr)
    print("The current state of the electronic is %s." %(state))
    return state

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
