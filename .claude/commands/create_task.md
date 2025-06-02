# Create Task Command

Create a new task assignment for the developer agent with full database integration.

## Purpose
Creates a task in the database with proper state tracking, then sends it via RabbitMQ for assignment. Ensures database and message queue stay synchronized.

## Usage
```bash
# Create a new task (replace TASK_DESCRIPTION with actual task)
project:create_task "TASK_DESCRIPTION"
```

## Implementation

```bash
#!/bin/bash

# Validate input
if [ -z "$1" ]; then
    echo "❌ Error: Task description is required"
    echo "Usage: project:create_task \"TASK_DESCRIPTION\""
    exit 1
fi

TASK_DESCRIPTION="$1"

# Generate unique task ID with timestamp
TASK_ID="task_$(date +%Y%m%d_%H%M%S)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 6)"
TIMESTAMP=$(date -Iseconds)

echo "📋 CREATING TASK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID: $TASK_ID"
echo "Description: $TASK_DESCRIPTION"
echo ""

# Create task in database with full integration
TASK_RESULT=$(python3 -c "
import sys
import json
from datetime import datetime

# Add tools directory to Python path
sys.path.append('tools')

try:
    from state_manager import StateManager
    from message_broker import send_task_to_developer
    
    # Initialize database connection
    sm = StateManager()
    if not sm.is_connected():
        print('ERROR:Database connection failed')
        sys.exit(1)
    
    # Create task in database with 'created' status
    task_data = {
        'task_id': '$TASK_ID',
        'title': '$TASK_DESCRIPTION',
        'description': '$TASK_DESCRIPTION',
        'status': 'created',
        'priority': 'normal',
        'created_by': 'manager',
        'assigned_to': None,  # Not assigned yet
        'requirements': [
            'Implement the requested functionality',
            'Write comprehensive tests',
            'Create or update documentation',
            'Follow coding standards in docs/standards/',
            'Ensure code quality and maintainability'
        ],
        'deliverables': [
            'Working implementation',
            'Test coverage',
            'Documentation updates',
            'Code review ready'
        ],
        'metadata': {
            'estimated_effort': 'TBD',
            'dependencies': [],
            'tags': []
        }
    }
    
    # Create task in database
    created_task_id = sm.create_task(task_data)
    if not created_task_id:
        print('ERROR:Failed to create task in database')
        sm.disconnect()
        sys.exit(1)
    
    # Log task creation activity
    sm.log_activity('manager', 'task_created', {
        'task_id': '$TASK_ID',
        'title': '$TASK_DESCRIPTION',
        'initial_status': 'created'
    })
    
    print(f'CREATED:{created_task_id}')
    
    # Now send to RabbitMQ
    task_message = {
        'message_type': 'task_assignment',
        'task_id': '$TASK_ID',
        'from_agent': 'manager',
        'to_agent': 'developer',
        'timestamp': '$TIMESTAMP',
        'priority': 'normal',
        'status': 'assigned',
        'task': {
            'title': '$TASK_DESCRIPTION',
            'description': '$TASK_DESCRIPTION',
            'requirements': task_data['requirements'],
            'deliverables': task_data['deliverables'],
            'context': {
                'project_root': '.',
                'coding_standards': 'docs/standards/coding_standards.md',
                'test_directory': 'tests/',
                'documentation_directory': 'docs/'
            }
        },
        'metadata': task_data['metadata']
    }
    
    # Send message to developer queue
    try:
        success = send_task_to_developer(task_message)
        
        if success:
            # Update task status to 'assigned' after successful send
            sm.update_task_state('$TASK_ID', 'assigned', {
                'assigned_at': datetime.utcnow().isoformat(),
                'assigned_to': 'developer',
                'queue_status': 'sent'
            })
            
            # Update manager state
            sm.update_agent_state('manager', metadata={
                'last_task_assigned': '$TASK_ID',
                'last_assignment_time': datetime.utcnow().isoformat()
            })
            
            # Log assignment activity
            sm.log_activity('manager', 'task_assigned', {
                'task_id': '$TASK_ID',
                'assigned_to': 'developer',
                'method': 'rabbitmq'
            })
            
            print('SENT:Success')
            
        else:
            # Rollback - mark task as failed to send
            sm.update_task_state('$TASK_ID', 'created', {
                'send_failed': True,
                'error': 'Failed to send to RabbitMQ'
            })
            
            sm.log_activity('manager', 'task_send_failed', {
                'task_id': '$TASK_ID',
                'error': 'RabbitMQ send failed'
            })
            
            print('ERROR:Failed to send task to RabbitMQ')
            
    except Exception as e:
        # Rollback on any error
        sm.update_task_state('$TASK_ID', 'created', {
            'send_failed': True,
            'error': str(e)
        })
        
        sm.log_activity('manager', 'task_send_error', {
            'task_id': '$TASK_ID',
            'error': str(e)
        })
        
        print(f'ERROR:Exception sending task: {e}')
    
    finally:
        sm.disconnect()
        
except ImportError as e:
    print(f'ERROR:Required module not available: {e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:Unexpected error: {e}')
    sys.exit(1)
")

# Parse the result
if [[ "$TASK_RESULT" == "CREATED:"* ]]; then
    CREATED_ID=$(echo "$TASK_RESULT" | grep "^CREATED:" | cut -d':' -f2)
    SEND_STATUS=$(echo "$TASK_RESULT" | grep "^SENT:" | cut -d':' -f2)
    
    if [ "$SEND_STATUS" = "Success" ]; then
        echo "✅ Task created in database: $CREATED_ID"
        echo "✅ Task sent to developer queue"
        echo ""
        echo "📊 TASK STATUS:"
        echo "  • Database: Created → Assigned"
        echo "  • Queue: Sent to developer-queue"
        echo "  • Developer: Will be notified immediately"
        
        # Log to file
        echo "$(date -Iseconds) [TASK_CREATE] Task created: $TASK_ID - $TASK_DESCRIPTION" >> .logs/manager.log
        echo "$(date -Iseconds) [TASK_SEND] Task $TASK_ID sent to developer-queue successfully" >> .logs/manager.log
        
    else
        echo "✅ Task created in database: $CREATED_ID"
        echo "❌ Failed to send task to developer queue"
        echo ""
        echo "⚠️  TASK STATUS:"
        echo "  • Database: Created (not assigned)"
        echo "  • Queue: Failed to send"
        echo ""
        echo "💡 TROUBLESHOOTING:"
        echo "  • Check if RabbitMQ is running: brew services list | grep rabbitmq"
        echo "  • Start RabbitMQ: project:start_message_broker"
        echo "  • Task remains in database and can be sent later"
        exit 1
    fi
    
elif [[ "$TASK_RESULT" == "ERROR:"* ]]; then
    ERROR_MSG=$(echo "$TASK_RESULT" | grep "^ERROR:" | cut -d':' -f2-)
    echo "❌ TASK CREATION FAILED"
    echo "Error: $ERROR_MSG"
    echo ""
    echo "💡 TROUBLESHOOTING:"
    echo "  • Check MongoDB connection: brew services list | grep mongodb"
    echo "  • Check RabbitMQ connection: brew services list | grep rabbitmq"
    echo "  • View logs: tail -20 .logs/manager.log"
    exit 1
else
    echo "❌ Unexpected error during task creation"
    echo "Result: $TASK_RESULT"
    exit 1
fi

echo ""
echo "📋 STANDARD REQUIREMENTS INCLUDED:"
echo "  • Implement requested functionality"
echo "  • Write comprehensive tests"
echo "  • Create/update documentation"
echo "  • Follow coding standards"
echo "  • Ensure code quality"
echo ""
echo "🎯 TASK DELIVERED TO DEVELOPER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Features
- Creates task in database with "created" status
- Updates to "assigned" after successful RabbitMQ send
- Logs all activities to database
- Rollback on failures to maintain consistency
- Proper error handling and user feedback

## Task State Flow
1. **Created** - Task created in database
2. **Assigned** - Task successfully sent to queue
3. **In Progress** - Developer picks up task
4. **Completed** - Task finished

## Database Operations
- Creates task record with full metadata
- Updates task state after queue send
- Logs creation and assignment activities
- Updates manager agent state
- Rollback on any failure

## Error Handling
- Database connection failures
- RabbitMQ send failures
- Rollback task state on errors
- Clear error messages for troubleshooting

## Example
```bash
project:create_task "Add user authentication to the dashboard"
```

Creates task with proper database tracking and queue delivery.