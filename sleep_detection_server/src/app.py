# File to run the web app, basically define API
from crypt import methods
from flask import Flask, request, jsonify
from tensorflow.python.keras.models  import load_model
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
from PIL import Image
import numpy as np
import cv2
import os
from inception import handleTrainRequest

# Load model
MODEL_NAME = '../har.hd5'
dict={0:'listening_to_music', 1:'sitting', 2:'sleeping', 3:'using_laptop'}
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())
appModel = None
with session.graph.as_default():
	set_session(session)
	if os.path.exists(MODEL_NAME):
		appModel=load_model(MODEL_NAME)

def classifyImage(model, image):
    with session.graph.as_default():
        set_session(session)
        result = model.predict(image)
        themax = np.argmax(result)

    return (dict[themax], result[0][themax], themax)

def preprocess_image(image):
	print(image)
	img = image.resize((249,249))
	imgarray = np.array(img)/255.0
	final = np.expand_dims(imgarray, axis=0)
	return final

app = Flask(__name__)

@app.route('/')
def hello_world():
	return "API is working properly!"

@app.route('/classify', methods=["POST"])
def classify():
	# Read
	file = request.files['image'] # byte file
	img = Image.open(file)

	# Check for model existance
	if not os.path.exists(MODEL_NAME) or appModel == None:
		return jsonify({ 'msg': 'Failed. No model found', 'data': {}})

	# Process image and classify
	img = preprocess_image(img)
	label, prob, _ = classifyImage(appModel, img)

	# Return
	return jsonify({ 'msg': 'success', 'data': {
		'label': label,
		'probability': str(prob)
	}})

@app.route('/train', methods=["GET"])
def train():
	handleTrainRequest()
	return jsonify({ "msg": "Training has completed. Send a POST request to /classify to classify your picture." })

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))