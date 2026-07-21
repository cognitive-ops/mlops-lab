# MLFlow Server Deployment with Terraform

This directory contains Terraform configuration files to deploy an MLFlow server on AWS. The deployment includes resources such as EC2, S3, RDS, IAM roles, and Route53 for hosting the MLFlow server.

## Prerequisites

Before deploying the MLFlow server, ensure the following:

1. **Terraform Installed**: Install Terraform on your system. Refer to the [Terraform Installation Guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
2. **AWS CLI Configured**: Ensure the AWS CLI is installed and configured with credentials and a default region.
3. **Backend Configuration**: The `main.tf` file uses an S3 bucket and DynamoDB table for remote state management. Ensure these resources exist:
   - S3 Bucket: `mlflow-dev-terraform-state-bucket`
   - DynamoDB Table: `mlflow-dev-terraform-state-lock`

## Steps to Deploy the MLFlow Server

1. **Initialize Terraform**:
   - Run the following command to initialize the Terraform working directory:
     ```bash
     terraform init
     ```

2. **Review and Update Variables**:
   - Open the `variables.tf` file and update the variable values as needed for your environment.

3. **Plan the Deployment**:
   - Generate and review the execution plan to understand the resources that will be created:
     ```bash
     terraform plan
     ```

4. **Apply the Configuration**:
   - Deploy the resources by applying the Terraform configuration:
     ```bash
     terraform apply
     ```
   - Confirm the apply operation when prompted.

5. **Access the MLFlow Server**:
   - Once the deployment is complete, the output will include the URL or IP address of the MLFlow server. Use this to access the MLFlow UI.

## Files in This Directory

- `main.tf`: Configures the Terraform backend for state management.
- `variables.tf`: Defines input variables for the Terraform configuration.
- `output.tf`: Specifies the outputs of the Terraform deployment.
- `ec2.tf`: Configures the EC2 instance for hosting the MLFlow server.
- `s3.tf`: Configures the S3 bucket for MLFlow artifact storage.
- `rds.tf`: Configures the RDS database for MLFlow metadata storage.
- `iam.tf`: Defines IAM roles and policies for resource access.
- `route53.tf`: Configures DNS records for the MLFlow server.
- `dynamodb.tf`: Configures the DynamoDB table for Terraform state locking.

## Notes

- Ensure that the AWS account has sufficient permissions to create the required resources.
- Modify the `provider.tf` file if you need to change the AWS region or provider settings.
- Use `terraform destroy` to tear down the resources when they are no longer needed.

## Troubleshooting

- **State Lock Issues**: If you encounter state lock errors, check the DynamoDB table for active locks and remove them if necessary.
- **Resource Limits**: Ensure your AWS account has sufficient limits for the resources being created.
- **Access Issues**: Verify that the security group rules allow access to the MLFlow server from your IP address.

For further assistance, refer to the [Terraform Documentation](https://developer.hashicorp.com/terraform/docs) or the [AWS Documentation](https://aws.amazon.com/documentation/).

https://kb.scopicsoftware.com/books/it-operations/page/mlops-mlflow
