#!/usr/bin/env python3
"""
Manager Agent RabbitMQ Message Listener

Listens for task completion messages on the manager-queue and processes them.
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
        logging.FileHandler('.logs/manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def handle_completion_message(message):
    """
    Handle incoming task completion messages.
    
    Args:
        message: Parsed JSON message from developer
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type == 'task_completion':
            # Process task completion
            completion_time = message.get('timestamp', datetime.now().isoformat())
            
            # Update manager status
            update_manager_status(message)
            
            # Archive completed task
            archive_completed_task(message)
            
            # Log completion
            logger.info(f"Task {task_id} completed successfully by {from_agent}")
            
            print(f"✅ TASK COMPLETED: {task_id}")
            print(f"   Completed by: {from_agent}")
            print(f"   Completed at: {completion_time}")
            
            # Display completion summary
            completion = message.get('completion', {})
            summary = completion.get('summary', 'No summary provided')
            print(f"   Summary: {summary}")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def update_manager_status(completion_message):
    """Update manager status with completed task information."""
    try:
        # Use StateManager to update status in MongoDB
        sm = StateManager()
        
        task_id = completion_message.get('task_id')
        
        # Update task status to completed
        sm.update_task_state(task_id, 'completed')
        
        # Log activity
        sm.log_activity('manager', 'task_completed', {
            'task_id': task_id,
            'completed_by': completion_message.get('from_agent'),
            'completed_at': completion_message.get('timestamp'),
            'summary': completion_message.get('completion', {}).get('summary', '')
        })
        
        # Update manager state
        sm.update_agent_state('manager', 'active', {
            'last_activity': datetime.now().isoformat(),
            'last_completed_task': task_id,
            'message_broker_status': 'connected'
        })
        
        sm.disconnect()
            
    except Exception as e:
        logger.error(f"Error updating manager status: {e}")

def archive_completed_task(completion_message):
    """Archive the completed task in MongoDB."""
    try:
        task_id = completion_message.get('task_id', 'unknown')
        
        # Use StateManager to archive in MongoDB
        sm = StateManager()
        
        # The completion details are already stored when we update task status
        # Just log this as an activity
        sm.log_activity('manager', 'task_archived', {
            'task_id': task_id,
            'archived_at': datetime.now().isoformat(),
            'completion_details': completion_message
        })
        
        logger.info(f"Archived completion message for task {task_id} in MongoDB")
        
        sm.disconnect()
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")

def main():
    """Main manager message listener."""
    print("🤖 MANAGER MESSAGE LISTENER STARTING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("📬 Listening for task completion messages...")
        print("Press Ctrl+C to stop")
        print("")
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.MANAGER_QUEUE, handle_completion_message)
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping manager message listener...")
            logger.info("Manager message listener stopped by user")
            
    except Exception as e:
        logger.error(f"Manager listener error: {e}")
        return 1
    finally:
        try:
            broker.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
