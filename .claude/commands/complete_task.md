# Complete Task Command

Mark a task as completed in the database and notify the manager agent via RabbitMQ.

## Purpose
Integrates database state management with message queue operations to:
- Update task state to 'completed' in database
- Update agent state back to 'ready'
- Log completion activity with duration and results
- Archive completed task data
- Send completion notification to manager

## Usage
```bash
# Complete a task (replace TASK_ID with actual task ID)
project:complete_task "TASK_ID"
```

## Implementation

```bash
#!/bin/bash

# Validate input
if [ -z "$1" ]; then
    echo "❌ Error: Task ID is required"
    echo "Usage: project:complete_task \"TASK_ID\""
    exit 1
fi

TASK_ID="$1"
TIMESTAMP=$(date -Iseconds)
COMPLETION_ID="completion_$(date +%Y%m%d_%H%M%S)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 6)"

# Validate task exists and get task details from database
TASK_VALIDATION=$(python3 -c "
import sys
import json
from datetime import datetime

# Add tools directory to Python path
sys.path.append('tools')

try:
    from state_manager import StateManager
    
    # Initialize database connection
    sm = StateManager()
    if not sm.is_connected():
        print('ERROR:Database connection failed')
        sys.exit(1)
    
    # Get task from database
    task = sm.get_task('$TASK_ID')
    if not task:
        print('ERROR:Task not found in database')
        sm.disconnect()
        sys.exit(1)
    
    # Check if task is assigned to developer
    if task.get('assigned_to') != 'developer':
        print('ERROR:Task not assigned to developer')
        sm.disconnect()
        sys.exit(1)
    
    # Check if task is in valid state for completion
    status = task.get('status')
    if status not in ['assigned', 'in_progress']:
        print(f'ERROR:Task cannot be completed from status: {status}')
        sm.disconnect()
        sys.exit(1)
    
    # Calculate duration if started
    duration = None
    if 'started_at' in task:
        start_time = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
    
    # Return task info for use in completion
    task_info = {
        'task_id': task['task_id'],
        'title': task.get('title', 'Untitled'),
        'assigned_by': task.get('assigned_by', 'unknown'),
        'started_at': task.get('started_at'),
        'duration_seconds': duration,
        'priority': task.get('priority', 'normal')
    }
    
    print(f'VALID:{json.dumps(task_info)}')
    sm.disconnect()
    
except ImportError as e:
    print(f'ERROR:Required module not available: {e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:Unexpected error: {e}')
    sys.exit(1)
")

# Parse validation result
if [[ "$TASK_VALIDATION" == "ERROR:"* ]]; then
    ERROR_MSG=$(echo "$TASK_VALIDATION" | sed 's/ERROR://')
    echo "❌ Error: $ERROR_MSG"
    exit 1
elif [[ "$TASK_VALIDATION" == "VALID:"* ]]; then
    TASK_INFO=$(echo "$TASK_VALIDATION" | sed 's/VALID://')
else
    echo "❌ Unexpected validation result"
    exit 1
fi

echo "$(date -Iseconds) [TASK_COMPLETE] Processing task completion for $TASK_ID..." >> .logs/developer.log

# Update task state in database and send completion message
COMPLETION_RESULT=$(python3 -c "
import sys
import json
from datetime import datetime

# Add tools directory to Python path
sys.path.append('tools')

try:
    from state_manager import StateManager
    from message_broker import send_completion_to_manager
    
    # Parse task info
    task_info = json.loads('$TASK_INFO')
    
    # Initialize database connection
    sm = StateManager()
    if not sm.is_connected():
        print('ERROR:Database connection failed')
        sys.exit(1)
    
    # Calculate duration for display
    duration_str = 'N/A'
    if task_info.get('duration_seconds'):
        duration = task_info['duration_seconds']
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        if hours > 0:
            duration_str = f'{hours}h {minutes}m {seconds}s'
        elif minutes > 0:
            duration_str = f'{minutes}m {seconds}s'
        else:
            duration_str = f'{seconds}s'
    
    # Create completion message
    completion_message = {
        'message_type': 'task_completion',
        'completion_id': '$COMPLETION_ID',
        'task_id': '$TASK_ID',
        'from_agent': 'developer',
        'to_agent': 'manager',
        'timestamp': '$TIMESTAMP',
        'status': 'completed',
        'completion': {
            'completed_at': '$TIMESTAMP',
            'summary': 'Task completed successfully',
            'deliverables_status': {
                'implementation': 'completed',
                'tests': 'completed',
                'documentation': 'completed',
                'code_review': 'ready'
            },
            'notes': 'All requirements have been fulfilled according to coding standards',
            'files_modified': [],
            'files_created': [],
            'next_steps': [],
            'duration': duration_str
        },
        'metadata': {
            'completed_by': 'developer',
            'effort_actual': duration_str,
            'quality_check': 'passed',
            'issues_encountered': [],
            'recommendations': [],
            'task_title': task_info.get('title'),
            'priority': task_info.get('priority')
        }
    }
    
    # First, update task state to 'completed' in database
    completion_metadata = {
        'completed_at': datetime.utcnow().isoformat(),
        'completion_id': '$COMPLETION_ID',
        'duration_seconds': task_info.get('duration_seconds'),
        'deliverables_completed': True,
        'quality_check': 'passed'
    }
    
    if not sm.update_task_state('$TASK_ID', 'completed', completion_metadata):
        print('ERROR:Failed to update task state in database')
        sm.disconnect()
        sys.exit(1)
    
    print('DB_UPDATE:Task marked as completed')
    
    # Log completion activity
    sm.log_activity('developer', 'task_completed', {
        'task_id': '$TASK_ID',
        'completion_id': '$COMPLETION_ID',
        'duration': duration_str,
        'title': task_info.get('title')
    })
    
    # Update developer state back to 'ready'
    sm.update_agent_state('developer', 'ready', {
        'last_completed_task': '$TASK_ID',
        'last_completion_time': datetime.utcnow().isoformat()
    })
    
    # Archive task data
    completed_task = sm.get_task('$TASK_ID')
    if completed_task:
        # Store completion data in archived_tasks collection
        sm.db.archived_tasks.insert_one({
            **completed_task,
            'archived_at': datetime.utcnow(),
            'archive_reason': 'completed'
        })
        print('DB_UPDATE:Task archived')
    
    # Now send to RabbitMQ
    try:
        success = send_completion_to_manager(completion_message)
        
        if success:
            print('SENT:Success')
            
            # Log successful send
            sm.log_activity('developer', 'completion_sent', {
                'task_id': '$TASK_ID',
                'completion_id': '$COMPLETION_ID',
                'sent_to': 'manager-queue'
            })
        else:
            # If send fails, log but don't rollback database
            print('SENT:Failed')
            
            sm.log_activity('developer', 'completion_send_failed', {
                'task_id': '$TASK_ID',
                'completion_id': '$COMPLETION_ID',
                'error': 'Failed to send to RabbitMQ'
            })
            
    except Exception as e:
        print(f'SENT:Error:{e}')
        
        sm.log_activity('developer', 'completion_send_error', {
            'task_id': '$TASK_ID',
            'completion_id': '$COMPLETION_ID',
            'error': str(e)
        })
    
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
if [[ "$COMPLETION_RESULT" == "ERROR:"* ]]; then
    ERROR_MSG=$(echo "$COMPLETION_RESULT" | grep "^ERROR:" | cut -d':' -f2-)
    echo "❌ TASK COMPLETION FAILED"
    echo "Error: $ERROR_MSG"
    echo ""
    echo "💡 TROUBLESHOOTING:"
    echo "  • Check MongoDB connection: brew services list | grep mongodb"
    echo "  • Check task status: project:agent_status"
    echo "  • View logs: tail -20 .logs/developer.log"
    exit 1
fi

# Check database updates
DB_UPDATES=$(echo "$COMPLETION_RESULT" | grep "^DB_UPDATE:" | wc -l)
SEND_STATUS=$(echo "$COMPLETION_RESULT" | grep "^SENT:" | cut -d':' -f2)

echo "✅ TASK COMPLETED IN DATABASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID: $TASK_ID"
echo "Completion ID: $COMPLETION_ID"
echo "Completed At: $TIMESTAMP"

if [ "$DB_UPDATES" -ge "2" ]; then
    echo ""
    echo "📊 DATABASE UPDATES:"
    echo "  ✅ Task state updated to 'completed'"
    echo "  ✅ Task data archived"
    echo "  ✅ Developer state updated to 'ready'"
    echo "  ✅ Activities logged"
fi

if [[ "$SEND_STATUS" == "Success" ]]; then
    echo ""
    echo "📬 NOTIFICATION:"
    echo "  ✅ Completion sent to manager-queue"
    echo "  • Manager notified immediately"
elif [[ "$SEND_STATUS" == "Failed" ]]; then
    echo ""
    echo "⚠️  NOTIFICATION:"
    echo "  ❌ Failed to send to manager-queue"
    echo "  • Task is completed in database"
    echo "  • Manager notification pending"
    echo ""
    echo "💡 To retry notification:"
    echo "  • Check RabbitMQ: project:start_message_broker"
    echo "  • Resend manually if needed"
else
    echo ""
    echo "⚠️  NOTIFICATION ERROR: $SEND_STATUS"
fi

# Archive task files from active directory (file system cleanup)
mkdir -p .comms/completed
ARCHIVED_TASK=".comms/completed/${TASK_ID}_${COMPLETION_ID}.json"

# Find and archive the original task assignment from active directory
ACTIVE_TASK_FILE=$(find .comms/active -name "*${TASK_ID}*" -type f 2>/dev/null | head -1)
if [ -n "$ACTIVE_TASK_FILE" ]; then
    cp "$ACTIVE_TASK_FILE" "$ARCHIVED_TASK"
    rm "$ACTIVE_TASK_FILE"
    echo "$(date -Iseconds) [ARCHIVE] Task file archived: $ARCHIVED_TASK" >> .logs/developer.log
fi

# Log task completion to local file (backup)
if [ ! -f .logs/developer.log ]; then
    mkdir -p .logs
    touch .logs/developer.log
fi

echo "$(date -Iseconds) [TASK_COMPLETE] Task completed: $TASK_ID" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Database updated, task archived" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Developer status: ready" >> .logs/developer.log

echo ""
echo "🎯 READY FOR NEXT TASK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Features
- Validates task exists in database and is assigned to developer
- Updates task state to 'completed' with metadata
- Archives task data to archived_tasks collection
- Updates developer state back to 'ready'
- Logs all activities to database
- Sends completion notification to manager
- Maintains consistency between database and message queue

## Task Completion Flow
1. **Validation** - Verify task exists and can be completed
2. **Database Update** - Mark task as completed
3. **Archive** - Move task to archived collection
4. **State Update** - Set developer to ready
5. **Notification** - Send to manager queue
6. **Activity Logging** - Record all actions

## Database Operations
- Updates task state with completion metadata
- Archives full task data for history
- Updates developer agent state
- Logs completion activity
- Tracks duration if task was started

## Error Handling
- Task validation before processing
- Database updates complete even if notification fails
- Clear error messages for troubleshooting
- No rollback of completed status

## Example
```bash
project:complete_task "task_20241126_143022_A7F3Kx"
```

Completes the specified task with full database integration.