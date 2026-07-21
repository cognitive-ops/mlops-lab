# EC2 GPU Terraform Project

This project uses Terraform to provision an EC2 instance with GPU capabilities on AWS. It is designed to facilitate the deployment of GPU instances for various workloads, including machine learning and data processing.

## Project Structure

- `main.tf`: Entry point for the Terraform configuration, calling the EC2 instance module.

- `variables.tf`: Input variables for the main Terraform configuration.

- `outputs.tf`: Output values for the main Terraform configuration.

- `provider.tf`: Provider configuration for Terraform.

## Setup Instructions

1. **Install Terraform**: Ensure that Terraform is installed on your machine. You can download it from the [Terraform website](https://www.terraform.io/downloads.html).

2. **Configure AWS Credentials**: Set up your AWS credentials. You can do this by configuring the AWS CLI or by setting environment variables.

3. **Generate SSH Keys**: Follow the instructions in the `ssh-keys/README.md` to generate SSH keys for accessing the EC2 instance.

4. **Modify Variables**: Update the `variables.tf` files in both the root and the `modules/ec2-instance/` directory to specify your desired configuration, such as the instance type and AMI ID.

5. **Initialize Terraform**: Run `terraform init` in the project root directory to initialize the Terraform configuration.

6. **Plan the Deployment**: Execute `terraform plan` to see the resources that will be created.

7. **Apply the Configuration**: Run `terraform apply` to provision the EC2 instance.

## Accessing the EC2 Instance

Once the EC2 instance is up and running, you can access it via SSH using the generated SSH keys. Ensure that the security group associated with the instance allows inbound SSH traffic.

## Outputs

After the deployment, you can find the instance ID and public IP address in the output of the `terraform apply` command.