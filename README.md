# EC2-auto-ops-system-on-AWS
EC2 Auto-Ops Control Plane AWS Lambda · API Gateway · EventBridge · SNS · CloudWatch · IAM · Python/boto3

# EC2 Auto-Ops Control Plane ☁️

A serverless system that monitors EC2 instances, automatically restarts them if they stop, and sends an email alert — all without any human involvement.

---

## What It Does

- **GET /ec2/status** — call a URL, get real-time EC2 instance details as JSON
- **Auto-Heal** — when any instance stops, EventBridge detects it and Lambda restarts it in under 10 seconds
- **Email Alert** — SNS sends a notification with instance details and recovery time
- **CloudWatch Dashboard** — live monitoring with auto-refresh every 30 seconds

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
EventBridge → Lambda → Restart instance
                  │
                  ├── SNS → Email alert
                  └── CloudWatch → Dashboard updated
```

---

## AWS Services Used

- **Lambda** — Python 3.12, serverless compute
- **API Gateway** — HTTP endpoint
- **EventBridge** — real-time EC2 stop event detection
- **SNS** — email notifications
- **IAM** — least-privilege roles
- **CloudWatch** — logs, custom metrics, live dashboard

---

## Setup

### Prerequisites
- AWS account
- At least one EC2 instance in your target region

### Steps
1. Create an IAM role with EC2 read, SNS publish, and CloudWatch permissions
2. Deploy `ec2_status_reporter` Lambda — attach to `GET /ec2/status` via API Gateway
3. Deploy `ec2_autoheal_handler` Lambda — triggered by EventBridge on EC2 stop events
4. Create an SNS topic and subscribe your email
5. Create an EventBridge rule filtering `EC2 Instance State-change Notification` where `state = stopped`
6. Build a CloudWatch dashboard to monitor Lambda invocations, duration, errors, and EC2 CPU

> Update `REGION` and `SNS_ARN` in each Lambda function to match your environment before deploying.

---

## How to Test

1. Deploy the status Lambda and call the API URL in your browser — you'll see your instances as JSON
2. Stop any EC2 instance manually — within 30 seconds it restarts itself and you receive an email

---

## IAM Permissions Required

| Permission | Why |
|---|---|
| `AmazonEC2ReadOnlyAccess` | Read instance details |
| `AWSLambdaBasicExecutionRole` | Write logs to CloudWatch |
| `ec2:StopInstances`, `ec2:StartInstances`, `ec2:RebootInstances` | Auto-heal actions |
| `sns:Publish` | Send email alerts |
| `cloudwatch:PutMetricData` | Push custom metrics to dashboard |

---

## Author

Built as a hands-on project to learn serverless architecture on AWS — Lambda, API Gateway, EventBridge, and CloudWatch working together to automate EC2 operations.
