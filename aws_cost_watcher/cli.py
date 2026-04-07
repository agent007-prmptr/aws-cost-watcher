#!/usr/bin/env python3
"""
AWS Cost Watcher - Get notified before your AWS bill surprises you.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import click
import boto3
from botocore.exceptions import ClientError, ProfileNotFound, NoCredentialsError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG_FILES = [
    Path.cwd() / "aws-cost-watcher.yaml",
    Path.cwd() / "aws-cost-watcher.yml",
    Path.home() / ".config" / "aws-cost-watcher.yaml",
    Path.home() / ".aws-cost-watcher.yaml",
]


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from file or environment."""
    import yaml

    config = {
        "budget": None,
        "webhook_url": None,
        "slack_webhook_url": None,
        "region": "us-east-1",
        "profile": None,
        "dry_run": False,
    }

    # Try to load from file
    if config_path and config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f) or {}
            config.update(file_config)
    else:
        for config_file in DEFAULT_CONFIG_FILES:
            if config_file.exists():
                with open(config_file) as f:
                    file_config = yaml.safe_load(f) or {}
                    config.update(file_config)
                break

    # Override with environment variables
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        config["webhook_url"] = os.environ.get("DISCORD_WEBHOOK_URL")
    if os.environ.get("SLACK_WEBHOOK_URL"):
        config["slack_webhook_url"] = os.environ.get("SLACK_WEBHOOK_URL")
    if os.environ.get("AWS_COST_BUDGET"):
        config["budget"] = float(os.environ.get("AWS_COST_BUDGET"))
    if os.environ.get("AWS_PROFILE"):
        config["profile"] = os.environ.get("AWS_PROFILE")

    return config


def get_ce_client(config: dict):
    """Create Cost Explorer client with optional profile."""
    session_kwargs = {"region_name": config.get("region", "us-east-1")}
    if config.get("profile"):
        session_kwargs["profile_name"] = config["profile"]
    return boto3.Session(**session_kwargs).client("ce")


# ─────────────────────────────────────────────────────────────────────────────
# AWS Cost Functions
# ─────────────────────────────────────────────────────────────────────────────

