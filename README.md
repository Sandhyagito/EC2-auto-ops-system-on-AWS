# EC2-auto-ops-system-on-AWS
EC2 Auto-Ops Control Plane AWS Lambda · API Gateway · EventBridge · SNS · CloudWatch · IAM · Python/boto3

# EC2 Auto-Ops Control Plane ☁️

A fully automated, serverless EC2 operations platform built on AWS. When an EC2 instance stops for any reason, the system detects it in real time, restarts it automatically in under 10 seconds, sends a rich email alert, and logs everything to a live CloudWatch dashboard.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  EC2 Auto-Ops Control Plane                     │
│                                                                 │
│  GET  /ec2/status   ──►  Reporter Lambda  ──►  EC2 API         │
│                                                                 │
│  POST /ec2/action   ──►  Action Lambda    ──►  EC2 API         │
│                                                                 │
│  EC2 Stop Event                                                 │
│       │                                                         │
│       ▼                                                         │
│  EventBridge  ──►  Auto-Heal Lambda  ──►  Start Instance       │
│                         │                                       │
│                         ├──►  SNS  ──►  Email Alert            │
│                         │                                       │
│                         └──►  CloudWatch  ──►  Dashboard       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Browser / curl
      │
      ▼
API Gateway (HTTPS)
      │
      ▼
Lambda Function (Python/boto3)
      │
      ▼
EC2 API ──► JSON Response
      │
      └──► CloudWatch Logs (automatic)
```

---

## ☁️ AWS Services Used

| Service | Purpose |
|---|---|
| **AWS Lambda** | Serverless compute — 3 functions |
| **API Gateway** | HTTP endpoints (GET + POST) |
| **EventBridge** | Real-time EC2 state change detection |
| **SNS** | Email alerting — decoupled notification layer |
| **IAM** | Least-privilege roles for each function |
| **CloudWatch** | Logs, custom metrics, live dashboard |
| **EC2 (boto3)** | Target — instances being monitored and controlled |

---

## 🚀 Features

- **Live Status API** — HTTP endpoint returning real-time EC2 instance details as JSON
- **Control API** — Stop, start, or reboot any instance via a single HTTP POST call
- **Auto-Healing** — Instances that stop unexpectedly are restarted automatically in under 10 seconds
- **Email Alerts** — Rich SNS notifications with instance details, incident timeline, and recovery confirmation
- **CloudWatch Dashboard** — 6 live widgets with 30-second auto-refresh
- **Custom Metrics** — `StopDetected`, `AutoHealSuccess`, `AutoHealFailure` pushed to CloudWatch
- **Structured Logging** — JSON event logs queryable via CloudWatch Logs Insights
- **IAM Least Privilege** — 5 scoped policies, each granting only what is needed

---

## 📁 Project Structure

```
ec2-auto-ops/
│
├── lambda/
│   ├── ec2_status_reporter.py     # GET /ec2/status — reads all EC2 instances
│   ├── ec2_action_handler.py      # POST /ec2/action — stop/start/reboot
│   └── ec2_autoheal_handler.py    # EventBridge triggered — auto-heal + SNS alert
│
├── iam/
│   ├── ec2-instance-actions-policy.json    # Stop/start/reboot permissions
│   ├── sns-publish-autoheal-policy.json    # SNS publish permission
│   └── cloudwatch-metrics-policy.json      # CloudWatch put metrics permission
│
├── eventbridge/
│   └── ec2-stop-rule-pattern.json          # EventBridge event pattern filter
│
└── README.md
```

---

## 🔌 API Endpoints

### GET /ec2/status
Returns real-time status of all EC2 instances in the region.

**Request:**
```bash
curl https://xyz.execute-api.ap-south-1.amazonaws.com/ec2/status
```
---

### POST /ec2/action
Stop, start, or reboot a specific EC2 instance by ID.

**Request:**
```bash
curl -X POST https://xyz.execute-api.ap-south-1.amazonaws.com/ec2/action \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "i-123xxxxxxxx", "action": "stop"}'
```

**Supported actions:** `stop` | `start` | `reboot`

**Response:**
```json
{
  "success": true,
  "action": "stop",
  "instance_id": "i-123xxxxxxxx",
  "message": "Instance i-123xxxxxxxxxx is stopping"
}
```

---

## ⚡ Auto-Heal Flow

When any EC2 instance enters the `stopped` state:

```
1. Instance stops (crash, manual stop, or any reason)
2. EventBridge detects the state change in real time
3. ec2-autoheal-handler Lambda is triggered automatically
4. Lambda fetches instance details (name, type, AZ, IP)
5. Lambda calls start_instances via boto3
6. SNS publishes email alert to subscribed address
7. CloudWatch custom metrics updated (StopDetected, AutoHealSuccess)
8. Structured JSON event logged to CloudWatch Logs
9. Instance back to RUNNING — total time: under 10 seconds
```

**Sample Auto-Heal Email:**
```
Subject: ⚠️ EC2 Auto-Heal: test-instance-01 (i-054a6eeb4eaac01ba) recovered — ap-south-1

