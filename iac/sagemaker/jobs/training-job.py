import sagemaker
import boto3
from botocore.exceptions import ClientError
from sagemaker.estimator import Estimator

# Constants
EXECUTION_ROLE = "arn:aws:iam::320963574916:role/sagemaker_execution_role"
CUSTOM_IMAGE_URI = "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.0.0-cpu-py310-ubuntu20.04-sagemaker"
# Replace with your bucket name
BUCKET_NAME = "sagemaker-ml-models-artifact-voidmapper"
OUTPUT_PATH = f"s3://{BUCKET_NAME}/model-artifacts/"
REGION = "us-east-1"
INSTANCE_TYPE = "ml.m5.xlarge"


def create_s3_bucket(bucket_name, region):
    """
    Create an S3 bucket if it doesn't already exist.

    Args:
        bucket_name (str): Name of the S3 bucket.
        region (str): AWS region where the bucket will be created.
    """
    s3 = boto3.client("s3", region_name=region)
    try:
        # Check if the bucket already exists
        s3.head_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' already exists.")
    except ClientError as e:
        # If the bucket doesn't exist, create it
        if e.response["Error"]["Code"] == "404":
            print(f"Creating S3 bucket '{bucket_name}'...")
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            print(f"S3 bucket '{bucket_name}' created successfully.")
        else:
            print(f"Error checking bucket: {e}")
            raise


def get_execution_role():
    """
    Fetch the SageMaker execution role.
    Replace this with a hardcoded role ARN if not using SageMaker Studio.
    """
    return EXECUTION_ROLE


def get_custom_image_uri():
    """
    Return the custom Docker image URI for the training job.
    """
    return CUSTOM_IMAGE_URI


def get_output_path():
    """
    Specify the S3 path where the model artifacts will be saved.
    """
    return OUTPUT_PATH


def create_estimator():
    """
    Create and configure the SageMaker Estimator for the training job.
    """
    return Estimator(
        entry_point="train.py",
        source_dir="src",
        image_uri=get_custom_image_uri(),
        role=get_execution_role(),
        instance_count=1,
        instance_type=INSTANCE_TYPE,
        output_path=get_output_path(),
    )


def main():
    """
    Main function to configure and start the SageMaker training job.
    """
    # Create the S3 bucket if it doesn't exist
    create_s3_bucket(BUCKET_NAME, REGION)

    print("Initializing SageMaker Estimator...")
    estimator = create_estimator()

    print("Starting training job...")
    estimator.fit()
    print("Training job completed.")


if __name__ == "__main__":
    main()
