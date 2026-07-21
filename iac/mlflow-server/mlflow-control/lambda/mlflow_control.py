import json
import boto3
import os

ec2 = boto3.client('ec2')
rds = boto3.client('rds')

EC2_INSTANCE_ID = os.environ['EC2_INSTANCE_ID']
RDS_INSTANCE_ID = os.environ['RDS_INSTANCE_ID']
API_KEY = os.environ.get('API_KEY', '')

def lambda_handler(event, context):
    try:
        # Validate API Key
        headers = event.get('headers', {})
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized. Missing Bearer token.'})
            }

        provided_key = auth_header.replace('Bearer ', '').strip()

        if not API_KEY or provided_key != API_KEY:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized. Invalid API key.'})
            }

        # Get HTTP method
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')

        # Handle GET request - check status
        if http_method == 'GET':
            status = {}

            # Get EC2 status
            ec2_response = ec2.describe_instances(InstanceIds=[EC2_INSTANCE_ID])
            if ec2_response['Reservations']:
                instance = ec2_response['Reservations'][0]['Instances'][0]
                ec2_state = instance['State']['Name']

                # Get status checks
                status_checks = ec2.describe_instance_status(InstanceIds=[EC2_INSTANCE_ID])

                instance_status = 'N/A'
                system_status = 'N/A'

                if status_checks['InstanceStatuses']:
                    instance_status = status_checks['InstanceStatuses'][0]['InstanceStatus']['Status']
                    system_status = status_checks['InstanceStatuses'][0]['SystemStatus']['Status']

                status['ec2'] = {
                    'instance_id': EC2_INSTANCE_ID,
                    'state': ec2_state,
                    'instance_status': instance_status,
                    'system_status': system_status
                }

            # Get RDS status
            rds_response = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
            if rds_response['DBInstances']:
                rds_state = rds_response['DBInstances'][0]['DBInstanceStatus']
                status['rds'] = {
                    'instance_id': RDS_INSTANCE_ID,
                    'status': rds_state
                }

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Status retrieved successfully',
                    'status': status
                })
            }

        # Handle POST request - start/stop instances
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', '').lower()
        resources = body.get('resources', [])

        # Validate action
        if action not in ['start', 'stop']:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action. Use "start" or "stop"'})
            }

        # Validate resources
        if not isinstance(resources, list) or len(resources) == 0:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'resources must be a non-empty list. Example: ["ec2", "rds"]'})
            }

        valid_resources = ['ec2', 'rds']
        for resource in resources:
            if resource.lower() not in valid_resources:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Invalid resource "{resource}". Valid options: {valid_resources}'})
                }

        results = {}

        # Control EC2
        if 'ec2' in [r.lower() for r in resources]:
            if action == 'start':
                ec2.start_instances(InstanceIds=[EC2_INSTANCE_ID])
                results['ec2'] = f'Starting EC2 instance {EC2_INSTANCE_ID}'
            else:
                ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])
                results['ec2'] = f'Stopping EC2 instance {EC2_INSTANCE_ID}'

        # Control RDS
        if 'rds' in [r.lower() for r in resources]:
            if action == 'start':
                rds.start_db_instance(DBInstanceIdentifier=RDS_INSTANCE_ID)
                results['rds'] = f'Starting RDS instance {RDS_INSTANCE_ID}'
            else:
                rds.stop_db_instance(DBInstanceIdentifier=RDS_INSTANCE_ID)
                results['rds'] = f'Stopping RDS instance {RDS_INSTANCE_ID}'

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Command executed successfully',
                'results': results
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
