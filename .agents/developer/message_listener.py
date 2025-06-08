#!/usr/bin/env python3
"""
Developer Agent RabbitMQ Message Listener

Listens for task assignment messages on the developer-queue and processes them.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

try:
    from message_broker import MessageBroker, BrokerConfig
    from state_manager import StateManager
except ImportError as e:
    print(f"ERROR: Required module not found: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.logs/developer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def handle_task_assignment(message):
    """
    Handle incoming task assignment messages.
    
    Args:
        message: Parsed JSON message from manager
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type in ['task_assignment', 'task_notification']:
            # Process task assignment/notification
            if message_type == 'task_notification':
                # For notifications, fetch task details from MongoDB
                sm = StateManager()
                task_data = sm.get_task(task_id)
                sm.disconnect()
                
                if task_data:
                    task = task_data
                    priority = task_data.get('priority', 'medium')
                else:
                    logger.error(f"Task {task_id} not found in database")
                    return
            else:
                # For direct assignments, use message content
                task = message.get('task', {})
                priority = message.get('priority', 'medium')
            
            # Update developer status
            update_developer_status(message)
            
            # Archive task assignment
            archive_task_assignment(message)
            
            # Log assignment
            logger.info(f"Task {task_id} assigned by {from_agent}")
            
            print(f"📋 NEW TASK ASSIGNED: {task_id}")
            print(f"   Assigned by: {from_agent}")
            print(f"   Priority: {priority}")
            
            # Display task details
            description = task.get('description', 'No description provided')
            print(f"   Description: {description}")
            
            # Show requirements if available
            requirements = task.get('requirements', [])
            if requirements:
                print(f"   Requirements ({len(requirements)}):")
                for i, req in enumerate(requirements[:3], 1):
                    print(f"     {i}. {req}")
                if len(requirements) > 3:
                    print(f"     ... and {len(requirements) - 3} more")
            
            print("   📋 Use project:developer_work to begin implementation")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def update_developer_status(task_message):
    """Update developer status with new task assignment."""
    try:
        # Use StateManager to update status in MongoDB
        sm = StateManager()
        
        task_id = task_message.get('task_id')
        
        # Update task status to in_progress
        sm.update_task_status(task_id, 'in_progress')
        
        # Log activity
        sm.log_activity('developer', 'task_received', {
            'task_id': task_id,
            'assigned_by': task_message.get('from_agent'),
            'assigned_at': task_message.get('timestamp'),
            'priority': task_message.get('priority', 'medium'),
            'description': task_message.get('task', {}).get('description', '')
        })
        
        # Update developer state
        sm.update_agent_state('developer', 'working', {
            'last_activity': datetime.now().isoformat(),
            'current_task': task_id,
            'message_broker_status': 'connected'
        })
        
        sm.disconnect()
            
    except Exception as e:
        logger.error(f"Error updating developer status: {e}")

def archive_task_assignment(task_message):
    """Archive the task assignment in MongoDB."""
    try:
        task_id = task_message.get('task_id', 'unknown')
        
        # Use StateManager to archive in MongoDB
        sm = StateManager()
        
        # The assignment details are already stored when we update task status
        # Just log this as an activity
        sm.log_activity('developer', 'task_assignment_archived', {
            'task_id': task_id,
            'archived_at': datetime.now().isoformat(),
            'assignment_details': task_message
        })
        
        logger.info(f"Archived task assignment for {task_id} in MongoDB")
        
        sm.disconnect()
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")

def main():
    """Main developer message listener."""
    print("👨‍💻 DEVELOPER MESSAGE LISTENER STARTING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("📬 Listening for task assignment messages...")
        print("Press Ctrl+C to stop")
        print("")
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.DEVELOPER_QUEUE, handle_task_assignment)
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping developer message listener...")
            logger.info("Developer message listener stopped by user")
            
    except Exception as e:
        logger.error(f"Developer listener error: {e}")
        return 1
    finally:
        try:
            broker.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