INSTANCE DETAILS
----------------
Instance ID    : i-123xxxxxxxxx
Instance Name  : test-instance-01
Instance Type  : t2.micro
Region         : ap-south-1
Availability Z : ap-south-1b
Private IP     : "1.2.3.4"

INCIDENT TIMELINE
-----------------
Stopped At     : 2026-03-19 18:28:50 UTC
Started At     : 2026-03-19 18:28:54 UTC
Recovery Time  : under 10 seconds

ACTION TAKEN
------------
Auto-start triggered successfully by Lambda.
Instance recovered without manual intervention.
```

---

## 📊 CloudWatch Dashboard

Dashboard name: `EC2-AutoOps-Dashboard`

| Widget | Type | Shows |
|---|---|---|
| Auto-Heal Triggers | Line chart | Lambda invocations over time |
| AutoHeal Success vs Fail | Line chart | StopDetected + AutoHealSuccess custom metrics |
| Lambda Duration | Line chart | Recovery time in milliseconds |
| Lambda Errors | Number | Error count — immediate failure visibility |
| EC2 CPU Utilization | Line chart | CPU drop on stop, recovery after auto-heal |
| Auto-Heal Event Log | Logs table | Structured JSON log of every auto-heal event |

**CloudWatch Logs Insights Query:**
```
fields @timestamp, @message
| sort @timestamp desc
| limit 20
```

---

## 🔐 IAM Role Summary

**Role name:** `lambda-ec2-reporter-role`
Used by all 3 Lambda functions.

| Policy | Type | Permissions |
|---|---|---|
| `AmazonEC2ReadOnlyAccess` | AWS Managed | DescribeInstances, DescribeImages, DescribeRegions |
| `AWSLambdaBasicExecutionRole` | AWS Managed | Write logs to CloudWatch |
| `ec2-instance-actions-policy` | Inline | StopInstances, StartInstances, RebootInstances |
| `sns-publish-autoheal-policy` | Inline | sns:Publish to ec2-autoheal-alerts topic only |
| `cloudwatch-metrics-policy` | Inline | PutMetricData, GetMetricData, ListMetrics |

---

## 🛠️ Setup Guide

### Prerequisites
- AWS account with console access
- IAM user with admin permissions
- At least 1 EC2 instance in your target region
- ~60 minutes

### Step 1 — Create IAM Role
1. IAM → Roles → Create Role → AWS Service → Lambda
2. Attach: `AmazonEC2ReadOnlyAccess` + `AWSLambdaBasicExecutionRole`
3. Name: `lambda-ec2-reporter-role`

### Step 2 — Deploy Reporter Lambda
1. Lambda → Create Function → `ec2-status-reporter` → Python 3.12
2. Paste code from `lambda/ec2_status_reporter.py`
3. Deploy → Test

### Step 3 — Create API Gateway
1. API Gateway → Create API → HTTP API
2. Integration: Lambda → `ec2-status-reporter`
3. Route: `GET /ec2/status`
4. Copy Invoke URL from Stages → $default

### Step 4 — Add EC2 Write Permissions
1. IAM → `lambda-ec2-reporter-role` → Add inline policy
2. Paste `iam/ec2-instance-actions-policy.json`
3. Name: `ec2-instance-actions-policy`

### Step 5 — Deploy Action Handler Lambda
1. Lambda → Create Function → `ec2-action-handler` → Python 3.12
2. Paste code from `lambda/ec2_action_handler.py`
3. API Gateway → Add route: `POST /ec2/action` → integrate with `ec2-action-handler`

### Step 6 — Create SNS Topic
1. SNS → Topics → Create topic → Standard → `ec2-autoheal-alerts`
2. Create subscription → Email → your address
3. Confirm subscription from your inbox
4. Add `iam/sns-publish-autoheal-policy.json` to IAM role

### Step 7 — Deploy Auto-Heal Lambda
1. Lambda → Create Function → `ec2-autoheal-handler` → Python 3.12
2. Paste code from `lambda/ec2_autoheal_handler.py`
3. Set timeout to 30 seconds
4. Add `iam/cloudwatch-metrics-policy.json` to IAM role

### Step 8 — Create EventBridge Rule
1. EventBridge → Rules → Create rule
2. Event source: EC2 → EC2 Instance State-change Notification
3. Filter: state = `stopped`
4. Target: Lambda → `ec2-autoheal-handler`
5. Name: `ec2-stop-autoheal-rule`

### Step 9 — Build CloudWatch Dashboard
1. CloudWatch → Dashboards → Create → `EC2-AutoOps-Dashboard`
2. Add 6 widgets (see Dashboard section above)
3. Set auto-refresh to 30 seconds → Save

### Step 10 — Test End to End
1. Stop your EC2 instance manually
2. Do NOT touch Lambda console
3. Watch instance recover automatically
4. Check email inbox for alert
5. Check CloudWatch dashboard for metrics spike

---

## 🌍 Configuration

Update these values in each Lambda function to match your environment:

```python
REGION  = 'ap-south-1'           # Your AWS region
SNS_ARN = 'arn:aws:sns:ap-south-1:YOUR-ACCOUNT-ID:ec2-autoheal-alerts'
```

**Common regions:**

| Region | Code |
|---|---|
| Mumbai | `ap-south-1` |
| Singapore | `ap-southeast-1` |
| US East (N. Virginia) | `us-east-1` |
| US West (Oregon) | `us-west-2` |
| Europe (Ireland) | `eu-west-1` |

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Syntax error in module` | Unclosed bracket when pasting | Select all → delete → paste fresh |
| `Task timed out` | Wrong region in code | Match `region_name` to where instances live |
| `AccessDenied / 403` | IAM policy missing | Check Lambda → Configuration → Permissions |
| `Empty instances []` | No instances in region | Change `region_name` in code |
| `502 Bad Gateway` | Lambda error or missing statusCode | Check CloudWatch Logs for actual error |
| SNS email in spam | Gmail filtering AWS sender | Search `from:no-reply@sns.amazonaws.com` → create filter |
| EventBridge not firing | Rule disabled or wrong filter | Confirm rule Enabled + state filter = `stopped` |
| Infinite loop risk | EventBridge on all state changes | Ensure pattern filters `state: ["stopped"]` only |

