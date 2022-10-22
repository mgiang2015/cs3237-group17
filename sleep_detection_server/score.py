# SCORING FILE. This is expected by Azure ML to guide it what to do with the model
from tensorflow.python.keras.models  import load_model
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify

from azureml.core.model import Model

MODEL_NAME = 'har'
dict={0:'listening_to_music', 1:'sitting', 2:'sleeping', 3:'using_laptop'}
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())

def preprocess_image(image):
	print(image)
	img = image.resize((249,249))
	imgarray = np.array(img)/255.0
	final = np.expand_dims(imgarray, axis=0)
	return final

def classifyImage(model, image):
    with session.graph.as_default():
        set_session(session)
        result = model.predict(image)
        themax = np.argmax(result)

    return (dict[themax], result[0][themax], themax)

def init():
    global model
    # Retrieve model
    with session.graph.as_default():
        set_session(session)
        model_path = Model.get_model_path(MODEL_NAME)            
        model = load_model(model_path)

def run(raw_data):
    file = raw_data.files['image'] # byte file
    img = Image.open(file)

    # Process image and classify
    img = preprocess_image(img)
    label, prob, _ = classifyImage(model, img)

    # Return
    return jsonify({ 'msg': 'success', 'data': {
        'label': label,
        'probability': str(prob)
    }})