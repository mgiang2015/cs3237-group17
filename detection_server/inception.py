# Download training data, train model and save model
from keras.applications.inception_v3 import InceptionV3
from keras.preprocessing import image
from keras.models import Model, load_model
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, GlobalAveragePooling2D
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import SGD
import tensorflow as tf # Converting model to tflite to host on firebase
import csv # For grouping files into folders
import os
import zipfile
import ssl

# Load dataset and do the normal training stuff
ssl._create_default_https_context = ssl._create_unverified_context

MODEL_FILE = "har.hd5"
HAR_DIR = '../Human Action Recognition'
TRAIN_DIR = HAR_DIR + '/train'
TEST_DIR = HAR_DIR + '/test'
TRAIN_FRACTION = 0.8
RANDOM_SEED = 2018

# Kaggle authentication
os.environ['KAGGLE_USERNAME'] = 'thedecoyg'
os.environ['KAGGLE_KEY'] = '76a4128dadffac0166a97844c34cd7d1'
# This import requires the environment to contain 2 variables above. https://towardsdatascience.com/downloading-datasets-from-kaggle-for-your-ml-project-b9120d405ea4
from kaggle.api.kaggle_api_extended import KaggleApi

def download_images():
    """If the images aren't already downloaded, save them to FLOWERS_DIR."""
    if not os.path.exists(HAR_DIR):
        # Authenticate Kaggle account 
        api = KaggleApi()
        api.authenticate()

        print('Downloading HAR images...')
        api.dataset_download_files('meetnagadia/human-action-recognition-har-dataset', path='..')

        with zipfile.ZipFile('../human-action-recognition-har-dataset.zip', 'r') as zip_ref:
            zip_ref.extractall('..')

        # Unzip our own collected data into HAR_DIR to create class folders
        with zipfile.ZipFile('../collected_data.zip', 'r') as zip_ref:
            zip_ref.extractall(TRAIN_DIR)

        # Grouping train data into folders
        with open(os.path.join(HAR_DIR, 'Training_set.csv'), newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['label'] in ['sleeping']:
                    parent_dir = os.path.join(TRAIN_DIR, row['label'])
                    old_path = os.path.join(TRAIN_DIR, row['filename'])
                    new_path = os.path.join(parent_dir, row['filename'])
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir)
                    os.rename(old_path, new_path)
                else:
                    parent_dir = os.path.join(TRAIN_DIR, 'not_sleeping')
                    old_path = os.path.join(TRAIN_DIR, row['filename'])
                    new_path = os.path.join(parent_dir, row['filename'])
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir)
                    os.rename(old_path, new_path)

    print('HAR photos are located in %s' % HAR_DIR)

def create_model(num_hidden, num_classes):
    base_model = InceptionV3(include_top=False, weights='imagenet')
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(num_hidden, activation='relu')(x)
    predictions = Dense(num_classes, activation='softmax')(x)

    for layer in base_model.layers:
        layer.trainable = False
    
    model = Model(inputs=base_model.input, outputs=predictions)

    return model

def load_existing(model_file):
    model = load_model(model_file)

    numlayers = len(model.layers)

    for layer in model.layers[:numlayers - 3]: # start til numlayers - 3
        layer.trainable = False

    for layer in model.layers[numlayers - 3:]: # numlayers - 3 onwards
        layer.trainable = True

    return model

def train(model_file, train_path, validation_path, num_hidden=200, num_classes=4, steps=32, num_epochs=20):
    if os.path.exists(model_file):
        print("\n*** Existing model found at %s. Loading.***\n\n" % model_file)
        model = load_existing(model_file)

    else:
        print("\n**** Creating new model ****\n\n")
        model = create_model(num_hidden, num_classes)

    model.compile(optimizer='rmsprop', loss='categorical_crossentropy')

    # checkpoint
    checkpoint = ModelCheckpoint(model_file)

    train_datagen = ImageDataGenerator(\
        rescale=1./255,\
        shear_range=0.2,\
        zoom_range=0.2,\
        horizontal_flip=True)

    test_datagen = ImageDataGenerator(rescale=1./255)

    train_generator = train_datagen.flow_from_directory(\
        train_path,\
        target_size=(249,249),\
        batch_size=32,\
        class_mode='categorical')

    validation_generator = test_datagen.flow_from_directory(\
        validation_path,\
        target_size=(249,249),\
        batch_size=32,\
        class_mode='categorical')
    
    model.fit(\
        train_generator,\
        steps_per_epoch = steps,\
        epochs=num_epochs,\
        callbacks = [checkpoint],\
        validation_data = validation_generator,\
        validation_steps=50)

    # train last 2 layers?
    for layer in model.layers[:249]:
        layer.trainable = False
    
    for layer in model.layers[249:]:
        layer.trainable = True

    model.compile(optimizer=SGD(lr=0.00001, momentum=0.9), loss='categorical_crossentropy')
    return model


def handleTrainRequest():
    # Actual training
    download_images()

    # Changed num_classes to 2, we only have 2 classes now
    # Changed epochs to 100 to have a better models
    train(MODEL_FILE, train_path=TRAIN_DIR, num_classes=2, validation_path=TRAIN_DIR, steps=54, num_epochs=100)

if __name__ == "__main__":
    handleTrainRequest()
