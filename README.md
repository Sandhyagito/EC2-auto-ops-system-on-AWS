# EC2-auto-ops-system-on-AWS
EC2 Auto-Ops Control Plane AWS Lambda · API Gateway · EventBridge · SNS · CloudWatch · IAM · Python/boto3

# EC2 Auto-Ops Control Plane ☁️

A serverless system that **automatically restarts EC2 instances** when they stop — and emails you when it does.

Built with AWS Lambda, API Gateway, EventBridge, SNS, and CloudWatch.

---

## What It Does

| Feature | How |
|---|---|
| Check EC2 status via URL | API Gateway → Lambda → EC2 |
| Auto-restart stopped instances | EventBridge → Lambda → EC2 |
| Email alert when instance recovers | Lambda → SNS → Your inbox |
| Live monitoring dashboard | CloudWatch — auto-refreshes every 30 sec |

---

## Architecture

```
GET /ec2/status
      │
      ▼
API Gateway → Lambda → EC2 API → JSON response

EC2 instance stops
      │
      ▼
EventBridge (detects it automatically)
      │
      ▼
Lambda (restarts it in under 10 seconds)
      │
      ├── SNS → Email alert to you
      └── CloudWatch → Dashboard updated
```

---

## Project Setup

### Step 1 — IAM Role
Create a role called `lambda-ec2-reporter-role` and attach:
- `AmazonEC2ReadOnlyAccess`
- `AWSLambdaBasicExecutionRole`

### Step 2 — Lambda: EC2 Status Reporter
- Runtime: Python 3.12
- Role: `lambda-ec2-reporter-role`

```python
import boto3, json
from botocore.config import Config

def lambda_handler(event, context):
    config = Config(connect_timeout=5, read_timeout=10, retries={'max_attempts': 1})
    ec2 = boto3.client('ec2', region_name='ap-south-1', config=config)

    try:
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
            'body': json.dumps({'total_instances': len(instances), 'instances': instances})
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```

### Step 3 — API Gateway
- Type: HTTP API
- Route: `GET /ec2/status`
- Integration: `ec2-status-reporter` Lambda

Test it in your browser:
```
https://YOUR-API-ID.execute-api.ap-south-1.amazonaws.com/ec2/status
```

**Response looks like this:**
```json
{
  "total_instances": 1,
  "instances": [{
    "InstanceId": "i-123333333333333",
    "Name": "test-instance-01",
    "State": "running",
    "InstanceType": "t2.micro",
    "Region": "ap-south-1",
    "PublicIP": "111111",
    "LaunchTime": "2026-03-19 16:17:40+00:00"
  }]
}
```

### Step 4 — SNS Email Alert
- Create topic: `ec2-autoheal-alerts` (Standard)
- Subscribe your email → confirm the link in your inbox

### Step 5 — Lambda: Auto-Heal Handler
- Runtime: Python 3.12
- Role: `lambda-ec2-reporter-role`
- Timeout: 30 seconds
- Add these extra IAM inline policies to the role:
  - `ec2:StopInstances`, `ec2:StartInstances`, `ec2:RebootInstances`
  - `sns:Publish` on your SNS topic
  - `cloudwatch:PutMetricData`

```python
import boto3, json
from datetime import datetime
from botocore.config import Config

REGION  = 'ap-south-1'
SNS_ARN = 'arn:aws:sns:ap-south-1:YOUR-ACCOUNT-ID:ec2-autoheal-alerts'

def lambda_handler(event, context):
    try:
        instance_id = event['detail']['instance-id']
        state       = event['detail']['state']
    except KeyError:
        instance_id = event.get('instance_id', 'UNKNOWN')
        state       = event.get('state', 'stopped')

    if state != 'stopped':
        return {'statusCode': 200, 'body': 'No action needed'}

    stopped_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    config     = Config(connect_timeout=5, read_timeout=10, retries={'max_attempts': 2})
    ec2_client = boto3.client('ec2', region_name=REGION, config=config)
    sns_client = boto3.client('sns', region_name=REGION, config=config)

    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        started_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        action = 'Auto-start triggered successfully'
    except Exception as e:
        started_time = 'FAILED'
        action = f'Auto-start FAILED: {str(e)}'

    sns_client.publish(
        TopicArn=SNS_ARN,
        Subject=f'EC2 Auto-Heal: {instance_id} recovered — {REGION}',
        Message=f'Instance : {instance_id}\nStopped  : {stopped_time}\nStarted  : {started_time}\nAction   : {action}'
    )

    return {'statusCode': 200, 'body': json.dumps({'instance_id': instance_id, 'action': action})}
```

### Step 6 — EventBridge Rule
- Name: `ec2-stop-autoheal-rule`
- Event source: EC2 → EC2 Instance State-change Notification
- Filter: state = `stopped`
- Target: `ec2-autoheal-handler` Lambda

Event pattern:
```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": { "state": ["stopped"] }
}
```

### Step 7 — CloudWatch Dashboard
- Create dashboard: `EC2-AutoOps-Dashboard`
- Add widgets: Lambda Invocations, Lambda Duration, Lambda Errors, EC2 CPU Utilization
- Set auto-refresh: 30 seconds

---

## Testing

**Test the status API** — paste in browser:
```
https://YOUR-API-ID.execute-api.ap-south-1.amazonaws.com/ec2/status
```

**Test auto-heal** — just stop your EC2 instance and wait:
```
Stop instance → wait 30 seconds → instance restarts itself → email arrives
```

---

## AWS Services Used

- **Lambda** — serverless functions (Python 3.12)
- **API Gateway** — HTTP endpoint
- **EventBridge** — real-time EC2 event detection
- **SNS** — email notifications
- **IAM** — least-privilege roles
- **CloudWatch** — logs and dashboard

---

## Common Errors

| Error | Fix |
|---|---|
| Task timed out | Wrong region — update `region_name` in code |
| Empty instances `[]` | No instances in that region |
| AccessDenied | IAM role missing a policy |
| SNS email not arriving | Check spam — search `from:no-reply@sns.amazonaws.com` |
| EventBridge not triggering | Confirm rule is Enabled and filter is `state: stopped` |

---

## Author

Built as a hands-on serverless project to learn AWS Lambda, API Gateway, and event-driven automation with EC2.

