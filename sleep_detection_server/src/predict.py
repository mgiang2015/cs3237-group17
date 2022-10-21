from tensorflow.python.keras.models  import load_model
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
import numpy as np
from PIL import Image
from os import listdir
from os.path import join

MODEL_NAME = 'har.hd5'
HAR_DIR = '../Human Action Recognition'
TEST_DIR = HAR_DIR + '/test'

dict={0:'listening_to_music', 1:'sitting', 2:'sleeping', 3:'using_laptop'}
session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())


def classify(model, image):
    with session.graph.as_default():
        set_session(session)
        result = model.predict(image)
        themax = np.argmax(result)

    return (dict[themax], result[0][themax], themax)

def load_image(image_fname):
    img = Image.open(image_fname)
    img = img.resize((249,249))
    imgarray = np.array(img)/255.0
    final = np.expand_dims(imgarray, axis=0)
    return final

def main():
    with session.graph.as_default():
        set_session(session)
        model=load_model(MODEL_NAME)

        sample_files = listdir(TEST_DIR)

        for filename in sample_files:
            filename = join(TEST_DIR, filename)
            img = load_image(filename)
            label,prob,_ = classify(model, img)

            print("We think with certainty %3.2f that image %s is %s." % (prob, filename, label))

if __name__ == "__main__":
    main()