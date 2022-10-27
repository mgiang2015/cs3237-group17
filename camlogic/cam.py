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
url = 'https://cs3237-366406.uc.r.appspot.com/classify'
client = mqtt.Client("P1")  # create new instance
client.connect("broker.emqx.io")  # connect to broker

# title of the app
cv2.namedWindow('python webcam screenshot app')

# let's assume the number of images gotten is 0
img_counter = 0

# while loop
while True:
    # intializing the frame, ret
    ret, frame = cam.read()
    # if statement
    if not ret:
        print('failed to grab frame')
        break
    # the frame will show with the title of test
    cv2.imshow('test', frame)
    # to get continuous live video feed from my laptops webcam
    k = cv2.waitKey(1)
    # if the escape key is been pressed, the app will stop
    if k % 256 == 27:
        print('escape hit, closing the app')
        break
    # if the spacebar key is been pressed
    # screenshots will be taken
    elif ((time.time() - oldtime) >= 5):  # elif k%256  == 32:
        oldtime = time.time()
        # the format for storing the images screenshotted
        img_name = f"opencv_frame_{img_counter}.jpeg"
        # saves the image as a png file
        cv2.imwrite(img_name, frame)
        print('screenshot taken')
        # the number of images automaticallly increases by 1
        img_counter += 1
        imgFile = open(f"D:/CodeStuff/{img_name}", 'rb')
        img_data = imgFile.read()
        # the http -> firebase straight way
        files = {'image': img_data}
        #print(bytearray(img_data))
        response = requests.post(url, files=files)
        print(response.content)

        # isSuccess, im_buf_arr = cv2.imencode('.png', cv2.imread(img_name))
        # io_buf = io.BytesIO(im_buf_arr)
        # byte_im = io_buf.getvalue()
        # print(bytearray(byte_im))
        # filecontent = imgFile.read()
        # byteArr = bytearray(filecontent)
        # print(filecontent)

        # client.publish('group17/tvManager/Camera', byte_im, qos=1)
        publish.single('group17/tvManager/Camera', bytearray(img_data), hostname='broker.emqx.io')

# release the camera
cam.release()

# stops the camera window
cam.destroyAllWindows()