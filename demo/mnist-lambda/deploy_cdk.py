#!/usr/bin/env python3
"""
AWS CDK Stack for MNIST Model Deployment
Deploys the trained model as a Lambda function with API Gateway
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct


class MNISTLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 bucket for model storage
        model_bucket = s3.Bucket(
            self,
            "MNISTModelBucket",
            bucket_name=f"{construct_id.lower()}-models",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        
        # Upload model to S3
        s3deploy.BucketDeployment(
            self,
            "DeployModel",
            sources=[s3deploy.Source.asset("./models")],
            destination_bucket=model_bucket,
            destination_key_prefix="models",
        )
        
        # Lambda function for inference
        mnist_lambda = lambda_.Function(
            self,
            "MNISTInferenceFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "./lambda_package",
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        " && ".join([
                            "pip install -r requirements.txt -t /asset-output",
                            "cp lambda_function.py /asset-output/",
                            "cp models/mnist_model_traced.pt /asset-output/",
                        ])
                    ],
                )
            ),
            memory_size=512,
            timeout=Duration.seconds(30),
            environment={
                "MODEL_BUCKET": model_bucket.bucket_name,
            },
        )
        
        # Grant Lambda read access to model bucket
        model_bucket.grant_read(mnist_lambda)
        
        # API Gateway
        api = apigw.RestApi(
            self,
            "MNISTApi",
            rest_api_name="MNIST Digit Recognition API",
            description="API for handwritten digit recognition using deep learning",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )
        
        # API endpoints
        predict_resource = api.root.add_resource("predict")
        predict_integration = apigw.LambdaIntegration(mnist_lambda)
        predict_resource.add_method("POST", predict_integration)
        
        # Health check endpoint
        health_resource = api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{
                    "statusCode": "200",
                    "responseTemplates": {
                        "application/json": '{"status": "healthy"}'
                    }
                }],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[{"statusCode": "200"}]
        )
        
        # Outputs
        cdk.CfnOutput(
            self,
            "ApiEndpoint",
            value=api.url,
            description="API Gateway endpoint URL",
        )
        
        cdk.CfnOutput(
            self,
            "PredictEndpoint",
            value=f"{api.url}predict",
            description="Prediction endpoint URL",
        )


app = cdk.App()
stack = MNISTLambdaStack(app, "MNISTLambdaStack")

# Add tags
cdk.Tags.of(stack).add("Owner", "v.anh")
cdk.Tags.of(stack).add("Project", "acme-mlstudio")
cdk.Tags.of(stack).add("Application", "mnist-digit-recognition")

app.synth()
