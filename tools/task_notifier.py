#!/usr/bin/env python3
"""
Task notification helper for sending RabbitMQ messages when tasks are completed.

This module provides functions to notify agents about task state changes
through the message broker.
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append('..')
from message_broker import MessageBroker


def send_task_completion_notification(
    task_id: str,
    completed_by: str,
    deliverables: list,
    summary: str,
    target_queue: str = 'manager-queue'
) -> bool:
    """
    Send a task completion notification to the specified queue.
    
    Args:
        task_id: The completed task ID
        completed_by: Agent who completed the task
        deliverables: List of deliverables created
        summary: Summary of what was done
        target_queue: Queue to send notification to (default: manager-queue)
        
    Returns:
        bool: True if notification sent successfully
    """
    broker = MessageBroker()
    
    try:
        if not broker.connect():
            print("Failed to connect to message broker")
            return False
        
        # Create completion message matching manager's expected format
        message = {
            "message_type": "task_completion",  # Changed from "type" to "message_type" and "task_completed" to "task_completion"
            "task_id": task_id,
            "from_agent": completed_by,  # Changed from "completed_by" to "from_agent"
            "to_agent": "manager",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "completion": {
                "completed_at": datetime.utcnow().isoformat(),
                "summary": summary,
                "deliverables_status": {
                    "implementation": "completed",
                    "tests": "completed",
                    "documentation": "completed",
                    "code_review": "ready"
                },
                "notes": f"Task completed with {len(deliverables)} deliverables",
                "files_created": deliverables,
                "duration": "N/A"
            },
            "metadata": {
                "completed_by": completed_by,
                "deliverables": deliverables,
                "notification_sent": datetime.utcnow().isoformat(),
                "source": "task_notifier"
            }
        }
        
        # Send the message
        success = broker.send_message(target_queue, message)
        
        if success:
            print(f"✅ Task completion notification sent to {target_queue}")
            print(f"   Task ID: {task_id}")
            print(f"   Completed by: {completed_by}")
        else:
            print(f"❌ Failed to send notification to {target_queue}")
            
        return success
        
    except Exception as e:
        print(f"Error sending task notification: {e}")
        return False
        
    finally:
        broker.disconnect()


def send_task_status_update(
    task_id: str,
    new_status: str,
    agent_id: str,
    details: Optional[Dict[str, Any]] = None,
    target_queue: str = 'manager-queue'
) -> bool:
    """
    Send a task status update notification.
    
    Args:
        task_id: The task ID
        new_status: New status (e.g., 'in_progress', 'blocked', 'completed')
        agent_id: Agent making the update
        details: Additional details about the status change
        target_queue: Queue to send notification to
        
    Returns:
        bool: True if notification sent successfully
    """
    broker = MessageBroker()
    
    try:
        if not broker.connect():
            print("Failed to connect to message broker")
            return False
        
        # Create status update message matching expected format
        message = {
            "message_type": "task_status_update",  # Changed from "type" to "message_type"
            "task_id": task_id,
            "from_agent": agent_id,  # Changed from "updated_by" to "from_agent"
            "to_agent": "manager",
            "timestamp": datetime.utcnow().isoformat(),
            "new_status": new_status,
            "details": details or {},
            "metadata": {
                "updated_by": agent_id,
                "update_time": datetime.utcnow().isoformat(),
                "notification_sent": datetime.utcnow().isoformat(),
                "source": "task_notifier"
            }
        }
        
        # Send the message
        success = broker.send_message(target_queue, message)
        
        if success:
            print(f"✅ Task status update sent to {target_queue}")
            print(f"   Task ID: {task_id}")
            print(f"   New status: {new_status}")
        else:
            print(f"❌ Failed to send status update to {target_queue}")
            
        return success
        
    except Exception as e:
        print(f"Error sending status update: {e}")
        return False
        
    finally:
        broker.disconnect()


if __name__ == "__main__":
    # Test the notifier
    import argparse
    
    parser = argparse.ArgumentParser(description="Send task notifications")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--type", choices=["completed", "status"], default="completed",
                       help="Notification type")
    parser.add_argument("--agent", required=True, help="Agent ID")
    parser.add_argument("--status", help="New status (for status updates)")
    parser.add_argument("--summary", help="Summary (for completions)")
    parser.add_argument("--queue", default="manager-queue", help="Target queue")
    
    args = parser.parse_args()
    
    if args.type == "completed":
        success = send_task_completion_notification(
            task_id=args.task_id,
            completed_by=args.agent,
            deliverables=[],
            summary=args.summary or "Task completed",
            target_queue=args.queue
        )
    else:
        success = send_task_status_update(
            task_id=args.task_id,
            new_status=args.status or "in_progress",
            agent_id=args.agent,
            target_queue=args.queue
        )
    
    sys.exit(0 if success else 1)