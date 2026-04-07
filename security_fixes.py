#!/usr/bin/env python3
"""
Security fixes for AWS Cost Watcher
"""

import urllib.parse
from typing import Optional
from botocore.exceptions import ClientError

# ─────────────────────────────────────────────────────────────────────────────
# Security & Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL is safe (prevent SSRF)."""
    if not url or not url.strip():
        return True  # Empty URLs are okay
    
    try:
        parsed = urllib.parse.urlparse(url)
        
        # Only allow HTTP/HTTPS
        if parsed.scheme not in {'http', 'https'}:
            return False
        
        # Must have a netloc (domain)
        if not parsed.netloc:
            return False
        
        # Block localhost, private IPs (basic SSRF protection)
        hostname = parsed.hostname
        if hostname:
            # Block localhost variants
            if hostname.lower() in {'localhost', '127.0.0.1', '0.0.0.0'}:
                return False
            # Block private IP ranges (basic check)
            if hostname.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.')):
                return False
        
        return True
        
    except Exception:
        return False


def validate_budget(budget_str: str) -> Optional[float]:
    """Safely validate and convert budget string to float."""
    try:
        budget = float(budget_str)
        # Budget must be positive and reasonable (max $1M/month)
        if budget <= 0 or budget > 1_000_000:
            return None
        return budget
    except (ValueError, TypeError):
        return None


def sanitize_aws_error(error: Exception) -> str:
    """Sanitize AWS error messages to avoid info disclosure."""
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        
        # Safe error messages that don't leak info
        safe_messages = {
            'AccessDenied': 'Access denied to AWS Cost Explorer. Check IAM permissions.',
            'InvalidParameterValue': 'Invalid parameter provided to AWS API.',
            'ThrottlingException': 'AWS API rate limit exceeded. Please try again later.',
            'ServiceUnavailable': 'AWS service temporarily unavailable.',
            'UnauthorizedOperation': 'Insufficient permissions for this operation.',
        }
        
        return safe_messages.get(error_code, 'AWS API error occurred. Check your configuration.')
    
    # For other exceptions, return generic message
    return 'An error occurred while processing your request.'


# Fixes to apply:

# 1. In load_config(), replace:
#    config["budget"] = float(os.environ.get("AWS_COST_BUDGET"))
# With:
#    budget_val = validate_budget(os.environ.get("AWS_COST_BUDGET"))
#    if budget_val is not None:
#        config["budget"] = budget_val

# 2. In load_config(), add webhook validation:
#    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
#    if webhook_url and validate_webhook_url(webhook_url):
#        config["webhook_url"] = webhook_url
#    
#    slack_url = os.environ.get("SLACK_WEBHOOK_URL") 
#    if slack_url and validate_webhook_url(slack_url):
#        config["slack_webhook_url"] = slack_url

# 3. In init command, add validation:
#    if discord_url and not validate_webhook_url(discord_url):
#        click.echo("❌ Invalid Discord webhook URL")
#        return
#    
#    if slack_url and not validate_webhook_url(slack_url):
#        click.echo("❌ Invalid Slack webhook URL") 
#        return

# 4. Replace all AWS error handling:
#    except ClientError as e:
#        click.echo(f"❌ AWS Error: {e}", err=True)
# With:
#    except ClientError as e:
#        click.echo(f"❌ {sanitize_aws_error(e)}", err=True)

# 5. Add import to top of file:
#    import urllib.parse

print("Security fixes created. Apply manually to cli.py")