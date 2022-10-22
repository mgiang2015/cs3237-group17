from azureml.core.webservice import LocalWebservice
from azureml.core.model import InferenceConfig
from azureml.core import Workspace
from azureml.core.model import Model
from azureml.core.environment import Environment

ws = Workspace.from_config()
model = Model(ws, 'har')

myenv = Environment.get(workspace=ws, name="tutorial-env", version="1")
inference_config = InferenceConfig(entry_script="score.py", image_config=image_config)

deployment_config = LocalWebservice.deploy_configuration(port=8080)

local_service = Model.deploy(workspace=ws, 
                       name='har-local', 
                       models=[model], 
                       inference_config=inference_config, 
                       deployment_config = deployment_config)

local_service.wait_for_deployment(show_output=True)
print(f"Scoring URI is : {local_service.scoring_uri}")