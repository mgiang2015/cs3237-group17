from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Access secret keys saved in .env file (telegram bot token obtained from bot father)
load_dotenv()
CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')
DATABASE = 'Analytics'
COLLECTION = "SensorData"

client = MongoClient(CONNECTION_STRING)
print("Successfully connected to MongoDB")

analytics_db = client[DATABASE]
print((f"DATABASE CONNECTED: {analytics_db}"))

sensor_data = analytics_db[COLLECTION]
print(f"COLLECTION: {sensor_data}")

def get_all_sensor_data():
    return sensor_data.find()

def add_sensor_data(sensor_data_json):
    sensor_data_json["date_time"] = datetime.now()
    sensor_data.insert_one(sensor_data_json)
