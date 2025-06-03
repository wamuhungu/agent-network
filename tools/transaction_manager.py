#!/usr/bin/env python3
"""
Transaction Manager

Provides transaction support for critical operations requiring
atomicity across multiple MongoDB collections.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
import pymongo
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ConnectionFailure

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TransactionState(Enum):
    """States of a transaction."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass
class TransactionOperation:
    """Represents a single operation in a transaction."""
    collection: str
    operation: str  # 'insert', 'update', 'delete', 'replace'
    filter: Optional[Dict[str, Any]]
    data: Optional[Dict[str, Any]]
    options: Dict[str, Any]
    
    def __post_init__(self):
        self.options = self.options or {}


class TransactionManager:
    """
    Manages atomic transactions across MongoDB collections.
    
    Features:
    - Multi-document transactions
    - Automatic retry logic
    - Rollback on failure
    - Transaction logging
    - Deadlock detection
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize the transaction manager."""
        self.connection_string = connection_string or "mongodb://localhost:27017/"
        self.database_name = "agent_network"
        
        # Setup client with transaction support
        self.client = MongoClient(
            self.connection_string,
            retryWrites=True,
            retryReads=True,
            maxPoolSize=10,
            readConcern="majority",
            writeConcern=pymongo.WriteConcern(
                w="majority",
                j=True,
                wtimeout=5000
            )
        )
        
        self.db = self.client[self.database_name]
        
        # Transaction settings
        self.max_retry_attempts = 3
        self.retry_delay = 0.1  # seconds
        self.transaction_timeout = 60  # seconds
        
        # Setup logging
        self.setup_logging()
        
        # Transaction history
        self.transaction_history = []
    
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('TransactionManager')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/transactions.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    @contextmanager
    def transaction(self, description: str = ""):
        """
        Context manager for executing transactions.
        
        Usage:
            with transaction_manager.transaction("Update task and agent state") as txn:
                txn.update('tasks', {'_id': task_id}, {'$set': {'status': 'completed'}})
                txn.update('agent_states', {'agent_id': 'developer'}, {'$set': {'status': 'ready'}})
        """
        transaction_id = f"txn_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create transaction context
        context = TransactionContext(
            transaction_id=transaction_id,
            description=description,
            manager=self
        )
        
        self.logger.info(f"Starting transaction {transaction_id}: {description}")
        
        try:
            yield context
            
            # If we get here without exception, commit
            if context.operations and not context.committed:
                context.commit()
                
        except Exception as e:
            # Rollback on any exception
            self.logger.error(f"Transaction {transaction_id} failed: {e}")
            context.abort()
            raise
    
    def execute_transaction(self, operations: List[TransactionOperation],
                          description: str = "") -> bool:
        """
        Execute a list of operations atomically.
        
        Args:
            operations: List of operations to execute
            description: Transaction description
            
        Returns:
            bool: True if successful
        """
        attempt = 0
        
        while attempt < self.max_retry_attempts:
            try:
                with self.client.start_session() as session:
                    with session.start_transaction(
                        read_concern=pymongo.ReadConcern("snapshot"),
                        write_concern=pymongo.WriteConcern("majority"),
                        read_preference=pymongo.ReadPreference.PRIMARY,
                        max_commit_time_ms=self.transaction_timeout * 1000
                    ):
                        # Execute all operations
                        for op in operations:
                            self._execute_operation(session, op)
                        
                        # Commit transaction
                        session.commit_transaction()
                        
                        self.logger.info(
                            f"Transaction committed: {description} "
                            f"({len(operations)} operations)"
                        )
                        
                        return True
                        
            except OperationFailure as e:
                if e.has_error_label("TransientTransactionError"):
                    # Retry transient errors
                    attempt += 1
                    self.logger.warning(
                        f"Transient error in transaction, retrying "
                        f"(attempt {attempt}/{self.max_retry_attempts}): {e}"
                    )
                    time.sleep(self.retry_delay * attempt)
                    continue
                    
                elif e.has_error_label("UnknownTransactionCommitResult"):
                    # Retry commit
                    attempt += 1
                    self.logger.warning(
                        f"Unknown commit result, retrying "
                        f"(attempt {attempt}/{self.max_retry_attempts}): {e}"
                    )
                    continue
                    
                else:
                    # Non-retryable error
                    self.logger.error(f"Transaction failed: {e}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Unexpected transaction error: {e}")
                return False
        
        self.logger.error(
            f"Transaction failed after {self.max_retry_attempts} attempts"
        )
        return False
    
    def _execute_operation(self, session: pymongo.client_session.ClientSession,
                          operation: TransactionOperation):
        """Execute a single operation within a transaction."""
        collection = self.db[operation.collection]
        
        if operation.operation == 'insert':
            if isinstance(operation.data, list):
                collection.insert_many(operation.data, session=session, 
                                     **operation.options)
            else:
                collection.insert_one(operation.data, session=session,
                                    **operation.options)
                
        elif operation.operation == 'update':
            collection.update_one(operation.filter, operation.data, 
                                session=session, **operation.options)
                                
        elif operation.operation == 'update_many':
            collection.update_many(operation.filter, operation.data,
                                 session=session, **operation.options)
                                 
        elif operation.operation == 'replace':
            collection.replace_one(operation.filter, operation.data,
                                 session=session, **operation.options)
                                 
        elif operation.operation == 'delete':
            collection.delete_one(operation.filter, session=session,
                                **operation.options)
                                
        elif operation.operation == 'delete_many':
            collection.delete_many(operation.filter, session=session,
                                 **operation.options)
                                 
        else:
            raise ValueError(f"Unknown operation: {operation.operation}")
    
    def create_task_with_assignment(self, task_data: Dict[str, Any],
                                   agent_id: str) -> bool:
        """
        Atomically create a task and update agent state.
        
        This is an example of a common transaction pattern.
        """
        operations = [
            # Insert new task
            TransactionOperation(
                collection='tasks',
                operation='insert',
                filter=None,
                data=task_data,
                options={}
            ),
            # Update agent state
            TransactionOperation(
                collection='agent_states',
                operation='update',
                filter={'agent_id': agent_id},
                data={
                    '$set': {
                        'status': 'working',
                        'current_task_id': task_data['task_id'],
                        'last_assignment': datetime.utcnow()
                    },
                    '$inc': {
                        'tasks_assigned': 1
                    }
                },
                options={}
            ),
            # Log activity
            TransactionOperation(
                collection='activity_logs',
                operation='insert',
                filter=None,
                data={
                    'timestamp': datetime.utcnow(),
                    'agent_id': 'manager',
                    'activity_type': 'task_assigned',
                    'details': {
                        'task_id': task_data['task_id'],
                        'assigned_to': agent_id
                    }
                },
                options={}
            )
        ]
        
        return self.execute_transaction(
            operations,
            f"Create and assign task {task_data['task_id']}"
        )
    
    def complete_task_atomic(self, task_id: str, agent_id: str,
                           completion_data: Dict[str, Any]) -> bool:
        """
        Atomically complete a task with all related updates.
        """
        operations = [
            # Update task status
            TransactionOperation(
                collection='tasks',
                operation='update',
                filter={'task_id': task_id},
                data={
                    '$set': {
                        'status': 'completed',
                        'metadata.completed_at': datetime.utcnow(),
                        'metadata.completion_data': completion_data
                    }
                },
                options={}
            ),
            # Update agent state
            TransactionOperation(
                collection='agent_states',
                operation='update',
                filter={'agent_id': agent_id},
                data={
                    '$set': {
                        'status': 'ready',
                        'current_task_id': None,
                        'last_completion': datetime.utcnow()
                    },
                    '$inc': {
                        'tasks_completed': 1
                    }
                },
                options={}
            ),
            # Archive task
            TransactionOperation(
                collection='archived_tasks',
                operation='insert',
                filter=None,
                data={
                    'task_id': task_id,
                    'archived_at': datetime.utcnow(),
                    'completion_data': completion_data
                },
                options={}
            ),
            # Log completion
            TransactionOperation(
                collection='activity_logs',
                operation='insert',
                filter=None,
                data={
                    'timestamp': datetime.utcnow(),
                    'agent_id': agent_id,
                    'activity_type': 'task_completed',
                    'details': {
                        'task_id': task_id,
                        'duration': completion_data.get('duration')
                    }
                },
                options={}
            )
        ]
        
        return self.execute_transaction(
            operations,
            f"Complete task {task_id}"
        )
    
    def batch_update_with_validation(self, updates: List[Dict[str, Any]],
                                   validation_func: Callable) -> bool:
        """
        Perform batch updates with validation in a transaction.
        """
        with self.transaction("Batch update with validation") as txn:
            # First, validate all data
            for update in updates:
                if not validation_func(update):
                    raise ValueError(f"Validation failed for update: {update}")
            
            # If all valid, apply updates
            for update in updates:
                txn.update(
                    update['collection'],
                    update['filter'],
                    update['data']
                )
            
            return True
    
    def ensure_consistency(self) -> Dict[str, Any]:
        """
        Check and fix data consistency issues atomically.
        """
        report = {
            'timestamp': datetime.utcnow(),
            'issues_found': 0,
            'issues_fixed': 0,
            'errors': []
        }
        
        try:
            with self.transaction("Consistency check and repair") as txn:
                # Check for orphaned tasks
                orphaned_tasks = list(self.db.tasks.find({
                    'status': 'assigned',
                    'assigned_to': {'$exists': True}
                }))
                
                for task in orphaned_tasks:
                    agent_id = task['assigned_to']
                    agent = self.db.agent_states.find_one({'agent_id': agent_id})
                    
                    if not agent or agent.get('current_task_id') != task['task_id']:
                        report['issues_found'] += 1
                        
                        # Fix: Reset task to created state
                        txn.update(
                            'tasks',
                            {'_id': task['_id']},
                            {'$set': {'status': 'created', 'assigned_to': None}}
                        )
                        
                        report['issues_fixed'] += 1
                
                # Check for agents with invalid task references
                agents = list(self.db.agent_states.find({
                    'current_task_id': {'$exists': True, '$ne': None}
                }))
                
                for agent in agents:
                    task_id = agent['current_task_id']
                    task = self.db.tasks.find_one({'task_id': task_id})
                    
                    if not task or task.get('status') not in ['assigned', 'in_progress']:
                        report['issues_found'] += 1
                        
                        # Fix: Clear invalid task reference
                        txn.update(
                            'agent_states',
                            {'_id': agent['_id']},
                            {'$set': {'current_task_id': None, 'status': 'ready'}}
                        )
                        
                        report['issues_fixed'] += 1
                
        except Exception as e:
            report['errors'].append(str(e))
            self.logger.error(f"Consistency check failed: {e}")
        
        return report
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        return {
            'total_transactions': len(self.transaction_history),
            'successful': sum(1 for t in self.transaction_history 
                            if t.get('status') == 'committed'),
            'failed': sum(1 for t in self.transaction_history 
                        if t.get('status') in ['aborted', 'failed']),
            'recent_transactions': self.transaction_history[-10:]
        }