---

## 📈 Why This Architecture

**Console is for humans. This API is for applications, automation, and teams without AWS access.**

Real-world use cases:
- **Grafana / Datadog** — call `/ec2/status` every 60 seconds to update dashboards
- **Patch management scripts** — check instance state before patching
- **Ops teams without console access** — check instance health via URL
- **Slack bots** — `/ec2-status` command triggers the API and posts to channel
- **Cross-account visibility** — one API aggregating instances from multiple accounts

**Why EventBridge over polling?**
Purely reactive — no wasted compute, reacts in real time vs checking every N minutes.

**Why SNS over direct email from Lambda?**
Decoupled — add Slack, PagerDuty, or SMS later without changing Lambda code at all.

**Why 3 separate Lambdas?**
Single responsibility — each function does one job. Easier to debug, update, and independently control permissions.

---

## 🔮 Planned Enhancements

- [ ] **DynamoDB logging** — store every auto-heal event for queryable history
- [ ] **Multi-region support** — query instances across all AWS regions in one API call
- [ ] **Slack integration** — post auto-heal events to a Slack channel via webhook
- [ ] **Tag-based filtering** — only auto-heal instances tagged `auto-heal=true`
- [ ] **Step Functions** — orchestrate multi-step remediation workflows with retries
- [ ] **Terraform IaC** — deploy entire stack with one command

---

## 👤 Author

Built as a hands-on serverless learning project to understand how Lambda, API Gateway, and EventBridge work together for EC2 fleet automation.

**Directly applicable to:** EC2 fleet management, patch compliance automation, on-call runbook automation, and CloudWatch observability at scale.

---

## 📄 License

MIT License — free to use, modify, and distribute.
