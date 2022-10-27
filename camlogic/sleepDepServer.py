from flask import Flask, request, jsonify
from flask_mqtt import Mqtt
import requests
from io import StringIO
from PIL import Image

url = 'https://cs3237-366406.uc.r.appspot.com/classify'
img_counter = 0

app = Flask(__name__)
app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'hello'  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = '123kek'  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True
topic = ['group17/tvManager/IR', 'group17/tvManager/Photoresistor', 'group17/stoveManager/TempSensor', 'group17/stoveManager/Photoresistor', 'group17/tvManager/Camera'];
mqtt_client = Mqtt(app)

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
   if(rc==0):
       print('Connected successfully')
       for line in topic:
          mqtt_client.subscribe(line) # subscribe topic
       return

   print('Bad connection. Code:', rc)
       
@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
   data = dict(
       topic1=message.topic,
       payload=message.payload.decode()
   )

   topic1 = message.topic
   if topic1=="group17/tvManager/Camera":
        print('Pic Number = ' + img_counter)
        img_counter = img_counter + 1
        
        f = open('output.jpeg', 'wb')
        f.write(message.payload)
        f.close
        imgFile = open(f"D:/CodeStuff/output.jpeg", 'rb')
        img_data = imgFile.read()
        # the http -> firebase straight way
        files = {'image': img_data}
        
        response = requests.post(url, files=files)
        print(response.content)
   else:  
        print('Received message on topic: {topic} with payload: {payload}'.format(**data))

@app.route('/publish', methods=['POST'])
def publish_message():
   request_data = request.get_json()
   publish_result = mqtt_client.publish(request_data['topic'], request_data['msg'])
   return jsonify({'code': publish_result[0]})

if __name__ == '__main__':
   app.run(host='127.0.0.1', port=5000)