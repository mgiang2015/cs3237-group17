import numpy as np                                                              
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from tensorflow.python.keras.models import Model, load_model
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
import os
import json

MODEL_NAME = 'electronics.hd5'

session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())

with session.graph.as_default():
    set_session(session)
    model = load_model(MODEL_NAME)

def create_model(train_path):
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

def get_model(model_file, train_path):
    if os.path.exists(model_file):
        print("\n*** Existing model found at %s. Loading.***\n\n" % model_file)
        model = load_existing(model_file)
    else:
        print("\n*** Creating new model ***\n\n")
        model = create_model(train_path)


def classify_state(filename, data):
    with session.graph.as_default():
        set_session(session)
        state_of_elec = model.predict(data).reshape(-1, 1) # The state will be either 0 (off) or 1 (on)
    return {"state": state_of_elec}

def main():
    get_model(MODEL_NAME, train_path="C:/CS3237/electronics.csv")

if __name__ == "__main__":
    main()