import boto3
import json
from botocore.config import Config

def lambda_handler(event, context):
    
    # Add explicit timeout so boto3 fails fast with a clear error
    config = Config(
        connect_timeout=5,
        read_timeout=10,
        retries={'max_attempts': 1}
    )
    
    try:
        ec2 = boto3.client('ec2', region_name='ap-south-1', config=config)
        response = ec2.describe_instances()
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                
                instances.append({
                    'InstanceId':   instance['InstanceId'],
                    'Name':         name,
                    'State':        instance['State']['Name'],
                    'InstanceType': instance['InstanceType'],
                    'Region':       'ap-south-1',
                    'PublicIP':     instance.get('PublicIpAddress', 'None'),
                    'LaunchTime':   str(instance['LaunchTime'])
                })
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'total_instances': len(instances),
                'instances': instances
            })
        }
    
    # This will now show the REAL error instead of just timing out
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }