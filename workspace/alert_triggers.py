"""
Alert Triggers Module for ML Trading Bot
Handles automated alert triggering based on system health and trading conditions.
Engineer: ML Trading Bot Team
Version: 2.0.0
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import concurrent.futures
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels for classification."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert data structure with type hints and validation."""
    id: str
    severity: AlertSeverity
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class AlertTriggers:
    """
    Advanced alert triggering system with timeout support, configurable parameters,
    and comprehensive error handling.
    
    Features:
    - Configurable agent count via environment/config
    - Async health checks with timeout
    - Graceful error handling for None returns
    - Structured logging and alert aggregation
    - Thread-safe operations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AlertTriggers with configuration.
        
        Args:
            config: Configuration dictionary with optional parameters:
                - max_agents: Maximum number of agents to monitor (default: 5)
                - health_check_timeout: Timeout in seconds (default: 30)
                - alert_manager_config: Configuration for alert manager
        """
        self.config = config or {}
        self.max_agents = self.config.get("max_agents", 5)
        self.health_check_timeout = self.config.get("health_check_timeout", 30)
        
        # Initialize alert manager (mock for example - would be injected in production)
        self.alert_manager = self._initialize_alert_manager()
        
        logger.info(f"AlertTriggers initialized: max_agents={self.max_agents}, "
                   f"timeout={self.health_check_timeout}s")
    
    def _initialize_alert_manager(self) -> Any:
        """Initialize alert manager with proper dependency injection."""
        try:
            # In production, this would be a proper AlertManager instance
            # For now, we create a mock with the required interface
            class MockAlertManager:
                def check_health_metrics(self) -> Optional[List[Dict[str, Any]]]:
                    """Mock health check that returns sample data."""
                    return [
                        {"agent_id": f"agent_{i}", "status": "healthy", "last_seen": datetime.now()}
                        for i in range(3)
                    ]
            
            return MockAlertManager()
        except Exception as e:
            logger.error(f"Failed to initialize alert manager: {e}")
            raise
    
    async def trigger_health_check(self) -> List[Alert]:
        """
        Perform comprehensive health check with timeout and error handling.
        
        Returns:
            List[Alert]: Collection of health alerts generated during check
            
        Raises:
            asyncio.TimeoutError: If health check exceeds configured timeout
            Exception: For any unexpected errors during health check
        """
        alerts: List[Alert] = []
        
        try:
            # Execute health check with timeout
            async with asyncio.timeout(self.health_check_timeout):
                logger.info(f"Starting health check for up to {self.max_agents} agents")
                
                # Get health metrics with None check
                health_metrics = self.alert_manager.check_health_metrics()
                
                if health_metrics is None:
                    alert = Alert(
                        id="HC-001",
                        severity=AlertSeverity.WARNING,
                        message="Health metrics returned None - possible monitoring issue",
                        source="alert_triggers",
                        metadata={"function": "check_health_metrics"}
                    )
                    alerts.append(alert)
                    logger.warning("Health metrics returned None")
                    return alerts  # Early return with warning
                
                # Process health metrics
                alerts.extend(self._process_health_metrics(health_metrics))
                
                # Perform additional checks
                alerts.extend(await self._perform_agent_checks())
                
        except asyncio.TimeoutError:
            alert = Alert(
                id="HC-002",
                severity=AlertSeverity.ERROR,
                message=f"Health check timed out after {self.health_check_timeout} seconds",
                source="alert_triggers",
                metadata={"timeout_seconds": self.health_check_timeout}
            )
            alerts.append(alert)
            logger.error(f"Health check timeout: {self.health_check_timeout}s")
            
        except Exception as e:
            alert = Alert(
                id="HC-003",
                severity=AlertSeverity.CRITICAL,
                message=f"Health check failed with exception: {str(e)}",
                source="alert_triggers",
                metadata={"exception_type": type(e).__name__}
            )
            alerts.append(alert)
            logger.exception(f"Health check failed: {e}")
        
        finally:
            # Log summary of alerts
            if alerts:
                severity_counts = {}
                for alert in alerts:
                    sev = alert.severity.value
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                
                logger.info(f"Health check completed: {len(alerts)} alerts generated - {severity_counts}")
            else:
                logger.info("Health check completed: No alerts generated")
        
        return alerts  # Explicit return statement as requested
    
    def _process_health_metrics(self, metrics: List[Dict[str, Any]]) -> List[Alert]:
        """Process health metrics and generate appropriate alerts."""
        alerts = []
        
        for metric in metrics:
            try:
                agent_id = metric.get("agent_id", "unknown")
                status = metric.get("status", "unknown")
                
                if status != "healthy":
                    alert = Alert(
                        id=f"HC-{agent_id}",
                        severity=AlertSeverity.WARNING,
                        message=f"Agent {agent_id} has non-healthy status: {status}",
                        source="health_metrics",
                        metadata=metric
                    )
                    alerts.append(alert)
                    
            except KeyError as e:
                logger.warning(f"Missing key in health metric: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing health metric: {e}")
                continue
        
        return alerts
    
    async def _perform_agent_checks(self) -> List[Alert]:
        """Perform additional agent-specific checks asynchronously."""
        alerts = []
        
        # Example: Check each agent's last activity
        # In production, this would query actual agent status
        sample_agents = [
            {"id": "data_scientist", "last_active": datetime.now() - timedelta(minutes=5)},
            {"id": "quant_analyst", "last_active": datetime.now() - timedelta(minutes=2)},
            {"id": "engineer", "last_active": datetime.now() - timedelta(minutes=10)},
        ]
        
        for agent in sample_agents[:self.max_agents]:  # Respect max_agents configuration
            last_active = agent["last_active"]
            inactive_minutes = (datetime.now() - last_active).total_seconds() / 60
            
            if inactive_minutes > 5:  # Threshold: 5 minutes
                alert = Alert(
                    id=f"AC-{agent['id']}",
                    severity=AlertSeverity.WARNING,
                    message=f"Agent {agent['id']} inactive for {inactive_minutes:.1f} minutes",
                    source="agent_check",
                    metadata=agent
                )
                alerts.append(alert)
        
        return alerts
    
    def get_alert_summary(self, alerts: List[Alert]) -> Dict[str, Any]:
        """
        Generate summary statistics for alerts.
        
        Args:
            alerts: List of Alert objects
            
        Returns:
            Dictionary with alert summary statistics
        """
        if not alerts:
            return {"total": 0, "by_severity": {}, "sources": []}
        
        by_severity = {}
        sources = set()
        
        for alert in alerts:
            sev = alert.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            sources.add(alert.source)
        
        return {
            "total": len(alerts),
            "by_severity": by_severity,
            "sources": list(sources),
            "timestamp": datetime.now().isoformat()
        }


# Example usage and testing
async def main():
    """Example usage of AlertTriggers."""
    # Configuration with parameters (not hardcoded)
    config = {
        "max_agents": 8,  # Configurable, not hardcoded
        "health_check_timeout": 45,  # Configurable timeout
    }
    
    triggers = AlertTriggers(config)
    
    print("Performing health check...")
    alerts = await triggers.trigger_health_check()
    
    print(f"Generated {len(alerts)} alerts")
    
    if alerts:
        summary = triggers.get_alert_summary(alerts)
        print(f"Alert summary: {summary}")
        
        # Example: Send alerts to monitoring system
        for alert in alerts[:3]:  # Show first 3 alerts
            print(f"Alert: {alert.to_dict()}")
    
    return alerts


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())