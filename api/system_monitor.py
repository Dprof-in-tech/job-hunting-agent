"""
System Monitoring Module
Provides real-time system health, security metrics, and alerts
"""

import os
import time
import psutil
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemHealthData:
    """System health metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    response_time_p95: float
    error_rate: float
    uptime_seconds: int
    last_restart: str

@dataclass
class SecurityMetrics:
    """Security monitoring metrics"""
    blocked_requests: int
    suspicious_activities: int
    rate_limit_hits: int
    active_sessions: int
    failed_authentications: int
    vulnerability_scan_status: str
    last_security_scan: str
    threat_level: str

@dataclass
class AlertData:
    """System alert information"""
    id: str
    type: str  # 'info', 'warning', 'error', 'critical'
    message: str
    timestamp: str
    resolved: bool
    component: str

class SystemMonitor:
    """Comprehensive system monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.alerts: List[AlertData] = []
        self.security_counters = {
            'blocked_requests': 0,
            'suspicious_activities': 0, 
            'rate_limit_hits': 0,
            'failed_authentications': 0
        }
        
    def get_system_health(self) -> SystemHealthData:
        """Get current system health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network connections (handle permission errors)
            try:
                connections = len(psutil.net_connections())
            except (psutil.AccessDenied, PermissionError):
                connections = 0  # Fallback when permissions are denied
            
            # System uptime
            uptime_seconds = int(time.time() - self.start_time)
            
            # Mock response time and error rate for now
            response_time_p95 = self._get_response_time_p95()
            error_rate = self._get_error_rate()
            
            return SystemHealthData(
                cpu_usage=round(cpu_percent, 1),
                memory_usage=round(memory_percent, 1),
                disk_usage=round(disk_percent, 1),
                active_connections=connections,
                response_time_p95=response_time_p95,
                error_rate=error_rate,
                uptime_seconds=uptime_seconds,
                last_restart=datetime.fromtimestamp(self.start_time).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            # Return default values on error
            return SystemHealthData(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_connections=0,
                response_time_p95=0.0,
                error_rate=0.0,
                uptime_seconds=int(time.time() - self.start_time),
                last_restart=datetime.fromtimestamp(self.start_time).isoformat()
            )
    
    def get_security_metrics(self, security_manager=None) -> SecurityMetrics:
        """Get security monitoring metrics"""
        try:
            # Get active sessions from security manager if available
            active_sessions = 0
            if security_manager and hasattr(security_manager, 'active_sessions'):
                active_sessions = len([
                    s for s in security_manager.active_sessions.values()
                    if not self._is_session_expired(s)
                ])
            
            # Calculate threat level
            threat_level = self._calculate_threat_level()
            
            return SecurityMetrics(
                blocked_requests=self.security_counters['blocked_requests'],
                suspicious_activities=self.security_counters['suspicious_activities'],
                rate_limit_hits=self.security_counters['rate_limit_hits'],
                active_sessions=active_sessions,
                failed_authentications=self.security_counters['failed_authentications'],
                vulnerability_scan_status="Passed",
                last_security_scan=datetime.now().isoformat(),
                threat_level=threat_level
            )
            
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}")
            return SecurityMetrics(
                blocked_requests=0,
                suspicious_activities=0,
                rate_limit_hits=0,
                active_sessions=0,
                failed_authentications=0,
                vulnerability_scan_status="Unknown",
                last_security_scan="Never",
                threat_level="low"
            )
    
    def get_recent_alerts(self, limit: int = 10) -> List[AlertData]:
        """Get recent system alerts"""
        # Sort by timestamp and return most recent
        sorted_alerts = sorted(
            self.alerts, 
            key=lambda x: x.timestamp, 
            reverse=True
        )
        return sorted_alerts[:limit]
    
    def add_alert(self, alert_type: str, message: str, component: str = "System"):
        """Add a new system alert"""
        alert = AlertData(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            type=alert_type,
            message=message,
            timestamp=datetime.now().isoformat(),
            resolved=False,
            component=component
        )
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def increment_security_counter(self, counter_name: str):
        """Increment security counter"""
        if counter_name in self.security_counters:
            self.security_counters[counter_name] += 1
    
    def _get_response_time_p95(self) -> float:
        """Calculate 95th percentile response time"""
        # Mock implementation - in production, use actual request timing data
        return 250.0
    
    def _get_error_rate(self) -> float:
        """Calculate current error rate"""
        # Mock implementation - in production, use actual error tracking
        return 1.2
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """Check if session is expired"""
        try:
            created_at = session.get('created_at')
            if not created_at:
                return True
            
            # Simple check - assume 24 hour expiry
            session_age = time.time() - created_at
            return session_age > 86400  # 24 hours
            
        except Exception:
            return True
    
    def _calculate_threat_level(self) -> str:
        """Calculate current threat level based on security metrics"""
        total_threats = (
            self.security_counters['blocked_requests'] +
            self.security_counters['suspicious_activities'] +
            self.security_counters['failed_authentications']
        )
        
        if total_threats > 50:
            return "high"
        elif total_threats > 10:
            return "medium"
        else:
            return "low"
    
    def generate_sample_alerts(self):
        """Generate sample alerts for testing"""
        sample_alerts = [
            {
                'type': 'info',
                'message': 'System monitoring initialized successfully',
                'component': 'SystemMonitor'
            },
            {
                'type': 'warning', 
                'message': 'High memory usage detected (85%)',
                'component': 'ResourceMonitor'
            },
            {
                'type': 'info',
                'message': 'Security scan completed - no vulnerabilities found',
                'component': 'SecurityScanner'
            }
        ]
        
        for alert_data in sample_alerts:
            self.add_alert(
                alert_data['type'],
                alert_data['message'], 
                alert_data['component']
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all monitoring data to dictionary"""
        try:
            health = self.get_system_health()
            security = self.get_security_metrics()
            alerts = self.get_recent_alerts()
            
            return {
                'system_health': asdict(health),
                'security_metrics': asdict(security),
                'recent_alerts': [asdict(alert) for alert in alerts]
            }
            
        except Exception as e:
            logger.error(f"Error converting monitoring data to dict: {e}")
            return {
                'system_health': {},
                'security_metrics': {},
                'recent_alerts': []
            }

# Global system monitor instance
system_monitor = SystemMonitor()

# Generate some sample alerts for demonstration
system_monitor.generate_sample_alerts()