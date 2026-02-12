"""
Unit tests for AlertTriggers module.
Engineer: ML Trading Bot Team
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from alert_triggers import AlertTriggers, Alert, AlertSeverity


class TestAlertTriggers:
    """Test suite for AlertTriggers functionality."""
    
    def test_init_with_config(self):
        """Test initialization with custom configuration."""
        config = {
            "max_agents": 10,
            "health_check_timeout": 60
        }
        
        triggers = AlertTriggers(config)
        
        assert triggers.max_agents == 10
        assert triggers.health_check_timeout == 60
        assert triggers.config == config
    
    def test_init_without_config(self):
        """Test initialization with default configuration."""
        triggers = AlertTriggers()
        
        assert triggers.max_agents == 5  # Default value
        assert triggers.health_check_timeout == 30  # Default value
    
    def test_alert_structure(self):
        """Test Alert dataclass structure and methods."""
        alert = Alert(
            id="TEST-001",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            source="test_suite"
        )
        
        assert alert.id == "TEST-001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.message == "Test alert"
        assert alert.source == "test_suite"
        assert isinstance(alert.timestamp, datetime)
        
        # Test serialization
        alert_dict = alert.to_dict()
        assert alert_dict["id"] == "TEST-001"
        assert alert_dict["severity"] == "WARNING"
        assert "timestamp" in alert_dict
    
    @pytest.mark.asyncio
    async def test_trigger_health_check_returns_list(self):
        """Verify that trigger_health_check returns a list."""
        triggers = AlertTriggers()
        
        alerts = await triggers.trigger_health_check()
        
        assert isinstance(alerts, list)
        # All items should be Alert instances
        if alerts:
            assert all(isinstance(alert, Alert) for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_health_check_with_timeout_config(self):
        """Test that timeout configuration is respected."""
        config = {"health_check_timeout": 1}  # Very short timeout
        triggers = AlertTriggers(config)
        
        # This should complete within timeout
        alerts = await triggers.trigger_health_check()
        assert isinstance(alerts, list)
    
    def test_get_alert_summary(self):
        """Test alert summary generation."""
        triggers = AlertTriggers()
        
        # Test with empty alerts
        empty_summary = triggers.get_alert_summary([])
        assert empty_summary["total"] == 0
        assert empty_summary["by_severity"] == {}
        
        # Test with sample alerts
        alerts = [
            Alert(id="1", severity=AlertSeverity.INFO, message="Test", source="source1"),
            Alert(id="2", severity=AlertSeverity.WARNING, message="Test", source="source2"),
            Alert(id="3", severity=AlertSeverity.WARNING, message="Test", source="source1"),
        ]
        
        summary = triggers.get_alert_summary(alerts)
        
        assert summary["total"] == 3
        assert summary["by_severity"]["INFO"] == 1
        assert summary["by_severity"]["WARNING"] == 2
        assert set(summary["sources"]) == {"source1", "source2"}
        assert "timestamp" in summary


@pytest.mark.asyncio
async def test_integration():
    """Integration test for main functionality."""
    config = {"max_agents": 3}
    triggers = AlertTriggers(config)
    
    alerts = await triggers.trigger_health_check()
    
    # Should return list (even if empty)
    assert isinstance(alerts, list)
    
    # Verify we can generate summary
    summary = triggers.get_alert_summary(alerts)
    assert "total" in summary
    assert "by_severity" in summary
    
    print(f"Integration test passed: {len(alerts)} alerts generated")


if __name__ == "__main__":
    # Run tests
    import sys
    sys.exit(pytest.main([__file__, "-v"]))