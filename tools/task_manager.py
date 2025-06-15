#!/usr/bin/env python3
"""
Enhanced task manager that integrates database operations with message broker notifications.

This module provides a unified interface for task management that ensures
both database updates and message broker notifications are handled together.
"""

import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.append('..')
from state_manager import StateManager
from message_broker import MessageBroker
from task_notifier import send_task_completion_notification, send_task_status_update


class TaskManager:
    """Unified task management with database and messaging."""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.message_broker = MessageBroker()
        
    def __enter__(self):
        """Context manager entry."""
        self.message_broker.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.state_manager.disconnect()
        self.message_broker.disconnect()
    
    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        deliverables: List[str],
        summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Complete a task with database update and notification.
        
        Args:
            task_id: Task to complete
            agent_id: Agent completing the task
            deliverables: List of deliverables
            summary: Summary of work done
            metadata: Additional metadata
            
        Returns:
            bool: True if both database update and notification succeeded
        """
        # Prepare metadata
        completion_metadata = {
            'completed_by': agent_id,
            'completion_time': datetime.utcnow().isoformat(),
            'deliverables': deliverables,
            'summary': summary
        }
        
        if metadata:
            completion_metadata.update(metadata)
        
        # Update database
        db_success = self.state_manager.update_task_state(
            task_id, 'completed', completion_metadata
        )
        
        if not db_success:
            print(f"❌ Failed to update task {task_id} in database")
            return False
            
        print(f"✅ Task {task_id} marked as completed in database")
        
        # Send notification
        notify_success = send_task_completion_notification(
            task_id=task_id,
            completed_by=agent_id,
            deliverables=deliverables,
            summary=summary,
            target_queue='manager-queue'
        )
        
        if not notify_success:
            print(f"⚠️  Task completed but notification failed")
            # Still return True since task was completed in DB
            
        # Update agent state
        self.state_manager.update_agent_state(agent_id, 'ready', {
            'last_completed_task': task_id,
            'completion_time': datetime.utcnow().isoformat()
        })
        
        # Log activity
        self.state_manager.log_activity(agent_id, 'task_completed', {
            'task_id': task_id,
            'deliverables': deliverables,
            'summary': summary,
            'notification_sent': notify_success
        })
        
        return db_success
    
    def update_task_progress(
        self,
        task_id: str,
        agent_id: str,
        progress: int,
        status: str = 'in_progress',
        notes: Optional[str] = None
    ) -> bool:
        """
        Update task progress with notification.
        
        Args:
            task_id: Task to update
            agent_id: Agent making the update
            progress: Progress percentage (0-100)
            status: Current status
            notes: Optional progress notes
            
        Returns:
            bool: True if update successful
        """
        # Update database
        metadata = {
            'progress': progress,
            'last_updated_by': agent_id,
            'update_time': datetime.utcnow().isoformat()
        }
        
        if notes:
            metadata['notes'] = notes
            
        db_success = self.state_manager.update_task_state(
            task_id, status, metadata
        )
        
        if not db_success:
            return False
            
        # Send notification for significant updates
        if progress % 25 == 0 or status != 'in_progress':
            send_task_status_update(
                task_id=task_id,
                new_status=status,
                agent_id=agent_id,
                details={'progress': progress, 'notes': notes}
            )
            
        return True
    
    def pickup_task(self, task_id: str, agent_id: str) -> bool:
        """
        Assign a task to an agent with notification.
        
        Args:
            task_id: Task to assign
            agent_id: Agent to assign to
            
        Returns:
            bool: True if assignment successful
        """
        # Assign in database
        db_success = self.state_manager.assign_task_to_agent(task_id, agent_id)
        
        if not db_success:
            return False
            
        # Update agent state
        self.state_manager.update_agent_state(agent_id, 'working', {
            'current_task_id': task_id,
            'task_started': datetime.utcnow().isoformat()
        })
        
        # Send notification
        send_task_status_update(
            task_id=task_id,
            new_status='assigned',
            agent_id=agent_id,
            details={'assigned_to': agent_id}
        )
        
        return True


def complete_task_with_notification(
    task_id: str,
    agent_id: str,
    deliverables: List[str],
    summary: str
) -> bool:
    """
    Convenience function to complete a task with full integration.
    
    Args:
        task_id: Task to complete
        agent_id: Agent completing the task
        deliverables: List of deliverables
        summary: Summary of work done
        
    Returns:
        bool: True if successful
    """
    with TaskManager() as tm:
        return tm.complete_task(task_id, agent_id, deliverables, summary)


if __name__ == "__main__":
    # Test the task manager
    import argparse
    
    parser = argparse.ArgumentParser(description="Task management operations")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--agent", required=True, help="Agent ID")
    parser.add_argument("--action", choices=["complete", "update", "pickup"],
                       required=True, help="Action to perform")
    parser.add_argument("--summary", help="Summary (for completions)")
    parser.add_argument("--progress", type=int, help="Progress percentage")
    parser.add_argument("--notes", help="Progress notes")
    
    args = parser.parse_args()
    
    with TaskManager() as tm:
        if args.action == "complete":
            success = tm.complete_task(
                task_id=args.task_id,
                agent_id=args.agent,
                deliverables=[],
                summary=args.summary or "Task completed"
            )
        elif args.action == "update":
            success = tm.update_task_progress(
                task_id=args.task_id,
                agent_id=args.agent,
                progress=args.progress or 50,
                notes=args.notes
            )
        else:  # pickup
            success = tm.pickup_task(args.task_id, args.agent)
            
    sys.exit(0 if success else 1)