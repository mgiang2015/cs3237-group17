from flask import Flask, request, jsonify
from PIL import Image
import shutil
from model import preprocess_image, classify_image, get_model, MODEL_PATH

app = Flask(__name__)
url = "https://cs3237-366406.uc.r.appspot.com/"

@app.route('/')
def index():
    return 'Web App with Python Flask!'

@app.route("/help")
def help():
    structure = "{\n\"data\":{\n\"label\": activity label,\n\"probability\": confidence of prediction\n},\n\"msg\": \"success\"\n}"
    instr = f'Send a POST request with your image to URL: {url}. Result is returned in JSON format, with the following structure:\n{structure}'

    return instr

@app.route("/updateModel", methods=["POST"])
def update():
    # Delete model and zip file to ensure it's updated
    shutil.rmtree(MODEL_PATH)
    get_model()
    return "Update completed"

@app.route("/classify", methods=["POST"])
def classify():
    # Read file sent
    print("Reading file sent with POST request")
    file = request.files['image'] # byte file
    img = Image.open(file)
    
    # Process image and classify
    print("Processing image sent with POST request")
    img = preprocess_image(img)
    label, prob, _ = classify_image(get_model(), img)

    # Return
    return jsonify({ 'msg': 'success', 'data': {
        'label': label,
        'probability': str(prob)
    }})