# Update Message Listeners Command

Update message listener scripts with enhanced acknowledgment and rollback capabilities.

## Purpose
Enhances the message processing in both Developer and Manager agents to:
- Implement manual message acknowledgment
- Support database transaction rollback on failures
- Ensure consistency between database and message queue
- Prevent message loss during processing errors

## Usage
```bash
# Update all message listeners with enhanced capabilities
project:update_message_listeners
```

## Implementation

```bash
#!/bin/bash

echo "🔄 UPDATING MESSAGE LISTENERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create enhanced developer message listener
cat > .agents/developer/message_listener_enhanced.py << 'EOF'
#!/usr/bin/env python3
"""
Developer Agent RabbitMQ Message Listener with Enhanced Database Integration

Implements transactional message processing with manual acknowledgment
and database rollback capabilities.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

try:
    from message_broker import MessageBroker, BrokerConfig
    from state_manager import StateManager
except ImportError as e:
    print(f"ERROR: Required module not found: {e}")
    print("Ensure tools/message_broker.py and tools/state_manager.py exist.")
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

# Initialize StateManager
state_manager = StateManager()

def handle_message(ch, method, properties, body):
    """
    Handle incoming messages with transactional processing.
    
    Args:
        ch: Channel object
        method: Delivery method
        properties: Message properties
        body: Message body
    """
    # Track database changes for potential rollback
    db_changes = {
        'task_created': None,
        'agent_state_updated': False,
        'activities_logged': [],
        'original_agent_state': None
    }
    
    try:
        # Parse message
        message = json.loads(body.decode('utf-8'))
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        # Store original agent state for rollback
        db_changes['original_agent_state'] = state_manager.get_agent_state('developer')
        
        # Process message based on type
        if message_type == 'task_assignment':
            success = handle_task_assignment(message, db_changes)
        elif message_type == 'task_update':
            success = handle_task_update(message, db_changes)
        elif message_type == 'resource_allocation':
            success = handle_resource_allocation(message, db_changes)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            success = False
        
        if success:
            # Acknowledge message only after successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message {task_id} acknowledged")
        else:
            # Rollback database changes on failure
            rollback_changes(db_changes)
            # Reject and requeue message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logger.warning(f"Message {task_id} rejected and requeued")
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")
        # Don't requeue invalid messages
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # Rollback any database changes
        rollback_changes(db_changes)
        # Requeue message for retry
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def rollback_changes(db_changes: Dict[str, Any]):
    """
    Rollback database changes made during message processing.
    
    Args:
        db_changes: Dictionary tracking database modifications
    """
    try:
        # Remove created task if any
        if db_changes['task_created']:
            state_manager.db.tasks.delete_one({'_id': db_changes['task_created']})
            logger.info(f"Rolled back task creation: {db_changes['task_created']}")
        
        # Remove logged activities
        if db_changes['activities_logged']:
            state_manager.db.activity_logs.delete_many({
                '_id': {'$in': db_changes['activities_logged']}
            })
            logger.info(f"Rolled back {len(db_changes['activities_logged'])} activity logs")
        
        # Restore original agent state if updated
        if db_changes['agent_state_updated'] and db_changes['original_agent_state']:
            original = db_changes['original_agent_state']
            state_manager.update_agent_state(
                'developer', 
                original.get('status', 'ready'),
                original.get('metadata', {})
            )
            logger.info("Restored original agent state")
            
    except Exception as e:
        logger.error(f"Error during rollback: {e}")

def handle_task_assignment(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle task assignment messages with transactional database updates.
    
    Args:
        message: Task assignment message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        task_id = message.get('task_id')
        from_agent = message.get('from_agent')
        task = message.get('task', {})
        priority = message.get('priority', 'normal')
        
        # Create task in database if it doesn't exist
        existing_task = state_manager.get_task(task_id)
        if existing_task:
            logger.info(f"Task {task_id} already exists in database")
        else:
            task_data = {
                'task_id': task_id,
                'title': task.get('title', 'Untitled Task'),
                'description': task.get('description', ''),
                'requirements': task.get('requirements', []),
                'assigned_to': 'developer',
                'assigned_by': from_agent,
                'priority': priority,
                'status': 'assigned'
            }
            
            created_task_id = state_manager.create_task(task_data)
            if not created_task_id:
                logger.error(f"Failed to create task {task_id} in database")
                return False
            
            db_changes['task_created'] = created_task_id
            logger.info(f"Task {task_id} created in database")
        
        # Update developer state with current task
        current_tasks = state_manager.get_agent_tasks('developer', ['assigned', 'in_progress'])
        if not state_manager.update_agent_state('developer', 'working', {
            'current_task_id': task_id,
            'current_tasks_count': len(current_tasks) + 1,
            'last_assignment': datetime.utcnow().isoformat()
        }):
            logger.error("Failed to update developer state")
            return False
        
        db_changes['agent_state_updated'] = True
        
        # Log task assignment activity
        activity_id = state_manager.log_activity('developer', 'task_assigned', {
            'task_id': task_id,
            'assigned_by': from_agent,
            'priority': priority,
            'title': task.get('title', '')
        })
        
        if activity_id:
            db_changes['activities_logged'].append(activity_id)
        
        # Archive task assignment
        if not archive_task_assignment(message):
            logger.warning("Failed to archive task assignment")
            # Non-critical, don't fail the transaction
        
        print(f"📋 NEW TASK ASSIGNED: {task_id}")
        print(f"   Assigned by: {from_agent}")
        print(f"   Priority: {priority}")
        print(f"   Title: {task.get('title', 'Untitled')}")
        
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
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_task_assignment: {e}")
        return False

def handle_task_update(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle task update messages with transactional processing.
    
    Args:
        message: Task update message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        task_id = message.get('task_id')
        update_type = message.get('update_type')
        
        # Log task update
        activity_id = state_manager.log_activity('developer', 'task_update_received', {
            'task_id': task_id,
            'update_type': update_type,
            'details': message.get('details', {})
        })
        
        if activity_id:
            db_changes['activities_logged'].append(activity_id)
        
        print(f"📝 TASK UPDATE: {task_id}")
        print(f"   Update type: {update_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_task_update: {e}")
        return False

def handle_resource_allocation(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle resource allocation messages with transactional processing.
    
    Args:
        message: Resource allocation message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        resources = message.get('resources', {})
        
        # Update developer state with allocated resources
        if not state_manager.update_agent_state('developer', metadata={
            'allocated_resources': resources,
            'resources_updated': datetime.utcnow().isoformat()
        }):
            logger.error("Failed to update developer state with resources")
            return False
        
        db_changes['agent_state_updated'] = True
        
        print(f"🔧 RESOURCES ALLOCATED")
        for resource, value in resources.items():
            print(f"   {resource}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_resource_allocation: {e}")
        return False

def archive_task_assignment(task_message: Dict[str, Any]) -> bool:
    """
    Archive the task assignment for record keeping.
    
    Args:
        task_message: Task message to archive
        
    Returns:
        bool: True if archived successfully
    """
    try:
        task_id = task_message.get('task_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create archive filename
        archive_file = f".comms/active/{task_id}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(archive_file), exist_ok=True)
        
        # Save assignment message
        with open(archive_file, 'w') as f:
            json.dump(task_message, f, indent=2)
            
        logger.info(f"Archived task assignment to {archive_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")
        return False

def update_heartbeat():
    """Update developer heartbeat in database."""
    state_manager.update_agent_state('developer', metadata={
        'last_heartbeat': datetime.utcnow().isoformat()
    })

def main():
    """Main developer message listener."""
    print("👨‍💻 DEVELOPER MESSAGE LISTENER STARTING (Enhanced)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if not state_manager.is_connected():
        logger.error("Failed to connect to MongoDB")
        print("❌ Database connection failed")
        return 1
    
    try:
        # Update developer status to listening
        state_manager.update_agent_state('developer', 'listening')
        
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            state_manager.update_agent_state('developer', 'error', {
                'error': 'RabbitMQ connection failed'
            })
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("✅ Connected to MongoDB")
        print("📬 Listening for task assignments...")
        print("⚡ Enhanced with rollback capabilities")
        print("Press Ctrl+C to stop")
        print("")
        
        # Update status to connected
        state_manager.update_agent_state('developer', 'active', {
            'message_broker_status': 'connected',
            'listener_version': 'enhanced'
        })
        
        # Configure message consumption with manual acknowledgment
        broker.channel.basic_qos(prefetch_count=1)  # Process one message at a time
        broker.channel.basic_consume(
            queue=MessageBroker.DEVELOPER_QUEUE,
            on_message_callback=handle_message,
            auto_ack=False  # Manual acknowledgment for transaction support
        )
        
        # Start consuming
        broker.channel.start_consuming()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping developer message listener...")
        logger.info("Developer message listener stopped by user")
        
    except Exception as e:
        logger.error(f"Developer listener error: {e}")
        state_manager.update_agent_state('developer', 'error', {
            'error': str(e)
        })
        return 1
    finally:
        try:
            broker.disconnect()
            state_manager.update_agent_state('developer', 'stopped')
            state_manager.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
EOF

# Create enhanced manager message listener
cat > .agents/manager/message_listener_enhanced.py << 'EOF'
#!/usr/bin/env python3
"""
Manager Agent RabbitMQ Message Listener with Enhanced Database Integration

Implements transactional message processing with manual acknowledgment
and database rollback capabilities.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

try:
    from message_broker import MessageBroker, BrokerConfig
    from state_manager import StateManager
except ImportError as e:
    print(f"ERROR: Required module not found: {e}")
    print("Ensure tools/message_broker.py and tools/state_manager.py exist.")
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

# Initialize StateManager
state_manager = StateManager()

def handle_message(ch, method, properties, body):
    """
    Handle incoming messages with transactional processing.
    
    Args:
        ch: Channel object
        method: Delivery method
        properties: Message properties
        body: Message body
    """
    # Track database changes for potential rollback
    db_changes = {
        'task_updated': False,
        'activities_logged': [],
        'work_request_created': None,
        'original_task_state': None
    }
    
    try:
        # Parse message
        message = json.loads(body.decode('utf-8'))
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        # Process message based on type
        if message_type == 'task_completion':
            success = handle_task_completion(message, db_changes)
        elif message_type == 'work_request':
            success = handle_work_request(message, db_changes)
        elif message_type == 'status_update':
            success = handle_status_update(message, db_changes)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            success = False
        
        if success:
            # Acknowledge message only after successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Message {task_id} acknowledged")
        else:
            # Rollback database changes on failure
            rollback_changes(db_changes)
            # Reject and requeue message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logger.warning(f"Message {task_id} rejected and requeued")
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")
        # Don't requeue invalid messages
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # Rollback any database changes
        rollback_changes(db_changes)
        # Requeue message for retry
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def rollback_changes(db_changes: Dict[str, Any]):
    """
    Rollback database changes made during message processing.
    
    Args:
        db_changes: Dictionary tracking database modifications
    """
    try:
        # Restore original task state if updated
        if db_changes['task_updated'] and db_changes['original_task_state']:
            original = db_changes['original_task_state']
            state_manager.update_task_state(
                original['task_id'],
                original['status'],
                original.get('metadata', {})
            )
            logger.info(f"Restored original task state for {original['task_id']}")
        
        # Remove created work request if any
        if db_changes['work_request_created']:
            state_manager.db.work_requests.delete_one({'_id': db_changes['work_request_created']})
            logger.info(f"Rolled back work request creation: {db_changes['work_request_created']}")
        
        # Remove logged activities
        if db_changes['activities_logged']:
            state_manager.db.activity_logs.delete_many({
                '_id': {'$in': db_changes['activities_logged']}
            })
            logger.info(f"Rolled back {len(db_changes['activities_logged'])} activity logs")
            
    except Exception as e:
        logger.error(f"Error during rollback: {e}")

def handle_task_completion(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle task completion messages with transactional processing.
    
    Args:
        message: Task completion message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        task_id = message.get('task_id')
        from_agent = message.get('from_agent')
        completion_time = message.get('timestamp', datetime.utcnow().isoformat())
        
        # Store original task state for rollback
        original_task = state_manager.get_task(task_id)
        if original_task:
            db_changes['original_task_state'] = {
                'task_id': task_id,
                'status': original_task['status'],
                'metadata': original_task.get('metadata', {})
            }
        
        # Update task status in database
        if not state_manager.update_task_state(task_id, 'completed', {
            'completed_by': from_agent,
            'completed_at': completion_time,
            'completion_summary': message.get('completion', {}).get('summary', ''),
            'manager_acknowledged': True
        }):
            logger.error(f"Failed to update task {task_id} status")
            return False
        
        db_changes['task_updated'] = True
        
        # Log completion activity
        activity_id = state_manager.log_activity('manager', 'task_completed', {
            'task_id': task_id,
            'completed_by': from_agent,
            'summary': message.get('completion', {}).get('summary', '')
        })
        
        if activity_id:
            db_changes['activities_logged'].append(activity_id)
        
        # Update manager heartbeat
        state_manager.update_agent_state('manager', metadata={
            'last_task_completion': completion_time,
            'last_heartbeat': datetime.utcnow().isoformat()
        })
        
        # Archive completed task
        if not archive_completed_task(message):
            logger.warning("Failed to archive task completion")
            # Non-critical, don't fail the transaction
        
        print(f"✅ TASK COMPLETED: {task_id}")
        print(f"   Completed by: {from_agent}")
        print(f"   Summary: {message.get('completion', {}).get('summary', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_task_completion: {e}")
        return False

def handle_work_request(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle work request messages with transactional processing.
    
    Args:
        message: Work request message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        request_id = message.get('request_id')
        from_agent = message.get('from_agent')
        
        # Create work request in database
        req_id = state_manager.create_work_request(
            from_agent, 
            'manager',
            {
                'request_id': request_id,
                'type': message.get('request_type', 'general'),
                'details': message.get('details', {}),
                'priority': message.get('priority', 'normal')
            }
        )
        
        if not req_id:
            logger.error("Failed to create work request")
            return False
        
        db_changes['work_request_created'] = req_id
        
        # Log activity
        activity_id = state_manager.log_activity('manager', 'work_request_received', {
            'request_id': req_id,
            'from_agent': from_agent,
            'type': message.get('request_type', 'general')
        })
        
        if activity_id:
            db_changes['activities_logged'].append(activity_id)
        
        print(f"📨 NEW WORK REQUEST: {req_id}")
        print(f"   From: {from_agent}")
        print(f"   Type: {message.get('request_type', 'general')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_work_request: {e}")
        return False

def handle_status_update(message: Dict[str, Any], db_changes: Dict[str, Any]) -> bool:
    """
    Handle agent status update messages with transactional processing.
    
    Args:
        message: Status update message
        db_changes: Dictionary to track database changes
        
    Returns:
        bool: True if handled successfully
    """
    try:
        from_agent = message.get('from_agent')
        status = message.get('status')
        
        # Log status update
        activity_id = state_manager.log_activity(from_agent, 'status_update', {
            'new_status': status,
            'metadata': message.get('metadata', {})
        })
        
        if activity_id:
            db_changes['activities_logged'].append(activity_id)
        
        print(f"📊 STATUS UPDATE from {from_agent}: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_status_update: {e}")
        return False

def archive_completed_task(completion_message: Dict[str, Any]) -> bool:
    """
    Archive the completed task for record keeping.
    
    Args:
        completion_message: Completion message to archive
        
    Returns:
        bool: True if archived successfully
    """
    try:
        task_id = completion_message.get('task_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create archive filename
        archive_file = f".comms/completed/{task_id}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(archive_file), exist_ok=True)
        
        # Save completion message
        with open(archive_file, 'w') as f:
            json.dump(completion_message, f, indent=2)
            
        logger.info(f"Archived completion message to {archive_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")
        return False

def update_heartbeat():
    """Update manager heartbeat in database."""
    state_manager.update_agent_state('manager', metadata={
        'last_heartbeat': datetime.utcnow().isoformat()
    })

def main():
    """Main manager message listener."""
    print("🤖 MANAGER MESSAGE LISTENER STARTING (Enhanced)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if not state_manager.is_connected():
        logger.error("Failed to connect to MongoDB")
        print("❌ Database connection failed")
        return 1
    
    try:
        # Update manager status to listening
        state_manager.update_agent_state('manager', 'listening')
        
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            state_manager.update_agent_state('manager', 'error', {
                'error': 'RabbitMQ connection failed'
            })
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("✅ Connected to MongoDB")
        print("📬 Listening for messages...")
        print("⚡ Enhanced with rollback capabilities")
        print("Press Ctrl+C to stop")
        print("")
        
        # Update status to connected
        state_manager.update_agent_state('manager', 'active', {
            'message_broker_status': 'connected',
            'listener_version': 'enhanced'
        })
        
        # Configure message consumption with manual acknowledgment
        broker.channel.basic_qos(prefetch_count=1)  # Process one message at a time
        broker.channel.basic_consume(
            queue=MessageBroker.MANAGER_QUEUE,
            on_message_callback=handle_message,
            auto_ack=False  # Manual acknowledgment for transaction support
        )
        
        # Start consuming
        broker.channel.start_consuming()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping manager message listener...")
        logger.info("Manager message listener stopped by user")
        
    except Exception as e:
        logger.error(f"Manager listener error: {e}")
        state_manager.update_agent_state('manager', 'error', {
            'error': str(e)
        })
        return 1
    finally:
        try:
            broker.disconnect()
            state_manager.update_agent_state('manager', 'stopped')
            state_manager.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
EOF

# Make enhanced scripts executable
chmod +x .agents/developer/message_listener_enhanced.py
chmod +x .agents/manager/message_listener_enhanced.py

echo "✅ Enhanced message listeners created"
echo ""
echo "📁 FILES CREATED:"
echo "  • .agents/developer/message_listener_enhanced.py"
echo "  • .agents/manager/message_listener_enhanced.py"
echo ""
echo "🔄 ENHANCEMENTS IMPLEMENTED:"
echo "  ✅ Manual message acknowledgment"
echo "  ✅ Database transaction rollback on failures"
echo "  ✅ Original state preservation"
echo "  ✅ Activity log cleanup on rollback"
echo "  ✅ Task state restoration"
echo "  ✅ Work request rollback support"
echo ""
echo "🚀 TO USE ENHANCED LISTENERS:"
echo "  Developer: python3 .agents/developer/message_listener_enhanced.py"
echo "  Manager: python3 .agents/manager/message_listener_enhanced.py"
echo ""
echo "💡 BENEFITS:"
echo "  • Messages acknowledged only after successful DB updates"
echo "  • Failed messages automatically requeued"
echo "  • Database consistency maintained on errors"
echo "  • No data loss during processing failures"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Features

### Enhanced Message Processing
- Manual acknowledgment after successful database updates
- Automatic message requeue on processing failures
- Invalid message rejection without requeue
- Single message processing (prefetch_count=1)

### Database Transaction Support
- Track all database changes during message processing
- Store original states for rollback
- Rollback task updates, activity logs, and work requests
- Restore agent and task states on failure

### Rollback Capabilities
1. **Task Creation Rollback** - Remove created tasks
2. **Activity Log Rollback** - Delete logged activities
3. **State Restoration** - Restore original agent/task states
4. **Work Request Rollback** - Remove created work requests

### Error Handling
- JSON decode errors reject without requeue
- Processing errors trigger rollback and requeue
- Database errors prevent acknowledgment
- Comprehensive error logging

## Usage Examples

Start enhanced listeners:
```bash
# Developer agent with enhanced listener
python3 .agents/developer/message_listener_enhanced.py

# Manager agent with enhanced listener
python3 .agents/manager/message_listener_enhanced.py
```

The enhanced listeners will:
1. Process messages one at a time
2. Update database with full transaction tracking
3. Acknowledge only on success
4. Rollback and requeue on any failure
5. Maintain complete consistency

## Testing Rollback

To test rollback capabilities:
1. Temporarily break database connection during processing
2. Send malformed messages
3. Simulate processing errors
4. Check that messages are requeued and database remains consistent