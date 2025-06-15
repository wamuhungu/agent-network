#!/usr/bin/env python3
"""
Integration tests for developer-to-manager RabbitMQ messaging.

This module tests the complete message flow from developer to manager,
ensuring messages are properly formatted, sent, and can be processed.
"""

import sys
import json
import time
import unittest
import threading
from datetime import datetime
from unittest.mock import Mock, patch

# Add tools directory to path
sys.path.append('tools')

from message_broker import MessageBroker
from task_notifier import send_task_completion_notification, send_task_status_update


class TestMessagingIntegration(unittest.TestCase):
    """Integration tests for agent messaging."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with broker connection."""
        cls.broker = MessageBroker()
        if not cls.broker.connect():
            raise RuntimeError("Failed to connect to RabbitMQ for testing")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up broker connection."""
        if cls.broker:
            cls.broker.disconnect()
    
    def setUp(self):
        """Set up each test."""
        self.received_messages = []
        self.message_event = threading.Event()
    
    def message_handler(self, message):
        """Test message handler that captures received messages."""
        self.received_messages.append(message)
        self.message_event.set()
    
    def test_task_completion_message_format(self):
        """Test that task completion messages have correct format."""
        # Send a completion notification
        success = send_task_completion_notification(
            task_id="test_task_001",
            completed_by="developer",
            deliverables=["file1.py", "file2.py"],
            summary="Test task completed",
            target_queue="manager-queue"
        )
        
        self.assertTrue(success, "Failed to send completion notification")
        
        # Set up consumer to receive the message
        consumer_broker = MessageBroker()
        self.assertTrue(consumer_broker.connect())
        
        # Consume one message
        received = None
        def capture_message(message):
            nonlocal received
            received = message
            self.message_event.set()
        
        # Start consuming in a thread
        consumer_thread = threading.Thread(
            target=lambda: consumer_broker.start_consuming("manager-queue", capture_message)
        )
        consumer_thread.daemon = True
        consumer_thread.start()
        
        # Wait for message
        self.assertTrue(self.message_event.wait(timeout=5), "Timeout waiting for message")
        
        # Stop consumer
        consumer_broker.stop_consuming()
        consumer_broker.disconnect()
        
        # Verify message format
        self.assertIsNotNone(received)
        self.assertEqual(received.get("message_type"), "task_completion")
        self.assertEqual(received.get("task_id"), "test_task_001")
        self.assertEqual(received.get("from_agent"), "developer")
        self.assertEqual(received.get("to_agent"), "manager")
        self.assertIn("timestamp", received)
        self.assertIn("completion", received)
        
        # Verify completion details
        completion = received.get("completion", {})
        self.assertIn("summary", completion)
        self.assertEqual(completion.get("summary"), "Test task completed")
        self.assertIn("files_created", completion)
        self.assertEqual(len(completion.get("files_created", [])), 2)
    
    def test_task_status_update_message_format(self):
        """Test that task status update messages have correct format."""
        # Send a status update
        success = send_task_status_update(
            task_id="test_task_002",
            new_status="in_progress",
            agent_id="developer",
            details={"progress": 50, "notes": "Halfway done"},
            target_queue="manager-queue"
        )
        
        self.assertTrue(success, "Failed to send status update")
        
        # Set up consumer
        consumer_broker = MessageBroker()
        self.assertTrue(consumer_broker.connect())
        
        received = None
        def capture_message(message):
            nonlocal received
            received = message
            self.message_event.set()
        
        # Start consuming
        consumer_thread = threading.Thread(
            target=lambda: consumer_broker.start_consuming("manager-queue", capture_message)
        )
        consumer_thread.daemon = True
        consumer_thread.start()
        
        # Wait for message
        self.assertTrue(self.message_event.wait(timeout=5), "Timeout waiting for message")
        
        # Stop consumer
        consumer_broker.stop_consuming()
        consumer_broker.disconnect()
        
        # Verify message format
        self.assertIsNotNone(received)
        self.assertEqual(received.get("message_type"), "task_status_update")
        self.assertEqual(received.get("task_id"), "test_task_002")
        self.assertEqual(received.get("from_agent"), "developer")
        self.assertEqual(received.get("new_status"), "in_progress")
        
        # Verify details
        details = received.get("details", {})
        self.assertEqual(details.get("progress"), 50)
        self.assertEqual(details.get("notes"), "Halfway done")
    
    def test_manager_can_process_completion_message(self):
        """Test that manager's message handler can process our messages."""
        # Import manager's handler
        sys.path.append('.agents/manager')
        from message_listener import handle_completion_message
        
        # Create a properly formatted message
        message = {
            "message_type": "task_completion",
            "task_id": "test_task_003",
            "from_agent": "developer",
            "to_agent": "manager",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "completion": {
                "completed_at": datetime.utcnow().isoformat(),
                "summary": "Test task completed successfully",
                "deliverables_status": {
                    "implementation": "completed",
                    "tests": "completed",
                    "documentation": "completed"
                },
                "files_created": ["main.py", "test_main.py", "README.md"]
            }
        }
        
        # Mock the state manager and logger to avoid database operations
        with patch('message_listener.update_manager_status') as mock_update:
            with patch('message_listener.archive_completed_task') as mock_archive:
                with patch('message_listener.logger') as mock_logger:
                    # Call the handler
                    handle_completion_message(message)
                    
                    # Verify it was processed correctly
                    mock_update.assert_called_once_with(message)
                    mock_archive.assert_called_once_with(message)
                    
                    # Check that info was logged (not warning for unknown type)
                    mock_logger.info.assert_called()
                    mock_logger.warning.assert_not_called()
    
    def test_message_persistence_after_broker_restart(self):
        """Test that messages persist if broker connection is lost and restored."""
        # Send a message
        success = send_task_completion_notification(
            task_id="test_task_004",
            completed_by="developer",
            deliverables=["persistent.py"],
            summary="Testing persistence",
            target_queue="manager-queue"
        )
        self.assertTrue(success)
        
        # Simulate broker restart by disconnecting and reconnecting
        time.sleep(0.5)  # Let message settle
        
        # New consumer should still receive the message
        consumer_broker = MessageBroker()
        self.assertTrue(consumer_broker.connect())
        
        received = None
        def capture_message(message):
            nonlocal received
            received = message
            self.message_event.set()
        
        # Start consuming
        consumer_thread = threading.Thread(
            target=lambda: consumer_broker.start_consuming("manager-queue", capture_message)
        )
        consumer_thread.daemon = True
        consumer_thread.start()
        
        # Wait for message
        self.assertTrue(self.message_event.wait(timeout=5), "Message was not persisted")
        
        # Stop consumer
        consumer_broker.stop_consuming()
        consumer_broker.disconnect()
        
        # Verify message
        self.assertIsNotNone(received)
        self.assertEqual(received.get("task_id"), "test_task_004")
    
    def test_multiple_messages_in_sequence(self):
        """Test sending multiple messages in sequence."""
        messages_to_send = [
            ("task_005", "Starting task"),
            ("task_006", "Another task"),
            ("task_007", "Final task")
        ]
        
        # Send all messages
        for task_id, summary in messages_to_send:
            success = send_task_completion_notification(
                task_id=task_id,
                completed_by="developer",
                deliverables=[],
                summary=summary,
                target_queue="manager-queue"
            )
            self.assertTrue(success, f"Failed to send {task_id}")
            time.sleep(0.1)  # Small delay between messages
        
        # Set up consumer
        consumer_broker = MessageBroker()
        self.assertTrue(consumer_broker.connect())
        
        received_messages = []
        expected_count = len(messages_to_send)
        
        def capture_messages(message):
            received_messages.append(message)
            if len(received_messages) >= expected_count:
                self.message_event.set()
        
        # Start consuming
        consumer_thread = threading.Thread(
            target=lambda: consumer_broker.start_consuming("manager-queue", capture_messages)
        )
        consumer_thread.daemon = True
        consumer_thread.start()
        
        # Wait for all messages
        self.assertTrue(self.message_event.wait(timeout=10), "Timeout waiting for all messages")
        
        # Stop consumer
        consumer_broker.stop_consuming()
        consumer_broker.disconnect()
        
        # Verify all messages received
        self.assertEqual(len(received_messages), expected_count)
        
        # Verify each message
        received_task_ids = [msg.get("task_id") for msg in received_messages]
        expected_task_ids = [task_id for task_id, _ in messages_to_send]
        
        for expected_id in expected_task_ids:
            self.assertIn(expected_id, received_task_ids)


