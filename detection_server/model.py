# Model config
import tempfile
import os
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
from tensorflow.python.keras.models  import load_model
import numpy as np
from google_storage_api import download_zip_and_unzip, CLOUD_STORAGE_BUCKET


MODEL_NAME = 'har.hd5'
dict={0:'not_sleeping', 1:'sleeping'}
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())
appModel = None

def get_model_path():
    tmpdir = tempfile.gettempdir()
    return os.path.join(tmpdir, MODEL_NAME)

def classify_image(model, image):
    with session.graph.as_default():
        set_session(session)
        result = model.predict(image)
        themax = np.argmax(result)

    return (dict[themax], result[0][themax], themax)

def preprocess_image(image):
	#print(image)
	img = image.resize((249,249))
	imgarray = np.array(img)/255.0
	final = np.expand_dims(imgarray, axis=0)
	return final


def get_model():
    if not os.path.exists(get_model_path()):
        source_blob_name = "model.zip"
        destination_file_name = tempfile.gettempdir()
        download_zip_and_unzip(CLOUD_STORAGE_BUCKET, source_blob_name=source_blob_name, destination_folder_name=destination_file_name)

    # Check if model has been loaded. If not, load
    global appModel
    if appModel == None:
        with session.graph.as_default():
            set_session(session)
            appModel=load_model(get_model_path())

    return appModel