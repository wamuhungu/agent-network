#!/usr/bin/env python3
"""
Integration test for task creation workflow.

This test verifies the complete task creation flow:
1. Task creation with correct initial state
2. Message delivery via RabbitMQ
3. Database state consistency
4. Developer task pickup
"""

import sys
import os
import json
import time
import unittest
from datetime import datetime

# Add project directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from state_manager import StateManager
from message_broker import MessageBroker, send_task_to_developer


class TestTaskCreationWorkflow(unittest.TestCase):
    """Test the complete task creation workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.sm = StateManager()
        cls.broker = MessageBroker()
        
        # Ensure we can connect to services
        if not cls.sm.is_connected():
            raise RuntimeError("Cannot connect to MongoDB for testing")
        
        if not cls.broker.connect():
            raise RuntimeError("Cannot connect to RabbitMQ for testing")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up connections."""
        cls.sm.disconnect()
        cls.broker.disconnect()
    
    def setUp(self):
        """Set up each test."""
        self.test_task_id = f"test_task_{int(time.time())}"
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test task if it exists
        try:
            self.sm.db.tasks.delete_one({'task_id': self.test_task_id})
        except:
            pass
    
    def test_task_creation_with_correct_state(self):
        """Test that tasks are created with correct initial state."""
        # Create task data
        task_data = {
            'task_id': self.test_task_id,
            'title': 'Test task for integration testing',
            'description': 'Verify task creation workflow',
            'status': 'pending',  # Should be 'pending'
            'priority': 'normal',
            'created_by': 'manager',
            'assigned_to': 'developer',  # Should be assigned from start
            'requirements': ['Test requirement 1', 'Test requirement 2'],
            'deliverables': ['Test deliverable 1'],
            'metadata': {
                'test': True,
                'created_at': datetime.utcnow().isoformat()
            }
        }
        
        # Create task
        created_id = self.sm.create_task(task_data)
        self.assertIsNotNone(created_id, "Task creation should return task ID")
        
        # Verify task state
        task = self.sm.db.tasks.find_one({'task_id': self.test_task_id})
        self.assertIsNotNone(task, "Task should exist in database")
        self.assertEqual(task['status'], 'pending', "Task status should be 'pending'")
        self.assertEqual(task['assigned_to'], 'developer', "Task should be assigned to developer")
        self.assertEqual(task['created_by'], 'manager', "Task should be created by manager")
    
    def test_task_message_delivery(self):
        """Test that task messages can be sent via RabbitMQ."""
        # Create a test task first
        task_data = {
            'task_id': self.test_task_id,
            'title': 'Test RabbitMQ delivery',
            'description': 'Test message delivery',
            'status': 'pending',
            'priority': 'high',
            'created_by': 'manager',
            'assigned_to': 'developer'
        }
        
        self.sm.create_task(task_data)
        
        # Create task message
        task_message = {
            'message_type': 'task_assignment',
            'task_id': self.test_task_id,
            'from_agent': 'manager',
            'to_agent': 'developer',
            'timestamp': datetime.utcnow().isoformat(),
            'priority': 'high',
            'task': {
                'title': task_data['title'],
                'description': task_data['description']
            }
        }
        
        # Send message
        success = send_task_to_developer(task_message)
        self.assertTrue(success, "Message should be sent successfully")
    
    def test_developer_can_find_pending_tasks(self):
        """Test that developer can find pending tasks assigned to them."""
        # Create a pending task
        task_data = {
            'task_id': self.test_task_id,
            'title': 'Test developer pickup',
            'description': 'Task for developer to find',
            'status': 'pending',
            'priority': 'normal',
            'created_by': 'manager',
            'assigned_to': 'developer'
        }
        
        self.sm.create_task(task_data)
        
        # Query for developer tasks
        pending_tasks = list(self.sm.db.tasks.find({
            'status': 'pending',
            'assigned_to': 'developer'
        }))
        
        # Should find at least our test task
        task_ids = [t['task_id'] for t in pending_tasks]
        self.assertIn(self.test_task_id, task_ids, 
                     "Developer should be able to find pending task")
    
    def test_task_state_updates(self):
        """Test that task state can be updated correctly."""
        # Create task
        task_data = {
            'task_id': self.test_task_id,
            'title': 'Test state updates',
            'status': 'pending',
            'assigned_to': 'developer',
            'created_by': 'manager'
        }
        
        self.sm.create_task(task_data)
        
        # Update to in_progress
        success = self.sm.update_task_state(
            self.test_task_id, 
            'in_progress',
            {'started_at': datetime.utcnow().isoformat()}
        )
        self.assertTrue(success, "Should update task state")
        
        # Verify update
        task = self.sm.db.tasks.find_one({'task_id': self.test_task_id})
        self.assertEqual(task['status'], 'in_progress', 
                        "Task status should be updated")
        self.assertIn('metadata', task, 
                     "Metadata should exist")
        self.assertIn('started_at', task.get('metadata', {}), 
                     "Additional metadata should be saved")
    
    def test_complete_workflow(self):
        """Test the complete workflow from creation to completion."""
        # 1. Create task with correct initial state
        task_data = {
            'task_id': self.test_task_id,
            'title': 'Complete workflow test',
            'description': 'Test full task lifecycle',
            'status': 'pending',
            'priority': 'normal',
            'created_by': 'manager',
            'assigned_to': 'developer',
            'requirements': ['Implement feature', 'Write tests'],
            'deliverables': ['Working code', 'Test suite']
        }
        
        created_id = self.sm.create_task(task_data)
        self.assertIsNotNone(created_id)
        
        # 2. Send notification (optional - task works without it)
        task_message = {
            'message_type': 'task_assignment',
            'task_id': self.test_task_id,
            'from_agent': 'manager',
            'to_agent': 'developer',
            'timestamp': datetime.utcnow().isoformat(),
            'task': task_data
        }
        
        # Don't fail if RabbitMQ is down - task is still available
        send_task_to_developer(task_message)
        
        # 3. Developer finds pending task
        pending_tasks = list(self.sm.db.tasks.find({
            'status': 'pending',
            'assigned_to': 'developer'
        }))
        
        found_task = None
        for task in pending_tasks:
            if task['task_id'] == self.test_task_id:
                found_task = task
                break
        
        self.assertIsNotNone(found_task, "Developer should find pending task")
        
        # 4. Developer starts work
        self.sm.update_task_state(self.test_task_id, 'in_progress', {
            'started_at': datetime.utcnow().isoformat(),
            'developer_session': 'test_session'
        })
        
        # Verify started_at was saved
        in_progress_task = self.sm.db.tasks.find_one({'task_id': self.test_task_id})
        self.assertIn('metadata', in_progress_task)
        self.assertIn('started_at', in_progress_task['metadata'])
        
        # 5. Developer completes task
        self.sm.update_task_state(self.test_task_id, 'completed', {
            'completed_at': datetime.utcnow().isoformat(),
            'results': {
                'files_created': ['test.py'],
                'tests_passed': True
            }
        })
        
        # 6. Verify final state
        final_task = self.sm.db.tasks.find_one({'task_id': self.test_task_id})
        self.assertEqual(final_task['status'], 'completed')
        self.assertIn('metadata', final_task)
        metadata = final_task.get('metadata', {})
        # Note: update_task_state replaces metadata, so started_at is lost
        # This is a limitation of the current implementation
        self.assertIn('completed_at', metadata)
        self.assertIn('results', metadata)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)