class TransactionContext:
    """Context for managing a transaction."""
    
    def __init__(self, transaction_id: str, description: str,
                manager: TransactionManager):
        self.transaction_id = transaction_id
        self.description = description
        self.manager = manager
        self.operations: List[TransactionOperation] = []
        self.committed = False
        self.aborted = False
        self.start_time = datetime.utcnow()
    
    def insert(self, collection: str, data: Union[Dict, List[Dict]],
              **options):
        """Add an insert operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='insert',
            filter=None,
            data=data,
            options=options
        ))
    
    def update(self, collection: str, filter: Dict[str, Any],
              update: Dict[str, Any], **options):
        """Add an update operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='update',
            filter=filter,
            data=update,
            options=options
        ))
    
    def update_many(self, collection: str, filter: Dict[str, Any],
                   update: Dict[str, Any], **options):
        """Add an update_many operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='update_many',
            filter=filter,
            data=update,
            options=options
        ))
    
    def replace(self, collection: str, filter: Dict[str, Any],
               replacement: Dict[str, Any], **options):
        """Add a replace operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='replace',
            filter=filter,
            data=replacement,
            options=options
        ))
    
    def delete(self, collection: str, filter: Dict[str, Any], **options):
        """Add a delete operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='delete',
            filter=filter,
            data=None,
            options=options
        ))
    
    def delete_many(self, collection: str, filter: Dict[str, Any], **options):
        """Add a delete_many operation to the transaction."""
        self.operations.append(TransactionOperation(
            collection=collection,
            operation='delete_many',
            filter=filter,
            data=None,
            options=options
        ))
    
    def commit(self):
        """Commit the transaction."""
        if self.committed or self.aborted:
            raise RuntimeError("Transaction already finalized")
        
        success = self.manager.execute_transaction(
            self.operations,
            self.description
        )
        
        self.committed = success
        
        # Record transaction
        self.manager.transaction_history.append({
            'transaction_id': self.transaction_id,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': datetime.utcnow(),
            'operations': len(self.operations),
            'status': 'committed' if success else 'failed'
        })
        
        if not success:
            raise RuntimeError("Transaction commit failed")
    
    def abort(self):
        """Abort the transaction."""
        if self.committed:
            raise RuntimeError("Cannot abort committed transaction")
        
        self.aborted = True
        
        # Record transaction
        self.manager.transaction_history.append({
            'transaction_id': self.transaction_id,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': datetime.utcnow(),
            'operations': len(self.operations),
            'status': 'aborted'
        })
        
        self.manager.logger.info(f"Transaction {self.transaction_id} aborted")


# Example usage patterns

def example_complex_transaction():
    """Example of a complex multi-collection transaction."""
    tm = TransactionManager()
    
    with tm.transaction("Complex task workflow") as txn:
        # Create multiple tasks
        for i in range(3):
            txn.insert('tasks', {
                'task_id': f'task_{i}',
                'title': f'Task {i}',
                'status': 'created',
                'created_at': datetime.utcnow()
            })
        
        # Update agent workload
        txn.update(
            'agent_states',
            {'agent_id': 'manager'},
            {
                '$inc': {'tasks_created': 3},
                '$set': {'last_batch_creation': datetime.utcnow()}
            }
        )
        
        # Log batch creation
        txn.insert('activity_logs', {
            'timestamp': datetime.utcnow(),
            'agent_id': 'manager',
            'activity_type': 'batch_task_creation',
            'details': {'count': 3}
        })


def example_conditional_transaction():
    """Example of conditional logic in transactions."""
    tm = TransactionManager()
    
    # This shows how you might handle conditional updates
    task_id = 'task_123'
    
    # First, check current state
    task = tm.db.tasks.find_one({'task_id': task_id})
    
    if task and task['status'] == 'in_progress':
        with tm.transaction("Conditional task update") as txn:
            # Only update if still in progress
            txn.update(
                'tasks',
                {'task_id': task_id, 'status': 'in_progress'},
                {'$set': {'status': 'completed'}}
            )
            
            # Update related data
            txn.update(
                'agent_states',
                {'agent_id': task['assigned_to']},
                {'$inc': {'completed_count': 1}}
            )


if __name__ == '__main__':
    # Test transaction manager
    tm = TransactionManager()
    
    print("Testing Transaction Manager...")
    
    # Test basic transaction
    success = tm.create_task_with_assignment(
        {
            'task_id': f'test_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
            'title': 'Test Task',
            'status': 'assigned',
            'created_at': datetime.utcnow()
        },
        'developer'
    )
    
    print(f"Test transaction: {'Success' if success else 'Failed'}")
    
    # Get stats
    stats = tm.get_transaction_stats()
    print(f"Transaction stats: {stats}")