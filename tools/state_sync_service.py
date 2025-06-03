#!/usr/bin/env python3
"""
State Synchronization Service

Ensures consistency between RabbitMQ message queues and MongoDB database state.
Handles recovery, reconciliation, and automatic repair of inconsistencies.
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager
from tools.message_broker import MessageBroker, BrokerConfig


class InconsistencyType(Enum):
    """Types of inconsistencies that can occur."""
    TASK_IN_QUEUE_NOT_DB = "task_in_queue_not_database"
    TASK_IN_DB_NOT_QUEUE = "task_in_database_not_queue"
    STATE_MISMATCH = "state_mismatch"
    STALLED_TASK = "stalled_task"
    ORPHANED_MESSAGE = "orphaned_message"
    AGENT_UNRESPONSIVE = "agent_unresponsive"


@dataclass
class Inconsistency:
    """Represents a detected inconsistency."""
    type: InconsistencyType
    task_id: Optional[str]
    agent_id: Optional[str]
    details: Dict[str, Any]
    severity: str  # 'critical', 'high', 'medium', 'low'
    detected_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None


class StateSyncService:
    """
    Service for synchronizing state between RabbitMQ and MongoDB.
    
    Features:
    - Periodic synchronization checks
    - Inconsistency detection and resolution
    - Stalled task recovery
    - Agent health monitoring
    - Automatic repair capabilities
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the state synchronization service.
        
        Args:
            config: Service configuration
        """
        self.config = config or {}
        self.sync_interval = self.config.get('sync_interval', 60)  # seconds
        self.stall_timeout = self.config.get('stall_timeout', 3600)  # 1 hour
        self.heartbeat_timeout = self.config.get('heartbeat_timeout', 300)  # 5 minutes
        
        # Initialize connections
        self.state_manager = StateManager()
        self.broker = MessageBroker()
        
        # Service state
        self.running = False
        self.sync_thread = None
        self.inconsistencies: List[Inconsistency] = []
        self.last_sync = None
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the service."""
        self.logger = logging.getLogger('StateSyncService')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/state_sync.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def start(self) -> bool:
        """
        Start the synchronization service.
        
        Returns:
            bool: True if started successfully
        """
        try:
            # Connect to services
            if not self.state_manager.is_connected():
                self.logger.error("Failed to connect to MongoDB")
                return False
            
            if not self.broker.connect():
                self.logger.error("Failed to connect to RabbitMQ")
                return False
            
            # Start sync thread
            self.running = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            
            self.logger.info("State synchronization service started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False
    
    def stop(self):
        """Stop the synchronization service."""
        self.running = False
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        self.broker.disconnect()
        self.state_manager.disconnect()
        
        self.logger.info("State synchronization service stopped")
    
    def _sync_loop(self):
        """Main synchronization loop."""
        while self.running:
            try:
                self.perform_sync()
                time.sleep(self.sync_interval)
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                time.sleep(10)  # Brief pause before retry
    
    def perform_sync(self) -> Dict[str, Any]:
        """
        Perform a complete state synchronization.
        
        Returns:
            Dict containing sync results
        """
        sync_start = datetime.utcnow()
        self.logger.info("Starting state synchronization")
        
        results = {
            'timestamp': sync_start,
            'inconsistencies_found': 0,
            'inconsistencies_resolved': 0,
            'errors': []
        }
        
        try:
            # Check queue-database consistency
            queue_inconsistencies = self.check_queue_database_consistency()
            results['inconsistencies_found'] += len(queue_inconsistencies)
            
            # Check for stalled tasks
            stalled_tasks = self.check_stalled_tasks()
            results['inconsistencies_found'] += len(stalled_tasks)
            
            # Check agent health
            agent_issues = self.check_agent_health()
            results['inconsistencies_found'] += len(agent_issues)
            
            # Resolve inconsistencies
            all_inconsistencies = queue_inconsistencies + stalled_tasks + agent_issues
            
            for inconsistency in all_inconsistencies:
                if self.resolve_inconsistency(inconsistency):
                    results['inconsistencies_resolved'] += 1
            
            # Update sync metadata
            self.last_sync = sync_start
            self._update_sync_status(results)
            
        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            results['errors'].append(str(e))
        
        sync_duration = (datetime.utcnow() - sync_start).total_seconds()
        self.logger.info(
            f"Sync completed in {sync_duration:.2f}s - "
            f"Found: {results['inconsistencies_found']}, "
            f"Resolved: {results['inconsistencies_resolved']}"
        )
        
        return results
    
    def check_queue_database_consistency(self) -> List[Inconsistency]:
        """
        Check consistency between message queues and database.
        
        Returns:
            List of detected inconsistencies
        """
        inconsistencies = []
        
        try:
            # Get messages from queues
            queue_messages = self._get_all_queue_messages()
            
            # Get active tasks from database
            db_tasks = self._get_active_database_tasks()
            
            # Check for messages without corresponding database entries
            for queue_name, messages in queue_messages.items():
                for message in messages:
                    task_id = message.get('task_id')
                    if task_id and task_id not in db_tasks:
                        inconsistencies.append(Inconsistency(
                            type=InconsistencyType.TASK_IN_QUEUE_NOT_DB,
                            task_id=task_id,
                            agent_id=message.get('to_agent'),
                            details={
                                'queue': queue_name,
                                'message': message
                            },
                            severity='high',
                            detected_at=datetime.utcnow()
                        ))
            
            # Check for database tasks without queue messages
            queue_task_ids = set()
            for messages in queue_messages.values():
                queue_task_ids.update(m.get('task_id') for m in messages if m.get('task_id'))
            
            for task_id, task in db_tasks.items():
                if task['status'] == 'assigned' and task_id not in queue_task_ids:
                    inconsistencies.append(Inconsistency(
                        type=InconsistencyType.TASK_IN_DB_NOT_QUEUE,
                        task_id=task_id,
                        agent_id=task.get('assigned_to'),
                        details={
                            'task': task
                        },
                        severity='medium',
                        detected_at=datetime.utcnow()
                    ))
            
        except Exception as e:
            self.logger.error(f"Error checking queue-database consistency: {e}")
        
        return inconsistencies
    
    def check_stalled_tasks(self) -> List[Inconsistency]:
        """
        Check for tasks that have been in progress too long.
        
        Returns:
            List of stalled task inconsistencies
        """
        inconsistencies = []
        
        try:
            stall_threshold = datetime.utcnow() - timedelta(seconds=self.stall_timeout)
            
            # Find tasks that have been in progress too long
            stalled = self.state_manager.db.tasks.find({
                'status': 'in_progress',
                'metadata.started_at': {'$lt': stall_threshold.isoformat()}
            })
            
            for task in stalled:
                inconsistencies.append(Inconsistency(
                    type=InconsistencyType.STALLED_TASK,
                    task_id=task['task_id'],
                    agent_id=task.get('assigned_to'),
                    details={
                        'started_at': task['metadata'].get('started_at'),
                        'duration': self._calculate_duration(task['metadata'].get('started_at'))
                    },
                    severity='high',
                    detected_at=datetime.utcnow()
                ))
            
        except Exception as e:
            self.logger.error(f"Error checking stalled tasks: {e}")
        
        return inconsistencies
    
    def check_agent_health(self) -> List[Inconsistency]:
        """
        Check agent health and responsiveness.
        
        Returns:
            List of agent health issues
        """
        inconsistencies = []
        
        try:
            heartbeat_threshold = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)
            
            # Check each agent
            for agent_id in ['manager', 'developer']:
                agent_state = self.state_manager.get_agent_state(agent_id)
                
                if not agent_state:
                    continue
                
                # Check last heartbeat
                last_heartbeat = agent_state.get('last_heartbeat')
                if last_heartbeat:
                    heartbeat_time = datetime.fromisoformat(
                        last_heartbeat.replace('Z', '+00:00')
                    )
                    
                    if heartbeat_time < heartbeat_threshold:
                        inconsistencies.append(Inconsistency(
                            type=InconsistencyType.AGENT_UNRESPONSIVE,
                            task_id=None,
                            agent_id=agent_id,
                            details={
                                'last_heartbeat': last_heartbeat,
                                'status': agent_state.get('status'),
                                'time_since_heartbeat': (datetime.utcnow() - heartbeat_time).total_seconds()
                            },
                            severity='critical',
                            detected_at=datetime.utcnow()
                        ))
            
        except Exception as e:
            self.logger.error(f"Error checking agent health: {e}")
        
        return inconsistencies
    
    def resolve_inconsistency(self, inconsistency: Inconsistency) -> bool:
        """
        Attempt to resolve an inconsistency.
        
        Args:
            inconsistency: The inconsistency to resolve
            
        Returns:
            bool: True if resolved successfully
        """
        try:
            self.logger.info(
                f"Attempting to resolve {inconsistency.type.value} "
                f"for task/agent: {inconsistency.task_id or inconsistency.agent_id}"
            )
            
            if inconsistency.type == InconsistencyType.TASK_IN_QUEUE_NOT_DB:
                return self._resolve_orphaned_message(inconsistency)
                
            elif inconsistency.type == InconsistencyType.TASK_IN_DB_NOT_QUEUE:
                return self._resolve_missing_queue_message(inconsistency)
                
            elif inconsistency.type == InconsistencyType.STALLED_TASK:
                return self._resolve_stalled_task(inconsistency)
                
            elif inconsistency.type == InconsistencyType.AGENT_UNRESPONSIVE:
                return self._resolve_unresponsive_agent(inconsistency)
            
            else:
                self.logger.warning(f"No resolver for inconsistency type: {inconsistency.type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error resolving inconsistency: {e}")
            return False
    
    def _resolve_orphaned_message(self, inconsistency: Inconsistency) -> bool:
        """Resolve message in queue without database entry."""
        try:
            message = inconsistency.details['message']
            task_id = message.get('task_id')
            
            # Create task in database from message
            task_data = {
                'task_id': task_id,
                'title': message.get('task', {}).get('title', 'Recovered Task'),
                'description': message.get('task', {}).get('description', ''),
                'status': 'assigned',
                'assigned_to': message.get('to_agent'),
                'assigned_by': message.get('from_agent'),
                'priority': message.get('priority', 'normal'),
                'recovered': True,
                'recovery_reason': 'orphaned_message'
            }
            
            if self.state_manager.create_task(task_data):
                self.logger.info(f"Created database entry for orphaned task: {task_id}")
                inconsistency.resolved = True
                inconsistency.resolution = "Created database entry"
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to resolve orphaned message: {e}")
        
        return False
    
    def _resolve_missing_queue_message(self, inconsistency: Inconsistency) -> bool:
        """Resolve database task without queue message."""
        try:
            task = inconsistency.details['task']
            task_id = task['task_id']
            
            # Re-queue the task
            message = {
                'message_type': 'task_assignment',
                'task_id': task_id,
                'from_agent': task.get('assigned_by', 'manager'),
                'to_agent': task.get('assigned_to', 'developer'),
                'timestamp': datetime.utcnow().isoformat(),
                'priority': task.get('priority', 'normal'),
                'task': {
                    'title': task.get('title'),
                    'description': task.get('description'),
                    'requirements': task.get('requirements', [])
                },
                'recovered': True,
                'recovery_reason': 'missing_queue_message'
            }
            
            queue_name = MessageBroker.DEVELOPER_QUEUE if task.get('assigned_to') == 'developer' else MessageBroker.MANAGER_QUEUE
            
            if self.broker.publish_message(queue_name, message):
                self.logger.info(f"Re-queued task: {task_id}")
                inconsistency.resolved = True
                inconsistency.resolution = "Re-queued task"
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to resolve missing queue message: {e}")
        
        return False
    
    def _resolve_stalled_task(self, inconsistency: Inconsistency) -> bool:
        """Resolve a stalled task by reassigning it."""
        try:
            task_id = inconsistency.task_id
            
            # Update task status back to assigned
            if self.state_manager.update_task_state(task_id, 'assigned', {
                'stalled_at': datetime.utcnow().isoformat(),
                'reassigned': True,
                'previous_duration': inconsistency.details.get('duration')
            }):
                # Re-queue the task
                task = self.state_manager.get_task(task_id)
                if task:
                    message = {
                        'message_type': 'task_assignment',
                        'task_id': task_id,
                        'from_agent': 'manager',
                        'to_agent': task.get('assigned_to', 'developer'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'priority': 'high',  # Increase priority
                        'task': {
                            'title': task.get('title'),
                            'description': task.get('description'),
                            'requirements': task.get('requirements', [])
                        },
                        'recovered': True,
                        'recovery_reason': 'stalled_task'
                    }
                    
                    queue_name = MessageBroker.DEVELOPER_QUEUE if task.get('assigned_to') == 'developer' else MessageBroker.MANAGER_QUEUE
                    
                    if self.broker.publish_message(queue_name, message):
                        self.logger.info(f"Reassigned stalled task: {task_id}")
                        inconsistency.resolved = True
                        inconsistency.resolution = "Task reassigned"
                        return True
                        
        except Exception as e:
            self.logger.error(f"Failed to resolve stalled task: {e}")
        
        return False
    
    def _resolve_unresponsive_agent(self, inconsistency: Inconsistency) -> bool:
        """Handle unresponsive agent."""
        try:
            agent_id = inconsistency.agent_id
            
            # Update agent status to error
            self.state_manager.update_agent_state(agent_id, 'error', {
                'error': 'unresponsive',
                'last_known_heartbeat': inconsistency.details.get('last_heartbeat'),
                'marked_unresponsive_at': datetime.utcnow().isoformat()
            })
            
            # Reassign agent's active tasks
            active_tasks = self.state_manager.get_agent_tasks(agent_id, ['assigned', 'in_progress'])
            
            for task in active_tasks:
                # Update task to show it needs reassignment
                self.state_manager.update_task_state(task['task_id'], 'created', {
                    'previous_assignee': agent_id,
                    'reassignment_reason': 'agent_unresponsive'
                })
            
            self.logger.warning(
                f"Marked agent {agent_id} as unresponsive and "
                f"reassigned {len(active_tasks)} tasks"
            )
            
            inconsistency.resolved = True
            inconsistency.resolution = f"Agent marked as error, {len(active_tasks)} tasks reassigned"
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle unresponsive agent: {e}")
        
        return False
    
    def _get_all_queue_messages(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all messages from monitored queues."""
        messages = {}
        
        queues = [
            MessageBroker.MANAGER_QUEUE,
            MessageBroker.DEVELOPER_QUEUE,
            MessageBroker.WORK_REQUEST_QUEUE
        ]
        
        for queue in queues:
            messages[queue] = self._peek_queue_messages(queue)
        
        return messages
    
    def _peek_queue_messages(self, queue_name: str) -> List[Dict[str, Any]]:
        """Peek at messages in a queue without consuming them."""
        messages = []
        
        try:
            # This is a simplified version - in production you'd use
            # RabbitMQ management API or a dedicated inspection method
            method = self.broker.channel.queue_declare(queue=queue_name, passive=True)
            message_count = method.method.message_count
            
            if message_count > 0:
                # Note: This is for demonstration - actual implementation
                # would use management API to inspect messages
                self.logger.debug(f"Queue {queue_name} has {message_count} messages")
        
        except Exception as e:
            self.logger.error(f"Error peeking at queue {queue_name}: {e}")
        
        return messages
    
    def _get_active_database_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks from database."""
        tasks = {}
        
        try:
            active_tasks = self.state_manager.db.tasks.find({
                'status': {'$in': ['created', 'assigned', 'in_progress']}
            })
            
            for task in active_tasks:
                tasks[task['task_id']] = task
                
        except Exception as e:
            self.logger.error(f"Error getting active tasks: {e}")
        
        return tasks
    
    def _calculate_duration(self, start_time_str: str) -> float:
        """Calculate duration from start time to now."""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            return (datetime.utcnow() - start_time).total_seconds()
        except:
            return 0
    
    def _update_sync_status(self, results: Dict[str, Any]):
        """Update sync status in database."""
        try:
            self.state_manager.db.sync_status.replace_one(
                {'_id': 'state_sync'},
                {
                    '_id': 'state_sync',
                    'last_sync': results['timestamp'],
                    'inconsistencies_found': results['inconsistencies_found'],
                    'inconsistencies_resolved': results['inconsistencies_resolved'],
                    'errors': results['errors'],
                    'status': 'healthy' if not results['errors'] else 'degraded'
                },
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"Failed to update sync status: {e}")
    
    def get_sync_report(self) -> Dict[str, Any]:
        """Get a report of recent sync activities."""
        report = {
            'service_status': 'running' if self.running else 'stopped',
            'last_sync': self.last_sync,
            'recent_inconsistencies': [],
            'summary': defaultdict(int)
        }
        
        # Get recent inconsistencies
        for inc in self.inconsistencies[-100:]:  # Last 100
            report['recent_inconsistencies'].append({
                'type': inc.type.value,
                'severity': inc.severity,
                'detected': inc.detected_at.isoformat(),
                'resolved': inc.resolved,
                'resolution': inc.resolution
            })
            
            # Update summary
            report['summary'][inc.type.value] += 1
            if inc.resolved:
                report['summary']['resolved'] += 1
        
        return report


def main():
    """Main entry point for running the service standalone."""
    import argparse
    
    parser = argparse.ArgumentParser(description='State Synchronization Service')
    parser.add_argument('--interval', type=int, default=60, help='Sync interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run sync once and exit')
    
    args = parser.parse_args()
    
    # Configure service
    config = {
        'sync_interval': args.interval
    }
    
    service = StateSyncService(config)
    
    if args.once:
        # Run single sync
        if service.state_manager.is_connected() and service.broker.connect():
            results = service.perform_sync()
            print(json.dumps(results, indent=2, default=str))
            service.broker.disconnect()
            service.state_manager.disconnect()
    else:
        # Run as service
        print("Starting State Synchronization Service...")
        if service.start():
            print(f"Service running (sync interval: {args.interval}s)")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping service...")
                service.stop()
        else:
            print("Failed to start service")
            sys.exit(1)


if __name__ == '__main__':
    main()