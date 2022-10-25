# importing the python open cv library
import cv2
import time
import requests
from PIL import Image

# intialize the webcam and pass a constant which is 0
cam = cv2.VideoCapture(0)
oldtime = time.time()
url = 'https://cs3237-366406.uc.r.appspot.com/classify'

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
    #to get continuous live video feed from my laptops webcam
    k  = cv2.waitKey(1)
    # if the escape key is been pressed, the app will stop
    if k%256 == 27:
        print('escape hit, closing the app')
        break
    # if the spacebar key is been pressed
    # screenshots will be taken
    elif ((time.time()-oldtime) >= 10):#elif k%256  == 32:
        oldtime = time.time()
        # the format for storing the images scrreenshotted
        img_name = f'opencv_frame_{img_counter}.png'
        # saves the image as a png file
        cv2.imwrite(img_name, frame)
        print('screenshot taken')
        # the number of images automaticallly increases by 1
        img_counter += 1
        imgFile = open(img_name, 'rb')
        files = {'image': imgFile}
        response = requests.post(url, files=files)
        print(response.content)
        

# release the camera
cam.release()

# stops the camera window
cam.destroyAllWindows()