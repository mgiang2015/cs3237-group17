# File to run the web app, basically define API
from crypt import methods
from flask import Flask, request, jsonify
from PIL import Image
import numpy as np
import cv2

app = Flask(__name__)

@app.route('/')
def hello_world():
	return "API is working properly!"

@app.route('/classify', methods=["POST"])
def classify():
	# Read
	file = request.files['image'].read() # byte file
	npimg = np.fromstring(file, np.uint8)
	img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

	# Process and classify

	# Return

	return jsonify({ 'msg': 'success', 'data': 'placeholder data, replace with prediction later' })