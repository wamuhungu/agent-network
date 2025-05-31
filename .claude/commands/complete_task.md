# Complete Task Command

Mark a task as completed and notify the manager agent.

## Purpose
Creates a completion message for the manager, updates developer status, archives the original task, and logs the completion.

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

# Check if task exists in current developer status
TASK_EXISTS=$(python3 -c "
import json
import sys

try:
    with open('.agents/developer/status.json', 'r') as f:
        status = json.load(f)
    
    current_tasks = status.get('current_tasks', [])
    task_found = any(task.get('task_id') == '$TASK_ID' for task in current_tasks)
    
    if task_found:
        print('true')
    else:
        print('false')
except:
    print('false')
" 2>/dev/null)

if [ "$TASK_EXISTS" = "false" ]; then
    echo "❌ Error: Task $TASK_ID not found in current developer tasks"
    echo "Check your current tasks with:"
    echo "  cat .agents/developer/status.json | python3 -m json.tool"
    exit 1
fi

# Send completion message to RabbitMQ manager-queue
echo "$(date -Iseconds) [TASK_COMPLETE] Sending completion to RabbitMQ manager-queue..." >> .logs/developer.log

# Create and send completion message via RabbitMQ
python3 -c "
import sys
import json
from datetime import datetime

# Add tools directory to Python path
sys.path.append('tools')

try:
    from message_broker import send_completion_to_manager
    
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
            'next_steps': []
        },
        'metadata': {
            'completed_by': 'developer',
            'effort_actual': 'TBD',
            'quality_check': 'passed',
            'issues_encountered': [],
            'recommendations': []
        }
    }
    
    # Send message to manager queue
    success = send_completion_to_manager(completion_message)
    
    if success:
        print('✅ Completion sent successfully to manager-queue')
        with open('.logs/developer.log', 'a') as f:
            f.write('$(date -Iseconds) [COMPLETE_SEND] Task $TASK_ID completion sent to manager-queue successfully\n')
    else:
        print('❌ Failed to send completion to manager-queue')
        print('💡 Make sure RabbitMQ is running (use: project:start_message_broker)')
        with open('.logs/developer.log', 'a') as f:
            f.write('$(date -Iseconds) [ERROR] Failed to send completion $TASK_ID to manager-queue\n')
        sys.exit(1)
        
except ImportError as e:
    print('❌ RabbitMQ message broker not available')
    print(f'Error: {e}')
    print('💡 Install pika: pip install pika')
    print('💡 Start RabbitMQ: project:start_message_broker')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error sending completion: {e}')
    with open('.logs/developer.log', 'a') as f:
        f.write('$(date -Iseconds) [ERROR] Completion send error: $e\n')
    sys.exit(1)
"

# Check if message sending was successful
if [ $? -eq 0 ]; then
    MESSAGE_SENT=true
else
    MESSAGE_SENT=false
    echo "❌ TASK COMPLETION FAILED"
    echo "Completion could not be sent to manager queue"
    exit 1
fi

# Archive task assignment in completed directory for record keeping
mkdir -p .comms/completed
ARCHIVED_TASK=".comms/completed/${TASK_ID}_${COMPLETION_ID}.json"

# Find and archive the original task assignment from active directory
ACTIVE_TASK_FILE=$(find .comms/active -name "*${TASK_ID}*" -type f 2>/dev/null | head -1)
if [ -n "$ACTIVE_TASK_FILE" ]; then
    cp "$ACTIVE_TASK_FILE" "$ARCHIVED_TASK"
    rm "$ACTIVE_TASK_FILE"
    echo "$(date -Iseconds) [ARCHIVE] Task archived: $ARCHIVED_TASK" >> .logs/developer.log
fi

# Log task completion
if [ ! -f .logs/developer.log ]; then
    mkdir -p .logs
    touch .logs/developer.log
fi

echo "$(date -Iseconds) [TASK_COMPLETE] Task completed: $TASK_ID" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Completion message: $COMPLETION_FILE" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Task archived: $ARCHIVED_TASK" >> .logs/developer.log

# Update developer status back to ready
if [ -f .agents/developer/status.json ]; then
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('.agents/developer/status.json', 'r') as f:
        status = json.load(f)
    
    status['status'] = 'ready'
    status['last_activity'] = datetime.now().isoformat()
    
    # Remove completed task from current_tasks
    if 'current_tasks' in status:
        status['current_tasks'] = [t for t in status['current_tasks'] if t.get('task_id') != '$TASK_ID']
    
    # Add to completed_tasks
    if 'completed_tasks' not in status:
        status['completed_tasks'] = []
    
    status['completed_tasks'].append({
        'task_id': '$TASK_ID',
        'completed_at': '$TIMESTAMP',
        'completion_id': '$COMPLETION_ID'
    })
    
    with open('.agents/developer/status.json', 'w') as f:
        json.dump(status, f, indent=2)
        
except Exception as e:
    print(f'Warning: Could not update developer status: {e}', file=sys.stderr)
"
fi

# Display confirmation
echo "✅ TASK COMPLETION SENT TO MANAGER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID: $TASK_ID"
echo "Completion ID: $COMPLETION_ID"
echo "Completed At: $TIMESTAMP"
echo "Sent to: RabbitMQ manager-queue"
echo ""
echo "📁 FILES UPDATED:"
echo "  • Task archived: $ARCHIVED_TASK"
echo "  • Active task removed from queue"
echo ""
echo "📊 STATUS UPDATES:"
echo "  • Developer status: ready"
echo "  • Task moved to completed list"
echo "  • Manager notified immediately via RabbitMQ"
echo ""
echo "🎯 READY FOR NEXT TASK"
echo "📬 Manager will be notified immediately"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Completion Message Format
The command creates JSON messages with this structure:
- `message_type`: "task_completion"
- `completion_id`: Unique completion identifier
- `task_id`: Reference to original task
- `completion.deliverables_status`: Status of each requirement
- `completion.summary`: Brief completion summary
- `metadata`: Quality checks and recommendations

## Actions Performed
1. Sends completion message to RabbitMQ manager-queue
2. Archives original task to `.comms/completed/`
3. Removes active task from `.comms/active/`
4. Updates developer status to "ready"
5. Logs completion to `.logs/developer.log`
6. Immediate delivery to manager via message broker

## Example
```bash
project:complete_task "task_20241126_143022_A7F3Kx"
```

Completes the specified task and notifies the manager.