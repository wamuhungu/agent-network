#!/usr/bin/env python3
"""
Health Monitoring Service

Comprehensive health monitoring for the agent network with:
- Real-time health checks
- Performance metrics collection
- Alerting and notifications
- Health dashboards
"""

import os
import sys
import json
import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from collections import deque, defaultdict
import statistics
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager
from tools.message_broker import MessageBroker


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class HealthMetric:
    """Represents a health metric."""
    name: str
    type: MetricType
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


@dataclass
class HealthAlert:
    """Represents a health alert."""
    severity: str  # 'info', 'warning', 'error', 'critical'
    component: str
    message: str
    metric: Optional[str]
    threshold: Optional[float]
    actual_value: Optional[float]
    timestamp: datetime
    resolved: bool = False


class HealthMonitor:
    """
    Comprehensive health monitoring service.
    
    Features:
    - Real-time metric collection
    - Threshold-based alerting
    - Performance tracking
    - Resource monitoring
    - Custom health checks
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the health monitor."""
        self.config = config or {}
        
        # Monitoring settings
        self.check_interval = self.config.get('check_interval', 30)
        self.metric_retention = self.config.get('metric_retention', 3600)  # 1 hour
        self.alert_cooldown = self.config.get('alert_cooldown', 300)  # 5 minutes
        
        # Metric storage (in-memory for last hour)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[HealthAlert] = []
        self.alert_history: Dict[str, datetime] = {}
        
        # Health checks
        self.health_checks: Dict[str, Callable] = {
            'database': self._check_database_health,
            'message_queue': self._check_message_queue_health,
            'agents': self._check_agent_health,
            'system_resources': self._check_system_resources,
            'task_processing': self._check_task_processing
        }
        
        # Alert thresholds
        self.thresholds = {
            'cpu_percent': {'warning': 70, 'critical': 90},
            'memory_percent': {'warning': 80, 'critical': 95},
            'disk_percent': {'warning': 85, 'critical': 95},
            'queue_depth': {'warning': 100, 'critical': 500},
            'task_backlog': {'warning': 50, 'critical': 100},
            'error_rate': {'warning': 0.05, 'critical': 0.10},
            'response_time': {'warning': 5000, 'critical': 10000}  # ms
        }
        
        # Service state
        self.running = False
        self.monitor_thread = None
        
        # Connections
        self.state_manager = StateManager()
        self.broker = MessageBroker()
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('HealthMonitor')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/health_monitor.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def start(self) -> bool:
        """Start the health monitoring service."""
        try:
            # Connect to services
            if not self.state_manager.is_connected():
                self.logger.error("Failed to connect to MongoDB")
                return False
            
            if not self.broker.connect():
                self.logger.warning("Failed to connect to RabbitMQ")
                # Continue anyway - we can still monitor other components
            
            # Start monitoring thread
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            # Start metric cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            
            self.logger.info("Health monitoring service started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start health monitor: {e}")
            return False
    
    def stop(self):
        """Stop the health monitoring service."""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        if hasattr(self, 'cleanup_thread'):
            self.cleanup_thread.join(timeout=5)
        
        self.broker.disconnect()
        self.state_manager.disconnect()
        
        self.logger.info("Health monitoring service stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self.collect_metrics()
                self.run_health_checks()
                self.evaluate_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def _cleanup_loop(self):
        """Clean up old metrics periodically."""
        while self.running:
            try:
                self.cleanup_old_metrics()
                time.sleep(300)  # Every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def collect_metrics(self):
        """Collect all system metrics."""
        timestamp = datetime.utcnow()
        
        # System metrics
        self.record_metric('cpu_percent', psutil.cpu_percent(interval=1), 
                          'percent', timestamp, {'type': 'system'})
        
        memory = psutil.virtual_memory()
        self.record_metric('memory_percent', memory.percent, 
                          'percent', timestamp, {'type': 'system'})
        self.record_metric('memory_available', memory.available, 
                          'bytes', timestamp, {'type': 'system'})
        
        disk = psutil.disk_usage('/')
        self.record_metric('disk_percent', disk.percent, 
                          'percent', timestamp, {'type': 'system'})
        
        # Database metrics
        if self.state_manager.is_connected():
            try:
                db_stats = self.state_manager.db.command('dbstats')
                self.record_metric('db_size', db_stats.get('dataSize', 0), 
                                  'bytes', timestamp, {'type': 'database'})
                self.record_metric('db_objects', db_stats.get('objects', 0), 
                                  'count', timestamp, {'type': 'database'})
            except Exception as e:
                self.logger.error(f"Error collecting database metrics: {e}")
        
        # Message queue metrics
        if self.broker.is_connected:
            try:
                for queue in [MessageBroker.MANAGER_QUEUE, MessageBroker.DEVELOPER_QUEUE]:
                    info = self.broker.get_queue_info(queue)
                    if info:
                        self.record_metric(f'queue_depth_{queue}', 
                                         info['messages'], 'count', timestamp,
                                         {'type': 'queue', 'queue': queue})
                        self.record_metric(f'queue_consumers_{queue}', 
                                         info['consumers'], 'count', timestamp,
                                         {'type': 'queue', 'queue': queue})
            except Exception as e:
                self.logger.error(f"Error collecting queue metrics: {e}")
        
        # Application metrics
        self._collect_application_metrics(timestamp)
    
    def _collect_application_metrics(self, timestamp: datetime):
        """Collect application-specific metrics."""
        try:
            # Task metrics
            total_tasks = self.state_manager.db.tasks.count_documents({})
            active_tasks = self.state_manager.db.tasks.count_documents({
                'status': {'$in': ['created', 'assigned', 'in_progress']}
            })
            completed_tasks = self.state_manager.db.tasks.count_documents({
                'status': 'completed'
            })
            failed_tasks = self.state_manager.db.tasks.count_documents({
                'status': 'failed'
            })
            
            self.record_metric('tasks_total', total_tasks, 'count', 
                             timestamp, {'type': 'application'})
            self.record_metric('tasks_active', active_tasks, 'count', 
                             timestamp, {'type': 'application'})
            self.record_metric('tasks_completed', completed_tasks, 'count', 
                             timestamp, {'type': 'application'})
            self.record_metric('tasks_failed', failed_tasks, 'count', 
                             timestamp, {'type': 'application'})
            
            # Calculate rates
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_completions = self.state_manager.db.tasks.count_documents({
                'status': 'completed',
                'metadata.completed_at': {'$gte': one_hour_ago.isoformat()}
            })
            
            self.record_metric('task_completion_rate', recent_completions / 60, 
                             'per_minute', timestamp, {'type': 'application'})
            
            # Error rate
            if total_tasks > 0:
                error_rate = failed_tasks / total_tasks
                self.record_metric('error_rate', error_rate, 'ratio', 
                                 timestamp, {'type': 'application'})
            
        except Exception as e:
            self.logger.error(f"Error collecting application metrics: {e}")
    
    def record_metric(self, name: str, value: float, unit: str, 
                     timestamp: datetime, tags: Dict[str, str]):
        """Record a metric value."""
        metric = HealthMetric(
            name=name,
            type=MetricType.GAUGE,  # Simplified for now
            value=value,
            unit=unit,
            timestamp=timestamp,
            tags=tags
        )
        
        self.metrics[name].append(metric)
    
    def run_health_checks(self):
        """Run all configured health checks."""
        for name, check_func in self.health_checks.items():
            try:
                check_func()
            except Exception as e:
                self.logger.error(f"Error running health check {name}: {e}")
                self.create_alert(
                    severity='error',
                    component=name,
                    message=f"Health check failed: {str(e)}"
                )
    
    def _check_database_health(self):
        """Check database health."""
        if not self.state_manager.is_connected():
            self.create_alert(
                severity='critical',
                component='database',
                message='Database connection lost'
            )
            return
        
        try:
            # Check response time
            start = time.time()
            self.state_manager.db.command('ping')
            response_time = (time.time() - start) * 1000  # ms
            
            self.record_metric('db_response_time', response_time, 'ms',
                             datetime.utcnow(), {'type': 'database'})
            
            if response_time > self.thresholds['response_time']['critical']:
                self.create_alert(
                    severity='critical',
                    component='database',
                    message='Database response time critical',
                    metric='db_response_time',
                    threshold=self.thresholds['response_time']['critical'],
                    actual_value=response_time
                )
            elif response_time > self.thresholds['response_time']['warning']:
                self.create_alert(
                    severity='warning',
                    component='database',
                    message='Database response time high',
                    metric='db_response_time',
                    threshold=self.thresholds['response_time']['warning'],
                    actual_value=response_time
                )
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            self.create_alert(
                severity='error',
                component='database',
                message=f'Database health check error: {str(e)}'
            )
    
    def _check_message_queue_health(self):
        """Check message queue health."""
        if not self.broker.is_connected:
            # Try to reconnect
            if not self.broker.connect():
                self.create_alert(
                    severity='critical',
                    component='message_queue',
                    message='Message queue connection lost'
                )
                return
        
        try:
            # Check queue depths
            for queue in [MessageBroker.MANAGER_QUEUE, MessageBroker.DEVELOPER_QUEUE]:
                info = self.broker.get_queue_info(queue)
                if info:
                    depth = info['messages']
                    
                    if depth > self.thresholds['queue_depth']['critical']:
                        self.create_alert(
                            severity='critical',
                            component='message_queue',
                            message=f'Queue {queue} depth critical',
                            metric='queue_depth',
                            threshold=self.thresholds['queue_depth']['critical'],
                            actual_value=depth
                        )
                    elif depth > self.thresholds['queue_depth']['warning']:
                        self.create_alert(
                            severity='warning',
                            component='message_queue',
                            message=f'Queue {queue} depth high',
                            metric='queue_depth',
                            threshold=self.thresholds['queue_depth']['warning'],
                            actual_value=depth
                        )
                        
        except Exception as e:
            self.logger.error(f"Message queue health check failed: {e}")
    
    def _check_agent_health(self):
        """Check agent health."""
        try:
            for agent_id in ['manager', 'developer']:
                state = self.state_manager.get_agent_state(agent_id)
                
                if not state:
                    self.create_alert(
                        severity='error',
                        component=f'agent_{agent_id}',
                        message=f'{agent_id.capitalize()} agent not found'
                    )
                    continue
                
                # Check heartbeat
                last_heartbeat = state.get('last_heartbeat')
                if last_heartbeat:
                    heartbeat_time = datetime.fromisoformat(
                        last_heartbeat.replace('Z', '+00:00')
                    )
                    seconds_since = (datetime.utcnow() - heartbeat_time).total_seconds()
                    
                    if seconds_since > 300:  # 5 minutes
                        self.create_alert(
                            severity='critical',
                            component=f'agent_{agent_id}',
                            message=f'{agent_id.capitalize()} agent unresponsive',
                            metric='heartbeat_age',
                            threshold=300,
                            actual_value=seconds_since
                        )
                    elif seconds_since > 120:  # 2 minutes
                        self.create_alert(
                            severity='warning',
                            component=f'agent_{agent_id}',
                            message=f'{agent_id.capitalize()} agent heartbeat delayed',
                            metric='heartbeat_age',
                            threshold=120,
                            actual_value=seconds_since
                        )
                        
        except Exception as e:
            self.logger.error(f"Agent health check failed: {e}")
    
    def _check_system_resources(self):
        """Check system resource usage."""
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.thresholds['cpu_percent']['critical']:
            self.create_alert(
                severity='critical',
                component='system',
                message='CPU usage critical',
                metric='cpu_percent',
                threshold=self.thresholds['cpu_percent']['critical'],
                actual_value=cpu_percent
            )
        elif cpu_percent > self.thresholds['cpu_percent']['warning']:
            self.create_alert(
                severity='warning',
                component='system',
                message='CPU usage high',
                metric='cpu_percent',
                threshold=self.thresholds['cpu_percent']['warning'],
                actual_value=cpu_percent
            )
        
        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > self.thresholds['memory_percent']['critical']:
            self.create_alert(
                severity='critical',
                component='system',
                message='Memory usage critical',
                metric='memory_percent',
                threshold=self.thresholds['memory_percent']['critical'],
                actual_value=memory.percent
            )
        elif memory.percent > self.thresholds['memory_percent']['warning']:
            self.create_alert(
                severity='warning',
                component='system',
                message='Memory usage high',
                metric='memory_percent',
                threshold=self.thresholds['memory_percent']['warning'],
                actual_value=memory.percent
            )
        
        # Disk check
        disk = psutil.disk_usage('/')
        if disk.percent > self.thresholds['disk_percent']['critical']:
            self.create_alert(
                severity='critical',
                component='system',
                message='Disk usage critical',
                metric='disk_percent',
                threshold=self.thresholds['disk_percent']['critical'],
                actual_value=disk.percent
            )
        elif disk.percent > self.thresholds['disk_percent']['warning']:
            self.create_alert(
                severity='warning',
                component='system',
                message='Disk usage high',
                metric='disk_percent',
                threshold=self.thresholds['disk_percent']['warning'],
                actual_value=disk.percent
            )
    
    def _check_task_processing(self):
        """Check task processing health."""
        try:
            # Check task backlog
            backlog = self.state_manager.db.tasks.count_documents({
                'status': {'$in': ['created', 'assigned']}
            })
            
            if backlog > self.thresholds['task_backlog']['critical']:
                self.create_alert(
                    severity='critical',
                    component='task_processing',
                    message='Task backlog critical',
                    metric='task_backlog',
                    threshold=self.thresholds['task_backlog']['critical'],
                    actual_value=backlog
                )
            elif backlog > self.thresholds['task_backlog']['warning']:
                self.create_alert(
                    severity='warning',
                    component='task_processing',
                    message='Task backlog growing',
                    metric='task_backlog',
                    threshold=self.thresholds['task_backlog']['warning'],
                    actual_value=backlog
                )
            
            # Check error rate
            recent_metrics = list(self.metrics.get('error_rate', []))
            if recent_metrics:
                current_error_rate = recent_metrics[-1].value
                
                if current_error_rate > self.thresholds['error_rate']['critical']:
                    self.create_alert(
                        severity='critical',
                        component='task_processing',
                        message='Error rate critical',
                        metric='error_rate',
                        threshold=self.thresholds['error_rate']['critical'],
                        actual_value=current_error_rate
                    )
                elif current_error_rate > self.thresholds['error_rate']['warning']:
                    self.create_alert(
                        severity='warning',
                        component='task_processing',
                        message='Error rate elevated',
                        metric='error_rate',
                        threshold=self.thresholds['error_rate']['warning'],
                        actual_value=current_error_rate
                    )
                    
        except Exception as e:
            self.logger.error(f"Task processing health check failed: {e}")
    
    def create_alert(self, severity: str, component: str, message: str,
                    metric: Optional[str] = None, threshold: Optional[float] = None,
                    actual_value: Optional[float] = None):
        """Create a new alert if not in cooldown."""
        alert_key = f"{component}:{metric or message}"
        
        # Check cooldown
        if alert_key in self.alert_history:
            last_alert = self.alert_history[alert_key]
            if (datetime.utcnow() - last_alert).total_seconds() < self.alert_cooldown:
                return  # Still in cooldown
        
        # Create alert
        alert = HealthAlert(
            severity=severity,
            component=component,
            message=message,
            metric=metric,
            threshold=threshold,
            actual_value=actual_value,
            timestamp=datetime.utcnow()
        )
        
        self.alerts.append(alert)
        self.alert_history[alert_key] = alert.timestamp
        
        # Log alert
        self.logger.log(
            logging.CRITICAL if severity == 'critical' else 
            logging.ERROR if severity == 'error' else
            logging.WARNING if severity == 'warning' else
            logging.INFO,
            f"ALERT [{severity}] {component}: {message}"
        )
        
        # Send notifications
        self._send_alert_notifications(alert)
        
        # Store in database
        self._store_alert(alert)
    
    def _send_alert_notifications(self, alert: HealthAlert):
        """Send alert notifications."""
        # In production, this would integrate with:
        # - Email
        # - Slack
        # - PagerDuty
        # - SMS
        # - Webhooks
        pass
    
    def _store_alert(self, alert: HealthAlert):
        """Store alert in database."""
        try:
            self.state_manager.db.health_alerts.insert_one({
                'severity': alert.severity,
                'component': alert.component,
                'message': alert.message,
                'metric': alert.metric,
                'threshold': alert.threshold,
                'actual_value': alert.actual_value,
                'timestamp': alert.timestamp,
                'resolved': alert.resolved
            })
        except Exception as e:
            self.logger.error(f"Failed to store alert: {e}")
    
    def evaluate_alerts(self):
        """Evaluate and auto-resolve alerts."""
        # This would check if conditions that triggered alerts
        # have been resolved and mark them accordingly
        pass
    
    def cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.metric_retention)
        
        for metric_name, metric_list in self.metrics.items():
            # Remove old metrics
            while metric_list and metric_list[0].timestamp < cutoff:
                metric_list.popleft()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status summary."""
        # Determine overall status
        active_alerts = [a for a in self.alerts if not a.resolved]
        critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        error_alerts = [a for a in active_alerts if a.severity == 'error']
        warning_alerts = [a for a in active_alerts if a.severity == 'warning']
        
        if critical_alerts:
            overall_status = HealthStatus.CRITICAL
        elif error_alerts:
            overall_status = HealthStatus.DEGRADED
        elif warning_alerts:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'alerts': {
                'critical': len(critical_alerts),
                'error': len(error_alerts),
                'warning': len(warning_alerts),
                'total': len(active_alerts)
            },
            'components': self._get_component_status(),
            'metrics_summary': self._get_metrics_summary()
        }
    
    def _get_component_status(self) -> Dict[str, str]:
        """Get status of each component."""
        component_status = {}
        
        # Check recent alerts for each component
        for component in ['database', 'message_queue', 'agent_manager', 
                         'agent_developer', 'system', 'task_processing']:
            recent_alerts = [
                a for a in self.alerts
                if a.component == component and not a.resolved
                and (datetime.utcnow() - a.timestamp).total_seconds() < 300
            ]
            
            if any(a.severity == 'critical' for a in recent_alerts):
                component_status[component] = 'critical'
            elif any(a.severity == 'error' for a in recent_alerts):
                component_status[component] = 'error'
            elif any(a.severity == 'warning' for a in recent_alerts):
                component_status[component] = 'warning'
            else:
                component_status[component] = 'healthy'
        
        return component_status
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recent metrics."""
        summary = {}
        
        # Get latest values for key metrics
        key_metrics = [
            'cpu_percent', 'memory_percent', 'disk_percent',
            'tasks_active', 'error_rate', 'db_response_time'
        ]
        
        for metric_name in key_metrics:
            if metric_name in self.metrics and self.metrics[metric_name]:
                latest = self.metrics[metric_name][-1]
                summary[metric_name] = {
                    'value': latest.value,
                    'unit': latest.unit,
                    'timestamp': latest.timestamp.isoformat()
                }
        
        return summary
    
    def get_metric_history(self, metric_name: str, 
                          duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical values for a metric."""
        if metric_name not in self.metrics:
            return []
        
        cutoff = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        return [
            {
                'value': m.value,
                'timestamp': m.timestamp.isoformat(),
                'tags': m.tags
            }
            for m in self.metrics[metric_name]
            if m.timestamp >= cutoff
        ]


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Health Monitoring Service')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds')
    parser.add_argument('--status', action='store_true',
                       help='Show current status and exit')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor({
        'check_interval': args.interval
    })
    
    if args.status:
        # Show current status
        if monitor.start():
            time.sleep(2)  # Let it collect some metrics
            status = monitor.get_health_status()
            print(json.dumps(status, indent=2))
            monitor.stop()
    else:
        # Run as service
        print("Starting Health Monitoring Service...")
        if monitor.start():
            print(f"Health Monitor running (check interval: {args.interval}s)")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    time.sleep(60)
                    # Print summary every minute
                    status = monitor.get_health_status()
                    print(f"\nHealth Status: {status['status']}")
                    print(f"Active Alerts: {status['alerts']['total']}")
                    
            except KeyboardInterrupt:
                print("\nStopping Health Monitor...")
                monitor.stop()
        else:
            print("Failed to start Health Monitor")
            sys.exit(1)


if __name__ == '__main__':
    main()