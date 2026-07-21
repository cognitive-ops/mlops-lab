import pandas as pd
from azure.ai.ml import MLClient, command, dsl
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import Environment
from azure.ai.ml.dsl import pipeline
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes

# Connect to workspace
ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id="149320c8-1862-4442-a080-bfe259e3315a",
    resource_group_name="mlops",
    workspace_name="mlklowen"
)

print("Connected to Azure ML workspace", ml_client.workspace_name)

# Define environment (or use built-in like 'AzureML-sklearn')
env = Environment(
    name="sklearn-env",
    image="mcr.microsoft.com/azureml/sklearn:1.0-ubuntu20.04-py38-cpu",
)

# update the 'my_path' variable to match the location of where you downloaded the data on your
# local filesystem
my_path = "./data/default_of_credit_card_clients.csv"
# set the version number of the data asset
v1 = "initial"

my_data = Data(
    name="credit-card",
    version=v1,
    description="Credit card data",
    path=my_path,
    type=AssetTypes.URI_FILE,
)

# create data asset if it doesn't already exist:
try:
    data_asset = ml_client.data.get(name="credit-card", version=v1)
    print(
        f"Data asset already exists. Name: {my_data.name}, version: {my_data.version}"
    )
    print(f"Data asset URI: {data_asset.path}")
    df = pd.read_csv(data_asset.path)
    df.head()
except Exception:
    ml_client.data.create_or_update(my_data)
    print(
        f"Data asset created. Name: {my_data.name}, version: {my_data.version}")
