#!/usr/bin/env python3
"""
Recovery Manager

Handles system recovery from various failure scenarios including:
- Agent crashes and restarts
- Database connection failures
- Message queue failures
- Network partitions
"""

import os
import sys
import json
import time
import signal
import subprocess
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager
from tools.message_broker import MessageBroker


class FailureType(Enum):
    """Types of failures that can occur."""
    AGENT_CRASH = "agent_crash"
    DATABASE_CONNECTION = "database_connection"
    MESSAGE_QUEUE_CONNECTION = "message_queue_connection"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    """Represents a recovery action to take."""
    failure_type: FailureType
    component: str
    action: str
    params: Dict[str, Any]
    priority: int  # 1 (highest) to 5 (lowest)
    retry_count: int = 0
    max_retries: int = 3


class RecoveryManager:
    """
    Manages recovery from system failures.
    
    Features:
    - Automatic failure detection
    - Graceful degradation
    - Component restart
    - State recovery
    - Failover coordination
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the recovery manager."""
        self.config = config or {}
        
        # Recovery settings
        self.check_interval = self.config.get('check_interval', 30)
        self.recovery_timeout = self.config.get('recovery_timeout', 300)
        self.max_restart_attempts = self.config.get('max_restart_attempts', 3)
        
        # Component tracking
        self.components = {
            'mongodb': {
                'process_name': 'mongod',
                'check_func': self._check_mongodb,
                'restart_func': self._restart_mongodb,
                'critical': True
            },
            'rabbitmq': {
                'process_name': 'rabbitmq-server',
                'check_func': self._check_rabbitmq,
                'restart_func': self._restart_rabbitmq,
                'critical': True
            },
            'manager_agent': {
                'process_name': 'message_listener.py',
                'check_func': self._check_manager_agent,
                'restart_func': self._restart_manager_agent,
                'critical': False
            },
            'developer_agent': {
                'process_name': 'message_listener.py',
                'check_func': self._check_developer_agent,
                'restart_func': self._restart_developer_agent,
                'critical': False
            }
        }
        
        # Recovery state
        self.running = False
        self.monitor_thread = None
        self.recovery_queue: List[RecoveryAction] = []
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Connection retry settings
        self.db_retry_config = {
            'max_attempts': 5,
            'initial_delay': 1,
            'max_delay': 60,
            'backoff_factor': 2
        }
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('RecoveryManager')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/recovery.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def start(self) -> bool:
        """Start the recovery manager."""
        try:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            # Start recovery worker
            self.recovery_thread = threading.Thread(target=self._recovery_worker, daemon=True)
            self.recovery_thread.start()
            
            self.logger.info("Recovery manager started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recovery manager: {e}")
            return False
    
    def stop(self):
        """Stop the recovery manager."""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        if hasattr(self, 'recovery_thread'):
            self.recovery_thread.join(timeout=5)
        
        self.logger.info("Recovery manager stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self.check_system_health()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def _recovery_worker(self):
        """Process recovery actions from the queue."""
        while self.running:
            try:
                if self.recovery_queue:
                    # Sort by priority
                    self.recovery_queue.sort(key=lambda x: x.priority)
                    
                    # Process highest priority action
                    action = self.recovery_queue.pop(0)
                    self.execute_recovery_action(action)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in recovery worker: {e}")
                time.sleep(5)
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Check overall system health.
        
        Returns:
            Health status report
        """
        health_report = {
            'timestamp': datetime.utcnow(),
            'components': {},
            'issues': [],
            'status': 'healthy'
        }
        
        # Check each component
        for name, component in self.components.items():
            try:
                is_healthy = component['check_func']()
                health_report['components'][name] = {
                    'healthy': is_healthy,
                    'critical': component['critical']
                }
                
                if not is_healthy:
                    health_report['issues'].append({
                        'component': name,
                        'type': FailureType.UNKNOWN,
                        'critical': component['critical']
                    })
                    
                    # Queue recovery action
                    self.queue_recovery_action(RecoveryAction(
                        failure_type=FailureType.UNKNOWN,
                        component=name,
                        action='restart',
                        params={},
                        priority=1 if component['critical'] else 3
                    ))
                    
            except Exception as e:
                self.logger.error(f"Error checking {name}: {e}")
                health_report['components'][name] = {
                    'healthy': False,
                    'error': str(e)
                }
        
        # Update overall status
        if health_report['issues']:
            critical_issues = [i for i in health_report['issues'] if i['critical']]
            health_report['status'] = 'critical' if critical_issues else 'degraded'
        
        return health_report
    
    def queue_recovery_action(self, action: RecoveryAction):
        """Add a recovery action to the queue."""
        # Check if similar action already queued
        for existing in self.recovery_queue:
            if (existing.component == action.component and 
                existing.action == action.action):
                return  # Skip duplicate
        
        self.recovery_queue.append(action)
        self.logger.info(
            f"Queued recovery action: {action.action} for {action.component}"
        )
    
    def execute_recovery_action(self, action: RecoveryAction) -> bool:
        """
        Execute a recovery action.
        
        Args:
            action: The recovery action to execute
            
        Returns:
            bool: True if successful
        """
        self.logger.info(
            f"Executing recovery: {action.action} for {action.component} "
            f"(attempt {action.retry_count + 1}/{action.max_retries})"
        )
        
        try:
            # Record attempt
            self.recovery_history.append({
                'timestamp': datetime.utcnow(),
                'action': action,
                'status': 'started'
            })
            
            # Execute based on action type
            if action.action == 'restart':
                success = self._restart_component(action.component)
            elif action.action == 'reconnect':
                success = self._reconnect_component(action.component)
            elif action.action == 'failover':
                success = self._failover_component(action.component)
            else:
                self.logger.warning(f"Unknown action: {action.action}")
                success = False
            
            # Update history
            self.recovery_history[-1]['status'] = 'success' if success else 'failed'
            
            # Handle failure
            if not success:
                action.retry_count += 1
                if action.retry_count < action.max_retries:
                    # Re-queue with delay
                    time.sleep(min(2 ** action.retry_count, 60))
                    self.recovery_queue.append(action)
                else:
                    self.logger.error(
                        f"Failed to recover {action.component} after "
                        f"{action.max_retries} attempts"
                    )
                    self._handle_permanent_failure(action)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing recovery action: {e}")
            return False
    
    def _restart_component(self, component: str) -> bool:
        """Restart a system component."""
        component_info = self.components.get(component)
        if not component_info:
            return False
        
        restart_func = component_info.get('restart_func')
        if restart_func:
            return restart_func()
        
        return False
    
    def _reconnect_component(self, component: str) -> bool:
        """Reconnect to a component."""
        if component == 'mongodb':
            return self._reconnect_mongodb()
        elif component == 'rabbitmq':
            return self._reconnect_rabbitmq()
        
        return False
    
    def _failover_component(self, component: str) -> bool:
        """Failover to backup component."""
        # This would implement failover logic for components with backups
        self.logger.info(f"Failover not implemented for {component}")
        return False
    
    def _handle_permanent_failure(self, action: RecoveryAction):
        """Handle a component that cannot be recovered."""
        self.logger.critical(
            f"PERMANENT FAILURE: {action.component} cannot be recovered"
        )
        
        # Implement emergency procedures
        if action.component in ['mongodb', 'rabbitmq']:
            # Critical infrastructure failure
            self._enter_safe_mode()
        else:
            # Non-critical component
            self._disable_component(action.component)
    
    def _enter_safe_mode(self):
        """Enter safe mode when critical components fail."""
        self.logger.critical("Entering SAFE MODE due to critical failure")
        
        # Stop all agents
        for agent in ['manager_agent', 'developer_agent']:
            self._stop_agent(agent)
        
        # Alert administrators
        self._send_alert("CRITICAL: System in safe mode", priority='critical')
    
    def _disable_component(self, component: str):
        """Disable a non-critical component."""
        self.logger.warning(f"Disabling component: {component}")
        # Update system configuration to disable component
    
    # Component check functions
    
    def _check_mongodb(self) -> bool:
        """Check if MongoDB is healthy."""
        try:
            sm = StateManager()
            if sm.is_connected():
                # Test with a simple query
                sm.db.command('ping')
                sm.disconnect()
                return True
        except:
            pass
        return False
    
    def _check_rabbitmq(self) -> bool:
        """Check if RabbitMQ is healthy."""
        try:
            broker = MessageBroker()
            if broker.connect():
                broker.disconnect()
                return True
        except:
            pass
        return False
    
    def _check_manager_agent(self) -> bool:
        """Check if manager agent is healthy."""
        try:
            sm = StateManager()
            if sm.is_connected():
                state = sm.get_agent_state('manager')
                if state:
                    last_heartbeat = state.get('last_heartbeat')
                    if last_heartbeat:
                        heartbeat_time = datetime.fromisoformat(
                            last_heartbeat.replace('Z', '+00:00')
                        )
                        if (datetime.utcnow() - heartbeat_time).total_seconds() < 300:
                            sm.disconnect()
                            return True
                sm.disconnect()
        except:
            pass
        return False
    
    def _check_developer_agent(self) -> bool:
        """Check if developer agent is healthy."""
        try:
            sm = StateManager()
            if sm.is_connected():
                state = sm.get_agent_state('developer')
                if state:
                    last_heartbeat = state.get('last_heartbeat')
                    if last_heartbeat:
                        heartbeat_time = datetime.fromisoformat(
                            last_heartbeat.replace('Z', '+00:00')
                        )
                        if (datetime.utcnow() - heartbeat_time).total_seconds() < 300:
                            sm.disconnect()
                            return True
                sm.disconnect()
        except:
            pass
        return False
    
    # Component restart functions
    
    def _restart_mongodb(self) -> bool:
        """Restart MongoDB service."""
        try:
            self.logger.info("Attempting to restart MongoDB")
            
            # Platform-specific restart commands
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['brew', 'services', 'restart', 'mongodb/brew/mongodb-community'], 
                             check=True)
            elif sys.platform == 'linux':
                subprocess.run(['sudo', 'systemctl', 'restart', 'mongod'], check=True)
            
            # Wait for service to come up
            time.sleep(5)
            
            # Verify it's running
            return self._check_mongodb()
            
        except Exception as e:
            self.logger.error(f"Failed to restart MongoDB: {e}")
            return False
    
    def _restart_rabbitmq(self) -> bool:
        """Restart RabbitMQ service."""
        try:
            self.logger.info("Attempting to restart RabbitMQ")
            
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['brew', 'services', 'restart', 'rabbitmq'], check=True)
            elif sys.platform == 'linux':
                subprocess.run(['sudo', 'systemctl', 'restart', 'rabbitmq-server'], 
                             check=True)
            
            # Wait for service to come up
            time.sleep(10)
            
            # Verify it's running
            return self._check_rabbitmq()
            
        except Exception as e:
            self.logger.error(f"Failed to restart RabbitMQ: {e}")
            return False
    
    def _restart_manager_agent(self) -> bool:
        """Restart manager agent."""
        try:
            self.logger.info("Attempting to restart manager agent")
            
            # Find and kill existing process
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'message_listener.py' in ' '.join(cmdline) and 'manager' in ' '.join(cmdline):
                        proc.terminate()
                        proc.wait(timeout=5)
                except:
                    pass
            
            # Start new instance
            subprocess.Popen([
                sys.executable,
                '.agents/manager/message_listener.py'
            ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Wait for startup
            time.sleep(5)
            
            return self._check_manager_agent()
            
        except Exception as e:
            self.logger.error(f"Failed to restart manager agent: {e}")
            return False
    
    def _restart_developer_agent(self) -> bool:
        """Restart developer agent."""
        try:
            self.logger.info("Attempting to restart developer agent")
            
            # Find and kill existing process
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'message_listener.py' in ' '.join(cmdline) and 'developer' in ' '.join(cmdline):
                        proc.terminate()
                        proc.wait(timeout=5)
                except:
                    pass
            
            # Start new instance
            subprocess.Popen([
                sys.executable,
                '.agents/developer/message_listener.py'
            ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Wait for startup
            time.sleep(5)
            
            return self._check_developer_agent()
            
        except Exception as e:
            self.logger.error(f"Failed to restart developer agent: {e}")
            return False
    
    def _reconnect_mongodb(self) -> bool:
        """Reconnect to MongoDB with retry logic."""
        attempt = 0
        delay = self.db_retry_config['initial_delay']
        
        while attempt < self.db_retry_config['max_attempts']:
            try:
                self.logger.info(f"MongoDB reconnection attempt {attempt + 1}")
                
                sm = StateManager()
                if sm.is_connected():
                    sm.disconnect()
                    self.logger.info("Successfully reconnected to MongoDB")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
            
            attempt += 1
            time.sleep(delay)
            delay = min(delay * self.db_retry_config['backoff_factor'], 
                       self.db_retry_config['max_delay'])
        
        return False
    
    def _reconnect_rabbitmq(self) -> bool:
        """Reconnect to RabbitMQ with retry logic."""
        attempt = 0
        delay = self.db_retry_config['initial_delay']
        
        while attempt < self.db_retry_config['max_attempts']:
            try:
                self.logger.info(f"RabbitMQ reconnection attempt {attempt + 1}")
                
                broker = MessageBroker()
                if broker.connect():
                    broker.disconnect()
                    self.logger.info("Successfully reconnected to RabbitMQ")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
            
            attempt += 1
            time.sleep(delay)
            delay = min(delay * self.db_retry_config['backoff_factor'], 
                       self.db_retry_config['max_delay'])
        
        return False
    
    def _stop_agent(self, agent: str):
        """Stop an agent process."""
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'message_listener.py' in ' '.join(cmdline):
                        if agent.replace('_agent', '') in ' '.join(cmdline):
                            proc.terminate()
                            proc.wait(timeout=5)
                            self.logger.info(f"Stopped {agent}")
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Error stopping {agent}: {e}")
    
    def _send_alert(self, message: str, priority: str = 'normal'):
        """Send alert notification."""
        # In production, this would integrate with alerting systems
        # like PagerDuty, email, Slack, etc.
        self.logger.critical(f"ALERT [{priority}]: {message}")
        
        # Log to alert file
        with open('logs/alerts.log', 'a') as f:
            f.write(f"{datetime.utcnow().isoformat()} [{priority}] {message}\n")
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery status."""
        return {
            'running': self.running,
            'pending_actions': len(self.recovery_queue),
            'recent_recoveries': self.recovery_history[-10:],
            'component_status': {
                name: self.components[name]['check_func']()
                for name in self.components
            }
        }


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Recovery Manager')
    parser.add_argument('--check-interval', type=int, default=30,
                       help='Health check interval in seconds')
    parser.add_argument('--status', action='store_true',
                       help='Show current status and exit')
    
    args = parser.parse_args()
    
    manager = RecoveryManager({
        'check_interval': args.check_interval
    })
    
    if args.status:
        # Show status
        status = manager.get_recovery_status()
        print(json.dumps(status, indent=2, default=str))
    else:
        # Run as service
        print("Starting Recovery Manager...")
        if manager.start():
            print(f"Recovery Manager running (check interval: {args.check_interval}s)")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping Recovery Manager...")
                manager.stop()
        else:
            print("Failed to start Recovery Manager")
            sys.exit(1)


if __name__ == '__main__':
    main()