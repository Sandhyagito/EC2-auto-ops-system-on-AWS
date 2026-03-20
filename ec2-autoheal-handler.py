import boto3
import json
from datetime import datetime
from botocore.config import Config

# ---- CONFIGURATION ----
REGION  = 'ap-south-1'
SNS_ARN = 'arn:aws:sns:ap-south-1:691591070432:ec2-autoheal-alerts'
# -----------------------

def put_cloudwatch_metric(cw_client, metric_name, value, instance_id, instance_name):
    """Push a custom metric to CloudWatch for dashboard visibility."""
    cw_client.put_metric_data(
        Namespace='EC2AutoHeal',
        MetricData=[{
            'MetricName': metric_name,
            'Value':      value,
            'Unit':       'Count',
            'Dimensions': [
                {'Name': 'InstanceId',   'Value': instance_id},
                {'Name': 'InstanceName', 'Value': instance_name},
                {'Name': 'Region',       'Value': REGION}
            ]
        }]
    )


def get_instance_details(ec2_client, instance_id):
    """Get full instance details for the alert email."""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]

        name = 'N/A'
        for tag in instance.get('Tags', []):
            if tag['Key'] == 'Name':
                name = tag['Value']

        return {
            'name':          name,
            'instance_type': instance.get('InstanceType', 'N/A'),
            'public_ip':     instance.get('PublicIpAddress', 'Not assigned'),
            'private_ip':    instance.get('PrivateIpAddress', 'N/A'),
            'launch_time':   str(instance.get('LaunchTime', 'N/A')),
            'az':            instance.get('Placement', {}).get('AvailabilityZone', 'N/A'),
            'state':         instance['State']['Name']
        }
    except Exception as e:
        print(f"Could not fetch instance details: {str(e)}")
        return {
            'name':          'N/A',
            'instance_type': 'N/A',
            'public_ip':     'Not assigned',
            'private_ip':    'N/A',
            'launch_time':   'N/A',
            'az':            'N/A',
            'state':         'N/A'
        }


def send_sns_alert(sns_client, instance_id, details, action_taken, stopped_time, started_time):
    """Publish a rich alert email via SNS."""
    message = f"""
==============================================
  ⚠️  EC2 AUTO-HEAL REPORT — {REGION}
==============================================

INSTANCE DETAILS
----------------
Instance ID    : {instance_id}
Instance Name  : {details['name']}
Instance Type  : {details['instance_type']}
Region         : {REGION}
Availability Z : {details['az']}
Private IP     : {details['private_ip']}
Public IP      : {details['public_ip']}
Original Launch: {details['launch_time']}

INCIDENT TIMELINE
-----------------
🔴 Stopped At  : {stopped_time}
🟢 Started At  : {started_time}
⏱️  Recovery   : under 10 seconds

ACTION TAKEN
------------
{action_taken}

Current State  : Instance is back RUNNING ✅

----------------------------------------------
CloudWatch Dashboard:
https://console.aws.amazon.com/cloudwatch/home?region={REGION}
==============================================
"""
    sns_client.publish(
        TopicArn=SNS_ARN,
        Subject=f'⚠️ EC2 Auto-Heal: {details["name"]} ({instance_id}) recovered — {REGION}',
        Message=message
    )


def lambda_handler(event, context):

    print(f"Event received: {json.dumps(event)}")

    # ── Extract instance details from EventBridge ──
    try:
        instance_id = event['detail']['instance-id']
        state       = event['detail']['state']
    except KeyError:
        instance_id = event.get('instance_id', 'UNKNOWN')
        state       = event.get('state', 'stopped')

    print(f"Instance {instance_id} entered state: {state}")

    if state != 'stopped':
        print(f"State is '{state}' — no action needed.")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'No action for state: {state}'})
        }

    stopped_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # ── Set up AWS clients ──
    config     = Config(connect_timeout=5, read_timeout=10, retries={'max_attempts': 2})
    ec2_client = boto3.client('ec2', region_name=REGION, config=config)
    sns_client = boto3.client('sns', region_name=REGION, config=config)
    cw_client  = boto3.client('cloudwatch', region_name=REGION, config=config)

    # ── Get instance details ──
    details = get_instance_details(ec2_client, instance_id)
    print(f"Instance: {details['name']} | Type: {details['instance_type']} | AZ: {details['az']}")

    # ── Push metric: StopDetected ──
    put_cloudwatch_metric(cw_client, 'StopDetected', 1, instance_id, details['name'])
    print(f"✅ CloudWatch metric StopDetected pushed")

    # ── Attempt auto-start ──
    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        started_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"✅ Auto-start triggered for {instance_id}")
        action_taken = "✅ Auto-start triggered successfully by Lambda.\n   Instance recovered without manual intervention."

        # ── Push metric: AutoHealSuccess ──
        put_cloudwatch_metric(cw_client, 'AutoHealSuccess', 1, instance_id, details['name'])
        print(f"✅ CloudWatch metric AutoHealSuccess pushed")

    except Exception as e:
        started_time = 'FAILED'
        print(f"❌ Failed to start: {str(e)}")
        action_taken = f"❌ Auto-start FAILED.\n   Error: {str(e)}"

        # ── Push metric: AutoHealFailure ──
        put_cloudwatch_metric(cw_client, 'AutoHealFailure', 1, instance_id, details['name'])
        print(f"✅ CloudWatch metric AutoHealFailure pushed")

    # ── Send SNS alert ──
    try:
        send_sns_alert(sns_client, instance_id, details, action_taken, stopped_time, started_time)
        print(f"✅ SNS alert sent")
    except Exception as e:
        print(f"❌ SNS failed: {str(e)}")

    # ── Log structured summary for CloudWatch Logs Insights ──
    print(json.dumps({
        "event":          "AutoHeal",
        "instance_id":    instance_id,
        "instance_name":  details['name'],
        "instance_type":  details['instance_type'],
        "az":             details['az'],
        "private_ip":     details['private_ip'],
        "public_ip":      details['public_ip'],
        "stopped_at":     stopped_time,
        "started_at":     started_time,
        "action":         "start",
        "region":         REGION
    }))

    return {
        'statusCode': 200,
        'body': json.dumps({
            'instance_id':   instance_id,
            'instance_name': details['name'],
            'stopped_at':    stopped_time,
            'started_at':    started_time,
            'action':        action_taken
        })
    }