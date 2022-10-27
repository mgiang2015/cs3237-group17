# Model config
import tempfile
import os
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
from tensorflow.python.keras.models  import load_model
import numpy as np
from google_storage_api import download_zip_and_unzip, CLOUD_STORAGE_BUCKET

tmpdir = tempfile.gettempdir()
MODEL_NAME = 'har.hd5'
MODEL_PATH = os.path.join(tmpdir, MODEL_NAME)
dict={0:'listening_to_music', 1:'sitting', 2:'sleeping', 3:'using_laptop'}
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())
appModel = None

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
    if not os.path.exists(MODEL_PATH):
        source_blob_name = "model.zip"
        destination_file_name = tmpdir
        download_zip_and_unzip(CLOUD_STORAGE_BUCKET, source_blob_name=source_blob_name, destination_folder_name=destination_file_name)

    # Check if model has been loaded. If not, load
    global appModel
    if appModel == None:
        with session.graph.as_default():
            set_session(session)
            appModel=load_model(MODEL_PATH)

    return appModel