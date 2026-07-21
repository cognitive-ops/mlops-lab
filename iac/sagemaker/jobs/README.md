# SageMaker Training Job

This directory contains the necessary files to configure and run a SageMaker training job using a custom Docker image and an S3 bucket for storing model artifacts.

## Prerequisites

Before running the training job, ensure the following:

1. **AWS Credentials**: You have valid AWS credentials configured on your system.
2. **Python Environment**: Install the required Python packages using the `sagemaker-env.yml` file:

   ```bash
   conda env create -f sagemaker-env.yml
   conda activate sagemaker-env
   ```

3. **S3 Bucket**: Update the `BUCKET_NAME` constant in `training-job.py` with your S3 bucket name.
4. **IAM Role**: Ensure the `EXECUTION_ROLE` constant in `training-job.py` is set to a valid SageMaker execution role ARN.

## Files

- `training-job.py`: Main script to configure and run the SageMaker training job.
- `sagemaker-env.yml`: Conda environment file for installing dependencies.
- `src/`: Directory containing the training script (`train.py`) and other source files.
- `Dockerfile`: Dockerfile for building the custom training image.

## Steps to Run the Training Job

1. **Set Up the Environment**:
   - Activate the Conda environment:
     ```bash
     conda activate sagemaker-env
     ```

2. **Build and Push the Docker Image**:
   - Navigate to the directory containing the `Dockerfile` and build the image:
     ```bash
     docker build -t <image-name> .
     ```
   - Tag and push the image to Amazon ECR:
     ```bash
     aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
     docker tag <image-name>:latest <account-id>.dkr.ecr.<region>.amazonaws.com/<image-name>:latest
     docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<image-name>:latest
     ```

3. **Run the Training Job**:
   - Execute the `training-job.py` script:
     ```bash
     python training-job.py
     ```

4. **Monitor the Job**:
   - Use the AWS Management Console or AWS CLI to monitor the training job's progress.

## Notes

- Ensure that the `train.py` script in the `src/` directory is correctly implemented for your training task.
- Modify the `INSTANCE_TYPE` constant in `training-job.py` to change the SageMaker instance type.

## Troubleshooting

- **S3 Bucket Errors**: Ensure the bucket name is unique and you have the necessary permissions.
- **IAM Role Issues**: Verify that the execution role has the required permissions for SageMaker and S3.
- **Docker Image Issues**: Ensure the image is correctly built and pushed to ECR.

For further assistance, refer to the [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html).