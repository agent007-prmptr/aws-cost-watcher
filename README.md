# AWS Cost Watcher

Get notified before your AWS bill surprises you.

## Install

```bash
pip install aws-cost-watcher
```

## Usage

```bash
# Set up Discord webhook
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Check current month cost
aws-cost-watcher check

# Set a budget alert at $100
aws-cost-watcher alert --budget 100

# Run as cron (check daily)
0 10 * * * aws-cost-watcher check --budget 200
```

## Features

- 📊 Fetches costs from AWS Cost Explorer
- 🔔 Alerts via Discord, Slack, or stdout
- 💰 Budget thresholds
- 📈 Daily/weekly/monthly cost tracking
