import database
from datetime import datetime

# Add device data example

# database.add_device_data({
#     "name": "Air Con",
#     "identifier" : "abc",
#     "off_code": "OFF CODE FOR DEVICE ABC",
#     "on_code": "ON CODE FOR DEVICE ABC",
# })

# device = database.get_device_with_identifier("abc")
# print(device["on_code"])
# print(device["off_code"])

# Add sensor data example

# AWAKE
# database.add_sensor_data({
#     "sleeping_status": False,
#     "device_identifier": "abc",
#     "appliance_status": True,
# })

# ASLEEP
# database.add_sensor_data({
#     "sleeping_status": True,
#     "device_identifier": "abc",
#     "appliance_status": False,
# })

# print(database.get_sensor_data_for_device("abc"))