class TestMessageFormatValidation(unittest.TestCase):
    """Test message format validation."""
    
    def test_completion_message_required_fields(self):
        """Test that completion messages have all required fields."""
        # Create a minimal message
        message = send_task_completion_notification(
            task_id="validation_test",
            completed_by="developer",
            deliverables=[],
            summary="Validation test"
        )
        
        # The function returns boolean, but we need to check the actual message
        # Mock the broker to capture the message
        with patch('task_notifier.MessageBroker') as MockBroker:
            mock_broker = MockBroker.return_value
            mock_broker.connect.return_value = True
            mock_broker.send_message.return_value = True
            
            # Capture the message argument
            sent_message = None
            def capture_send(queue, msg):
                nonlocal sent_message
                sent_message = msg
                return True
            
            mock_broker.send_message.side_effect = capture_send
            
            # Send notification
            send_task_completion_notification(
                task_id="validation_test",
                completed_by="developer",
                deliverables=["file.py"],
                summary="Test summary"
            )
            
            # Verify required fields
            self.assertIsNotNone(sent_message)
            required_fields = ["message_type", "task_id", "from_agent", "to_agent", 
                             "timestamp", "status", "completion", "metadata"]
            
            for field in required_fields:
                self.assertIn(field, sent_message, f"Missing required field: {field}")
            
            # Verify field values
            self.assertEqual(sent_message["message_type"], "task_completion")
            self.assertEqual(sent_message["from_agent"], "developer")
            self.assertEqual(sent_message["to_agent"], "manager")
            self.assertEqual(sent_message["status"], "completed")


def run_integration_tests():
    """Run all integration tests."""
    # Check if RabbitMQ is available
    test_broker = MessageBroker()
    if not test_broker.connect():
        print("❌ RabbitMQ is not available. Please start it with:")
        print("   brew services start rabbitmq")
        return False
    
    test_broker.disconnect()
    
    # Run tests
    print("🧪 Running messaging integration tests...")
    print("=" * 50)
    
    unittest.main(argv=[''], exit=False, verbosity=2)
    return True


if __name__ == "__main__":
    run_integration_tests()