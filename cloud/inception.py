# Download training data, train model and save model
from keras.applications.inception_v3 import InceptionV3
from keras.preprocessing import image
from keras.models import Model, load_model
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, GlobalAveragePooling2D
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import SGD
import os.path
import os.system
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
    !tar xfz flower_photos.tgz
  print('Flower photos are located in %s' % FLOWERS_DIR)


def make_train_and_test_sets():
  """Split the data into train and test sets and get the label classes."""
  train_examples, test_examples = [], []
  shuffler = random.Random(RANDOM_SEED)
  is_root = True
  for (dirname, subdirs, filenames) in tf.gfile.Walk(FLOWERS_DIR):
    # The root directory gives us the classes
    if is_root:
      subdirs = sorted(subdirs)
      classes = collections.OrderedDict(enumerate(subdirs))
      label_to_class = dict([(x, i) for i, x in enumerate(subdirs)])
      is_root = False
    # The sub directories give us the image files for training.
    else:
      filenames.sort()
      shuffler.shuffle(filenames)
      full_filenames = [os.path.join(dirname, f) for f in filenames]
      label = dirname.split('/')[-1]
      label_class = label_to_class[label]
      # An example is the image file and it's label class.
      examples = list(zip(full_filenames, [label_class] * len(filenames)))
      num_train = int(len(filenames) * TRAIN_FRACTION)
      train_examples.extend(examples[:num_train])
      test_examples.extend(examples[num_train:])

  shuffler.shuffle(train_examples)
  shuffler.shuffle(test_examples)

  # Create samples folder and move over all test photos
  if not os.path.exists(SAMPLES_DIR):
  	os.mkdirs(SAMPLES_DIR)
	for photo in test_examples:
	  os.rename(photo, SAMPLES_DIR + '/' + dirname.split('/')[-1])
  
  return train_examples, test_examples, classes


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