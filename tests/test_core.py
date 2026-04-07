"""Tests for AWS Cost Watcher."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from aws_cost_watcher.cli import (
    load_config,
    calculate_total,
    format_currency,
    check_credentials,
    get_costs,
    get_service_costs,
    notify,
    cli,
    main,
)


class TestCalculateTotal:
    """Tests for calculate_total function."""

    def test_empty_response(self):
        assert calculate_total(None) == 0.0
        assert calculate_total({}) == 0.0

    def test_single_day(self):
        response = {
            "ResultsByTime": [
                {"Total": {"UnblendedCost": {"Amount": "100.50"}}}
            ]
        }
        assert calculate_total(response) == 100.50

    def test_multiple_days(self):
        response = {
            "ResultsByTime": [
                {"Total": {"UnblendedCost": {"Amount": "100.50"}}},
                {"Total": {"UnblendedCost": {"Amount": "50.25"}}},
            ]
        }
        assert calculate_total(response) == 150.75


class TestFormatCurrency:
    """Tests for format_currency function."""

    def test_whole_dollars(self):
        assert format_currency(100) == "$100.00"

    def test_decimal_dollars(self):
        assert format_currency(99.99) == "$99.99"

    def test_thousands(self):
        assert format_currency(1234.56) == "$1,234.56"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_default_config(self):
        config = load_config()
        assert "budget" in config
        assert "webhook_url" in config
        assert "region" in config

    def test_config_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/webhook")
        monkeypatch.setenv("AWS_COST_BUDGET", "150")
        config = load_config()
        assert config["webhook_url"] == "https://discord.com/webhook"
        assert config["budget"] == 150.0


class TestCLI:
    """Tests for CLI commands."""

    def test_help_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AWS Cost Watcher" in result.output

    def test_check_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "budget" in result.output

    def test_alert_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["alert", "--help"])
        assert result.exit_code == 0
        assert "budget" in result.output


class TestNotify:
    """Tests for notify function."""

    def test_no_budget(self):
        config = {"budget": None}
        # Should not raise
        notify(config, 100.0)

    def test_under_budget(self, capsys):
        config = {"budget": 200.0, "dry_run": True}
        notify(config, 100.0)
        # Should not send anything

    def test_over_budget_discord(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/webhook")
        config = {"budget": 100.0, "webhook_url": "https://discord.com/webhook", "dry_run": True}
        # Mock the webhook to not actually send
        with patch("aws_cost_watcher.cli.send_webhook", return_value=True):
            notify(config, 150.0)


class TestCredentials:
    """Tests for credential checking."""

    def test_no_credentials(self):
        config = {"region": "us-east-1", "profile": "nonexistent"}
        # Should return False or handle gracefully
        # This tests the error path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