def check_credentials(config: dict) -> bool:
    """Verify AWS credentials are available."""
    try:
        client = get_ce_client(config)
        client.get_cost_and_usage(
            TimePeriod={"Start": "2024-01-01", "End": "2024-01-02"},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        return True
    except ProfileNotFound:
        click.echo("❌ AWS profile not found. Check your ~/.aws/config", err=True)
        return False
    except NoCredentialsError:
        click.echo("❌ No AWS credentials found. Run `aws configure`", err=True)
        return False
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "AccessDeniedException":
            click.echo("❌ Access denied to AWS Cost Explorer. Check IAM permissions.", err=True)
        else:
            click.echo(f"❌ AWS Error: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        return False


def get_costs(config: dict, days: int = 30) -> dict:
    """Fetch costs from AWS Cost Explorer."""
    client = get_ce_client(config)
    today = datetime.now()
    start_date = (today.replace(day=1)).strftime("%Y-%m-%d")  # Start of month
    end_date = today.strftime("%Y-%m-%d")

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    return response


def calculate_total(response: dict) -> float:
    """Calculate total cost from response."""
    if not response:
        return 0.0

    total = 0.0
    for result in response.get("ResultsByTime", []):
        amount = float(result["Total"]["UnblendedCost"]["Amount"])
        total += amount
    return total


def get_service_costs(config: dict) -> list[tuple[str, float]]:
    """Get costs broken down by service."""
    client = get_ce_client(config)
    today = datetime.now()
    start_date = (today.replace(day=1)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    services = []
    for result in response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if amount > 0:
                services.append((group["Keys"][0], amount))

    return sorted(services, key=lambda x: x[1], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


# ─────────────────────────────────────────────────────────────────────────────
# Output Formatting
# ─────────────────────────────────────────────────────────────────────────────

def format_json(data: Any) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format data as ASCII table."""
    if not rows:
        return "No data"
    
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    def fmt_row(cells: List[str]) -> str:
        return " | ".join(str(c).ljust(w) for c, w in zip(cells, col_widths))
    
    sep = "-+-".join("-" * w for w in col_widths)
    return "\n".join([fmt_row(headers), sep, *(fmt_row(r) for r in rows)])


# ─────────────────────────────────────────────────────────────────────────────
# Budget Thresholds
# ─────────────────────────────────────────────────────────────────────────────

def check_budget_thresholds(config: dict, cost: float) -> List[Dict[str, Any]]:
    """Check cost against multiple budget thresholds."""
    budget = config.get("budget")
    if not budget:
        return []
    
    # Default thresholds: 80% warning, 100% critical
    thresholds = config.get("thresholds", [
        {"percent": 80, "level": "warning", "emoji": "⚠️", "message": "Approaching budget"},
        {"percent": 100, "level": "critical", "emoji": "🚨", "message": "Budget exceeded"},
    ])
    
    alerts = []
    for t in thresholds:
        threshold_amount = budget * t["percent"] / 100
        if cost >= threshold_amount:
            alerts.append({
                "level": t.get("level", "warning"),
                "percent": t["percent"],
                "amount": threshold_amount,
                "emoji": t.get("emoji", "⚠️"),
                "message": t.get("message", f"{t['percent']}% of budget used"),
            })
    
    return alerts


def send_webhook(url: str, message: str, cost: float, service: str = "AWS") -> bool:
    """Send notification to webhook."""
    import urllib.request
    import urllib.error

    data = {
        "content": None,
        "embeds": [
            {
                "title": f"💰 {service} Cost Alert",
                "description": message,
                "color": 5815263,  # Green-ish
                "fields": [
                    {"name": "Current Cost", "value": format_currency(cost), "inline": True},
                ],
                "footer": {"text": "AWS Cost Watcher"},
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        click.echo(f"❌ Webhook HTTP error: {e.code} {e.reason}", err=True)
        return False
    except urllib.error.URLError as e:
        click.echo(f"❌ Webhook error: {e.reason}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Failed to send webhook: {e}", err=True)
        return False


def send_discord(config: dict, message: str, cost: float) -> bool:
    """Send Discord notification."""
    url = config.get("webhook_url")
    if not url:
        return False
    return send_webhook(url, message, cost, "AWS")


def send_slack(config: dict, message: str, cost: float) -> bool:
    """Send Slack notification."""
    url = config.get("slack_webhook_url")
    if not url:
        return False

    # Slack uses slightly different format
    data = {
        "text": f"💰 *AWS Cost Alert*\n{message}\n*Current: {format_currency(cost)}*",
    }

    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception as e:
        click.echo(f"❌ Slack webhook error: {e}", err=True)
        return False


def notify(config: dict, cost: float, budget: Optional[float] = None):
    """Send notifications to configured channels."""
    if budget is None:
        budget = config.get("budget")

    if not budget:
        return

    alerts = check_budget_thresholds(config, cost)
    
    if not alerts:
        pct = (cost / budget * 100) if budget > 0 else 0
        click.echo(f"✅ Under budget: {format_currency(cost)} / {format_currency(budget)} ({pct:.0f}%)")
        return

    # Send alerts for each threshold triggered
    for alert in alerts:
        msg = f"{alert['emoji']} {alert['message']}: {format_currency(cost)} of {format_currency(budget)}"
        if config.get("dry_run"):
            msg += " [DRY RUN]"

        sent = []

        if send_discord(config, msg, cost):
            sent.append("Discord")
        if send_slack(config, msg, cost):
            sent.append("Slack")

        if sent:
            click.echo(f"✅ Alert sent to: {', '.join(sent)}")
        else:
            click.echo(msg)


def get_daily_costs(config: dict, days: int = 30) -> List[Dict[str, Any]]:
    """Get daily cost data for trend analysis."""
    client = get_ce_client(config)
    today = datetime.now()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
    )

    daily = []
    for result in response.get("ResultsByTime", []):
        amount = float(result["Total"]["UnblendedCost"]["Amount"])
        daily.append({
            "date": result["TimePeriod"]["Start"],
            "amount": amount,
        })
    return daily


# ─────────────────────────────────────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.option("--config", "-c", type=click.Path(path_type=Path), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, config, verbose):
    """AWS Cost Watcher - Monitor your AWS spending."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--budget", "-b", type=float, help="Budget threshold")
@click.option("--region", "-r", help="AWS region")
@click.option("--profile", "-p", help="AWS profile")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
@click.pass_context
def check(ctx, budget, region, profile, dry_run):
    """Check current AWS costs."""
    config = ctx.obj["config"]

    # CLI args override config
    if budget is not None:
        config["budget"] = budget
    if region:
        config["region"] = region
    if profile:
        config["profile"] = profile
    if dry_run:
        config["dry_run"] = True

    click.echo("🔍 Checking AWS costs...")

    # Check credentials first
    if not check_credentials(config):
        sys.exit(1)

    try:
        # Get monthly costs
        response = get_costs(config)
        monthly_total = calculate_total(response)

        click.echo(f"📅 This month: {format_currency(monthly_total)}")

        # Get service breakdown
        services = get_service_costs(config)
        if services:
            click.echo("\n📊 Top services:")
            for svc, amount in services[:5]:
                click.echo(f"   {svc}: {format_currency(amount)}")

        # Check budget
        if config.get("budget"):
            notify(config, monthly_total)
        elif config.get("dry_run"):
            click.echo("💡 Set --budget to enable alerts")

    except ClientError as e:
        click.echo(f"❌ AWS Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--budget", "-b", type=float, required=True, help="Budget threshold")
@click.option("--region", "-r", help="AWS region")
@click.option("--profile", "-p", help="AWS profile")
@click.pass_context
def alert(ctx, budget, region, profile):
    """Set a budget alert threshold."""
    config = ctx.obj["config"]

    if region:
        config["region"] = region
    if profile:
        config["profile"] = profile

    if not check_credentials(config):
        sys.exit(1)

    # Verify we can connect
    try:
        response = get_costs(config)
        current = calculate_total(response)
    except ClientError as e:
        click.echo(f"❌ AWS Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"📊 Current month cost: {format_currency(current)}")
    click.echo(f"🔔 Budget alert set: {format_currency(budget)}")

    if current >= budget:
        notify(config, current, budget)
    else:
        click.echo(f"✅ You have {format_currency(budget - current)} remaining")


@cli.command()
@click.pass_context
def services(ctx):
    """Show cost breakdown by service."""
    config = ctx.obj["config"]

    if not check_credentials(config):
        sys.exit(1)

    click.echo("🔍 Fetching service costs...")

    try:
        services = get_service_costs(config)

        if not services:
            click.echo("No costs found this month")
            return

        # Default to table output; can be extended later
        total = sum(amount for _, amount in services)
        click.echo(f"\n📊 Costs by service ({datetime.now().strftime('%B %Y')}):")
        headers = ["Service", "Cost", "Percent"]
        rows = [
            [svc, format_currency(amount), f"{(amount / total * 100) if total > 0 else 0:.1f}%"]
            for svc, amount in services
        ]
        click.echo(format_table(headers, rows))
        click.echo(f"\n   Total: {format_currency(total)}")

    except ClientError as e:
        click.echo(f"❌ AWS Error: {e}", err=True)
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Additional CLI Commands
# ─────────────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def forecast(ctx, format):
    """Forecast end-of-month cost based on current trend."""
    config = ctx.obj["config"]
    if not check_credentials(config):
        sys.exit(1)
    click.echo("🔮 Calculating cost forecast...")
    today = datetime.now()
    # Determine days in current month
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    days_in_month = (next_month - timedelta(days=1)).day
    days_elapsed = today.day
    daily_costs = get_daily_costs(config, days=days_elapsed)
    if not daily_costs:
        click.echo("No cost data available for forecast")
        return
    total_so_far = sum(d["amount"] for d in daily_costs)
    avg_daily = total_so_far / days_elapsed if days_elapsed else 0
    forecast_total = avg_daily * days_in_month
    if format == "json":
        data = {
            "month": today.strftime("%B %Y"),
            "days_elapsed": days_elapsed,
            "days_total": days_in_month,
            "current_total": total_so_far,
            "avg_daily": avg_daily,
            "forecast_total": forecast_total,
        }
        click.echo(format_json(data))
    else:
        click.echo(f"\n📈 Cost Forecast ({today.strftime('%B %Y')}):")
        click.echo(f"   Days elapsed: {days_elapsed}/{days_in_month}")
        click.echo(f"   Current total: {format_currency(total_so_far)}")
        click.echo(f"   Average daily: {format_currency(avg_daily)}")
        click.echo(f"   Forecasted total: {format_currency(forecast_total)}")
        # Budget comparison
        budget = config.get("budget")
        if budget:
            pct = (forecast_total / budget * 100) if budget else 0
            if pct > 100:
                click.echo(f"   🚨 Forecast exceeds budget by {format_currency(forecast_total - budget)} ({pct:.0f}%)")
            elif pct > 80:
                click.echo(f"   ⚠️ Forecast is {pct:.0f}% of budget")
            else:
                click.echo(f"   ✅ Forecast is {pct:.0f}% of budget")

@cli.command()
@click.option("--months", "-m", type=int, default=6, help="Number of months to show")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def history(ctx, months, format):
    """Show cost history over time."""
    config = ctx.obj["config"]
    if not check_credentials(config):
        sys.exit(1)
    click.echo(f"📊 Fetching {months} months of cost history...")
    client = get_ce_client(config)
    today = datetime.now()
    start_date = (today.replace(day=1) - timedelta(days=months*31)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )
    monthly_data = []
    for result in response.get("ResultsByTime", []):
        amount = float(result["Total"]["UnblendedCost"]["Amount"])
        period_start = datetime.strptime(result["TimePeriod"]["Start"], "%Y-%m-%d")
        monthly_data.append({
            "month": period_start.strftime("%Y-%m"),
            "display_month": period_start.strftime("%b %Y"),
            "amount": amount,
        })
    if format == "json":
        click.echo(format_json({"months": monthly_data}))
    else:
        if monthly_data:
            headers = ["Month", "Cost"]
            rows = [[d["display_month"], format_currency(d["amount"])] for d in monthly_data]
            click.echo(format_table(headers, rows))
            avg = sum(d["amount"] for d in monthly_data) / len(monthly_data)
            click.echo(f"\n   Average: {format_currency(avg)}")
        else:
            click.echo("No historical data found")

@cli.command()
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def compare(ctx, format):
    """Compare current month to previous month."""
    config = ctx.obj["config"]
    if not check_credentials(config):
        sys.exit(1)
    click.echo("🔍 Comparing current vs previous month...")
    client = get_ce_client(config)
    today = datetime.now()
    current_start = today.replace(day=1).strftime("%Y-%m-%d")
    current_end = today.strftime("%Y-%m-%d")
    prev_month = (today.replace(day=1) - timedelta(days=1))
    prev_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_end = prev_month.strftime("%Y-%m-%d")
    # Current month cost
    current_resp = client.get_cost_and_usage(
        TimePeriod={"Start": current_start, "End": current_end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )
    current_cost = calculate_total(current_resp)
    # Previous month cost
    prev_resp = client.get_cost_and_usage(
        TimePeriod={"Start": prev_start, "End": prev_end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
    )
    prev_cost = calculate_total(prev_resp)
    diff = current_cost - prev_cost
    pct_change = (diff / prev_cost * 100) if prev_cost else 0
    if format == "json":
        data = {
            "current_month": {"name": today.strftime("%B %Y"), "cost": current_cost},
            "previous_month": {"name": prev_month.strftime("%B %Y"), "cost": prev_cost},
            "difference": diff,
            "percent_change": pct_change,
        }
        click.echo(format_json(data))
    else:
        click.echo("\n📊 Month-over-month comparison:")
        headers = ["Period", "Cost"]
        rows = [
            [today.strftime("%b %Y (current)"), format_currency(current_cost)],
            [prev_month.strftime("%b %Y (previous)"), format_currency(prev_cost)],
        ]
        click.echo(format_table(headers, rows))
        if diff > 0:
            click.echo(f"\n   📈 Increase: {format_currency(diff)} ({pct_change:+.1f}%)")
        elif diff < 0:
            click.echo(f"\n   📉 Decrease: {format_currency(-diff)} ({pct_change:.1f}%)")
        else:
            click.echo("\n   ➡️ No change")

@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing config")
@click.pass_context
def init(ctx, force):
    """Create configuration file interactively."""
    config_path = Path("aws-cost-watcher.yaml")
    if config_path.exists() and not force:
        click.echo(f"❌ Config file already exists: {config_path}")
        click.echo("Use --force to overwrite or edit it manually")
        return
    click.echo("🚀 AWS Cost Watcher Setup\n")
    budget = click.prompt("Monthly budget (USD)", type=float, default=100.0)
    region = click.prompt("AWS region", default="us-east-1")
    profile = click.prompt("AWS profile (optional)", default="", show_default=False)
    click.echo("\n📱 Notification setup (optional):")
    discord_url = click.prompt("Discord webhook URL", default="", show_default=False)
    slack_url = click.prompt("Slack webhook URL", default="", show_default=False)
    config_data = {"budget": budget, "region": region}
    if profile:
        config_data["profile"] = profile
    if discord_url:
        config_data["webhook_url"] = discord_url
    if slack_url:
        config_data["slack_webhook_url"] = slack_url
    config_data["thresholds"] = [
        {"percent": 80, "level": "warning", "emoji": "⚠️", "message": "Approaching budget"},
        {"percent": 100, "level": "critical", "emoji": "🚨", "message": "Budget exceeded"},
    ]
    import yaml
    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    click.echo(f"\n✅ Config written to: {config_path}")
    click.echo("🧪 Test it: aws-cost-watcher check")
    click.echo(f"💡 Edit manually if needed: {config_path}")



def main():
    cli(obj={})


if __name__ == "__main__":
    main()