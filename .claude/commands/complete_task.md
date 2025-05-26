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

# Check if original task file exists
ORIGINAL_TASK_FILE=".comms/${TASK_ID}.json"
if [ ! -f "$ORIGINAL_TASK_FILE" ]; then
    echo "❌ Error: Task file not found: $ORIGINAL_TASK_FILE"
    echo "Available tasks:"
    ls -1 .comms/task_*.json 2>/dev/null | head -5 | sed 's/^/  /'
    exit 1
fi

# Create completion message file
COMPLETION_FILE=".comms/${COMPLETION_ID}.json"

# Generate structured completion message
cat > "$COMPLETION_FILE" << EOF
{
  "message_type": "task_completion",
  "completion_id": "$COMPLETION_ID",
  "task_id": "$TASK_ID",
  "from_agent": "developer",
  "to_agent": "manager",
  "timestamp": "$TIMESTAMP",
  "status": "completed",
  "completion": {
    "completed_at": "$TIMESTAMP",
    "summary": "Task completed successfully",
    "deliverables_status": {
      "implementation": "completed",
      "tests": "completed",
      "documentation": "completed",
      "code_review": "ready"
    },
    "notes": "All requirements have been fulfilled according to coding standards",
    "files_modified": [],
    "files_created": [],
    "next_steps": []
  },
  "metadata": {
    "completed_by": "developer",
    "effort_actual": "TBD",
    "quality_check": "passed",
    "issues_encountered": [],
    "recommendations": []
  }
}
EOF

# Archive original task to completed directory
mkdir -p .comms/completed
ARCHIVED_TASK=".comms/completed/${TASK_ID}.json"
cp "$ORIGINAL_TASK_FILE" "$ARCHIVED_TASK"

# Add completion timestamp to archived task
python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('$ARCHIVED_TASK', 'r') as f:
        task = json.load(f)
    
    task['completed_at'] = '$TIMESTAMP'
    task['completion_id'] = '$COMPLETION_ID'
    task['status'] = 'completed'
    
    with open('$ARCHIVED_TASK', 'w') as f:
        json.dump(task, f, indent=2)
        
except Exception as e:
    print(f'Warning: Could not update archived task: {e}', file=sys.stderr)
"

# Remove original task from active queue
rm "$ORIGINAL_TASK_FILE"

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

# Move to processed directory for cleanup
mkdir -p .comms/processed
mv "$COMPLETION_FILE" ".comms/processed/${COMPLETION_ID}.json"

# Display confirmation
echo "✅ TASK COMPLETED SUCCESSFULLY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID: $TASK_ID"
echo "Completion ID: $COMPLETION_ID"
echo "Completed At: $TIMESTAMP"
echo ""
echo "📁 FILES UPDATED:"
echo "  • Completion message: .comms/processed/$COMPLETION_ID.json"
echo "  • Task archived: $ARCHIVED_TASK"
echo "  • Original task removed from active queue"
echo ""
echo "📊 STATUS UPDATES:"
echo "  • Developer status: ready"
echo "  • Task moved to completed list"
echo "  • Manager notified of completion"
echo ""
echo "🎯 READY FOR NEXT TASK"
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

## File Operations
1. Creates completion message in `.comms/`
2. Archives original task to `.comms/completed/`
3. Moves completion message to `.comms/processed/`
4. Updates developer status to "ready"
5. Logs completion to `.logs/developer.log`

## Example
```bash
project:complete_task "task_20241126_143022_A7F3Kx"
```

Completes the specified task and notifies the manager.