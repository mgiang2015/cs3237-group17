# importing the python open cv library
import cv2
import time
import requests
import io
from io import BytesIO
from PIL import Image
import paho.mqtt.client as mqtt  # import the client1
import paho.mqtt.publish as publish
import os

# initialize the webcam and pass a constant which is 0
cam = cv2.VideoCapture(0)
oldtime = time.time()
url = 'http://127.0.0.1:5000/classify'#'https://cs3237-366406.uc.r.appspot.com/classify'
client = mqtt.Client("P1")  # create new instance
client.connect("broker.emqx.io")  # connect to broker

# title of the app
cv2.namedWindow('sleepDep')

imgctr = 0

while True:
    # intializing the frame, ret
    ret, frame = cam.read()
    # if statement
    if not ret:
        print('Framegrab failed')
        break
    # the frame will show with the title of test
    cv2.imshow('test', frame)
    # to get continuous live video feed from my laptops webcam
    k = cv2.waitKey(1)
    # if the escape key is pressed, the app will stop
    if k % 256 == 27:
        print('Closing app as Esc key has been pressed')
        break
    # if the spacebar key is been pressed
    # screenshots will be taken
    elif ((time.time() - oldtime) >= 5):  # elif k%256  == 32:
        oldtime = time.time()
        # the format for storing the images screenshotted
        img_name = f"opencv_frame_{imgctr}.jpeg"
        # saves the image as a png file
        cv2.imwrite(img_name, frame)
        print('Snapshot taken')
        # the number of images automaticallly increases by 1
        imgctr += 1
        imgFile = open(f"D:/CodeStuff/{img_name}", 'rb')
        img_data = imgFile.read()

        # the http -> firebase straight way
        files = {'image': img_data}
        
        #response = requests.post(url, files=files)
        #print(response.content)

        # client.publish('group17/tvManager/Camera', byte_im, qos=1)
        publish.single('group17/tvManager/Camera', bytearray(img_data), hostname='broker.emqx.io')

# release the camera
cam.release()

# stops the camera window
cam.destroyAllWindows()