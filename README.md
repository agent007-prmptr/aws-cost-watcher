# AWS Cost Watcher

Get notified before your AWS bill surprises you.

## Install

```bash
pip install aws-cost-watcher
```

## Quick Start

```bash
# Check your current month's costs
aws-cost-watcher check

# Set a budget alert at $100
aws-cost-watcher alert --budget 100

# See costs broken down by service
aws-cost-watcher services
```

## Configuration

Create a config file (optional):

```bash
# In current directory or ~/.config/aws-cost-watcher.yaml
cp aws-cost-watcher.example.yaml aws-cost-watcher.yaml
# Edit with your webhook URLs and budget
```

### Environment Variables

You can also use environment variables:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export AWS_COST_BUDGET=100
export AWS_PROFILE=default
```

## Usage

### Check Costs

```bash
# Basic check (current month)
aws-cost-watcher check

# With budget alert
aws-cost-watcher check --budget 200

# From specific AWS profile
aws-cost-watcher check --profile my-aws-profile --budget 150
```

### Set Budget Alert

```bash
# Get notified when you hit the threshold
aws-cost-watcher alert --budget 100
```

### View Service Breakdown

```bash
# See which services are costing the most
aws-cost-watcher services
```

### Set Up Cron

```bash
# Check daily at 10am
0 10 * * * aws-cost-watcher check --budget 200 >> /var/log/aws-cost.log 2>&1
```

## Features

- 📊 Fetches costs from AWS Cost Explorer
- 🔔 Alerts via Discord or Slack webhooks
- 💰 Configurable budget thresholds
- 📈 Monthly and daily cost tracking
- 🔧 Service-level cost breakdown
- ⚙️ YAML configuration file support
- 🔒 AWS profile support (not just default credentials)

## Requirements

- AWS credentials with `ce:GetCostAndUsage` permission
- Python 3.8+
- boto3

## IAM Policy

Attach this to your IAM user/role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ce:GetCostAndUsage",
      "Resource": "*"
    }
  ]
}
```

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/yourusername/aws-cost-watcher.git
cd aws-cost-watcher
pip install -e .

# Run tests
pip install -e ".[test]"
pytest
```

## License

MIT