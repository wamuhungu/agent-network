#!/usr/bin/env python3
"""
Integrated task completion script that handles both database updates and notifications.
"""

import sys
import argparse
from datetime import datetime

# Add tools directory to path
sys.path.append('tools')

from state_manager import StateManager
from task_notifier import send_task_completion_notification


def complete_task(task_id, deliverables, summary):
    """Complete a task with integrated database update and notification."""
    
    sm = StateManager()
    
    try:
        if not sm.is_connected():
            print("❌ Failed to connect to database")
            return False
            
        # Get task details
        task = sm.get_task_by_id(task_id)
        if not task:
            print(f"❌ Task {task_id} not found")
            return False
            
        # Check if already completed
        if task.get('status') == 'completed':
            print(f"⚠️  Task {task_id} is already completed")
            return True
            
        # Update task state
        completion_metadata = {
            'completed_by': 'developer',
            'completion_time': datetime.utcnow().isoformat(),
            'deliverables': deliverables,
            'summary': summary
        }
        
        success = sm.update_task_state(task_id, 'completed', completion_metadata)
        
        if not success:
            print(f"❌ Failed to update task {task_id} in database")
            return False
            
        print(f"✅ Task {task_id} marked as completed in database")
        
        # Update developer state
        sm.update_agent_state('developer', 'ready', {
            'last_completed_task': task_id,
            'completion_time': datetime.utcnow().isoformat()
        })
        
        # Log activity
        sm.log_activity('developer', 'task_completed', {
            'task_id': task_id,
            'deliverables': deliverables,
            'summary': summary
        })
        
        # Send notification
        notify_success = send_task_completion_notification(
            task_id=task_id,
            completed_by='developer',
            deliverables=deliverables,
            summary=summary,
            target_queue='manager-queue'
        )
        
        if not notify_success:
            print("⚠️  Task completed but notification to manager failed")
            print("💡 Manager can still see the completion in the database")
        else:
            print("✅ Manager has been notified via RabbitMQ")
            
        return True
        
    except Exception as e:
        print(f"❌ Error completing task: {e}")
        return False
        
    finally:
        sm.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complete a task with notifications")
    parser.add_argument("task_id", help="Task ID to complete")
    parser.add_argument("--deliverables", nargs="+", default=[], 
                       help="List of deliverables")
    parser.add_argument("--summary", default="Task completed successfully",
                       help="Completion summary")
    
    args = parser.parse_args()
    
    success = complete_task(args.task_id, args.deliverables, args.summary)
    sys.exit(0 if success else 1)