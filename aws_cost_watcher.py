#!/usr/bin/env python3
"""
AWS Cost Watcher - Get notified before your AWS bill surprises you.
"""

import argparse
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Install boto3: pip install boto3")
    exit(1)


def get_daily_costs():
    """Fetch daily costs from AWS Cost Explorer."""
    try:
        client = boto3.client('ce', region_name='us-east-1')
        
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'SERVICE', 'Key': 'SERVICE'}]
        )
        
        return response
    except ClientError as e:
        print(f"AWS Error: {e}")
        print("Make sure you have AWS credentials configured (aws configure)")
        return None


def calculate_total(response):
    """Calculate total cost from response."""
    if not response:
        return 0
    
    total = 0
    for result in response.get('ResultsByTime', []):
        for group in result.get('Groups', []):
            amount = float(group['Metrics']['UnblendedCost']['Amount'])
            total += amount
    
    return total


def format_cost(amount):
    """Format cost as currency."""
    return f"${amount:.2f}"


def send_discord_webhook(webhook_url, message, cost):
    """Send alert to Discord."""
    import urllib.request
    import urllib.error
    
    data = {
        "content": f"💰 **AWS Cost Alert**\n{message}\nCurrent: **{format_cost(cost)}**"
    }
    
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 204
    except urllib.error.URLError as e:
        print(f"Discord webhook error: {e}")
        return False


def check_costs(budget=None, webhook_url=None):
    """Main function to check AWS costs."""
    print("🔍 Checking AWS costs...")
    
    response = get_daily_costs()
    if not response:
        print("❌ Failed to get AWS costs")
        return
    
    total = calculate_total(response)
    print(f"📊 Last 30 days: {format_cost(total)}")
    
    # Get current month cost only
    client = boto3.client('ce', region_name='us-east-1')
    today = datetime.now()
    start_of_month = today.replace(day=1).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    monthly_response = client.get_cost_and_usage(
        TimePeriod={'Start': start_of_month, 'End': end_date},
        Granularity='DAILY',
        Metrics=['UnblendedCost']
    )
    
    monthly_total = sum(
        float(r['Total']['UnblendedCost']['Amount'])
        for r in monthly_response.get('ResultsByTime', [])
    )
    
    print(f"📅 This month (to date): {format_cost(monthly_total)}")
    
    if budget and monthly_total >= budget:
        msg = f"⚠️ You've used {format_cost(monthly_total)} of your {format_cost(budget)} budget"
        print(f"🚨 {msg}")
        
        if webhook_url:
            if send_discord_webhook(webhook_url, msg, monthly_total):
                print("✅ Discord notification sent")
    else:
        print("✅ Under budget")


def main():
    parser = argparse.ArgumentParser(description='AWS Cost Watcher')
    parser.add_argument('command', choices=['check', 'alert'], default='check')
    parser.add_argument('--budget', type=float, help='Budget threshold')
    parser.add_argument('--webhook', type=str, help='Discord webhook URL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    
    args = parser.parse_args()
    
    # Get webhook from env if not provided
    webhook = args.webhook or os.environ.get('DISCORD_WEBHOOK_URL')
    
    if args.command == 'check' or args.command == 'alert':
        check_costs(budget=args.budget, webhook_url=webhook)


if __name__ == '__main__':
    main()
