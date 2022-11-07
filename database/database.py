from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Access secret keys saved in .env file (telegram bot token obtained from bot father)
load_dotenv()
CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')
DATABASE = 'Analytics'
SENSOR_DATA_COLLECTION = "SensorData"
DEVICE_DATA_COLLECTION = "DeviceData"

client = MongoClient(CONNECTION_STRING)
print("Successfully connected to MongoDB")

analytics_db = client[DATABASE]
print((f"DATABASE CONNECTED: {analytics_db}"))

device_data = analytics_db[DEVICE_DATA_COLLECTION]
print(f"COLLECTION: {device_data}")

sensor_data = analytics_db[SENSOR_DATA_COLLECTION]
print(f"COLLECTION: {sensor_data}")

device_data.create_index("identifier", unique = True)
sensor_data.create_index("device_identifier", unique = True)

# Device data API

def add_device_data(device_data_json):
    device_data_json["date_time"] = datetime.now()
    device_data.insert_one(device_data_json)

def get_device_with_identifier(device_identifier):
    return device_data.find_one({"identifier": device_identifier})

# Sensor data API

def get_all_sensor_data():
    return sensor_data.find()

def add_sensor_data(sensor_data_json):
    sensor_data_json["date_time"] = datetime.now()
    sensor_data.insert_one(sensor_data_json)

def get_sensor_data_for_device(device_identifier):
    return list(sensor_data.find({"device_identifier": device_identifier}))
