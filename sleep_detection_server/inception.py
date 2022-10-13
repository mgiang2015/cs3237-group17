# Download training data, train model and save model
from keras.applications.inception_v3 import InceptionV3
from keras.preprocessing import image
from keras.models import Model, load_model
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, GlobalAveragePooling2D
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import SGD
import os.path
import tarfile
import urllib
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

MODEL_FILE = "flowers.hd5"
FLOWERS_DIR = './flower_photos'
SAMPLES_DIR = "./samples"
TRAIN_FRACTION = 0.8
RANDOM_SEED = 2018

def download_images():
    """If the images aren't already downloaded, save them to FLOWERS_DIR."""
    if not os.path.exists(FLOWERS_DIR):
        DOWNLOAD_URL = 'http://download.tensorflow.org/example_images/flower_photos.tgz'
        print('Downloading flower images from %s...' % DOWNLOAD_URL)
        urllib.request.urlretrieve(DOWNLOAD_URL, 'flower_photos.tgz')
        file = tarfile.open("flower_photos.tgz")
        file.extractall(".")
        file.close()
    print('Flower photos are located in %s' % FLOWERS_DIR)

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

def train(model_file, train_path, validation_path, num_hidden=200, num_classes=5, steps=32, num_epochs=20):
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

def main():
	# Need to find a way to download our flower set!
	download_images()
	train(MODEL_FILE, train_path="flower_photos", validation_path="flower_photos", steps=100, num_epochs=10)

if __name__ == "__main__":
    main()