# Create Task Command

Create a new task assignment for the developer agent.

## Purpose
Generates a structured task assignment with unique ID, requirements, and proper JSON formatting for the agent communication protocol.

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

# Send task message to RabbitMQ developer-queue
echo "$(date -Iseconds) [TASK_CREATE] Sending task to RabbitMQ developer-queue..." >> .logs/manager.log

# Create and send task message via RabbitMQ
python3 -c "
import sys
import json
from datetime import datetime

# Add tools directory to Python path
sys.path.append('tools')

try:
    from message_broker import send_task_to_developer
    
    # Create task message
    task_message = {
        'message_type': 'task_assignment',
        'task_id': '$TASK_ID',
        'from_agent': 'manager',
        'to_agent': 'developer',
        'timestamp': '$TIMESTAMP',
        'priority': 'normal',
        'status': 'assigned',
        'task': {
            'description': '$TASK_DESCRIPTION',
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
            'context': {
                'project_root': '.',
                'coding_standards': 'docs/standards/coding_standards.md',
                'test_directory': 'tests/',
                'documentation_directory': 'docs/'
            }
        },
        'metadata': {
            'created_by': 'manager',
            'assigned_to': 'developer',
            'estimated_effort': 'TBD',
            'dependencies': [],
            'tags': []
        }
    }
    
    # Send message to developer queue
    success = send_task_to_developer(task_message)
    
    if success:
        print('✅ Task sent successfully to developer-queue')
        with open('.logs/manager.log', 'a') as f:
            f.write('$(date -Iseconds) [TASK_SEND] Task $TASK_ID sent to developer-queue successfully\n')
    else:
        print('❌ Failed to send task to developer-queue')
        print('💡 Make sure RabbitMQ is running (use: project:start_message_broker)')
        with open('.logs/manager.log', 'a') as f:
            f.write('$(date -Iseconds) [ERROR] Failed to send task $TASK_ID to developer-queue\n')
        sys.exit(1)
        
except ImportError as e:
    print('❌ RabbitMQ message broker not available')
    print(f'Error: {e}')
    print('💡 Install pika: pip install pika')
    print('💡 Start RabbitMQ: project:start_message_broker')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error sending task: {e}')
    with open('.logs/manager.log', 'a') as f:
        f.write('$(date -Iseconds) [ERROR] Task send error: $e\n')
    sys.exit(1)
"

# Check if message sending was successful
if [ $? -eq 0 ]; then
    MESSAGE_SENT=true
else
    MESSAGE_SENT=false
    echo "❌ TASK CREATION FAILED"
    echo "Task could not be sent to developer queue"
    exit 1
fi

# Log task creation
if [ ! -f .logs/manager.log ]; then
    mkdir -p .logs
    touch .logs/manager.log
fi

echo "$(date -Iseconds) [TASK_CREATE] Task created: $TASK_ID - $TASK_DESCRIPTION" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Task file: $TASK_FILE" >> .logs/manager.log

# Update manager status with current task
if [ -f .agents/manager/status.json ]; then
    # Use a simple approach to add task to current_tasks array
    cp .agents/manager/status.json .agents/manager/status.json.bak
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('.agents/manager/status.json', 'r') as f:
        status = json.load(f)
    
    status['last_activity'] = datetime.now().isoformat()
    if 'current_tasks' not in status:
        status['current_tasks'] = []
    
    status['current_tasks'].append({
        'task_id': '$TASK_ID',
        'description': '$TASK_DESCRIPTION',
        'assigned_at': '$TIMESTAMP',
        'status': 'assigned'
    })
    
    with open('.agents/manager/status.json', 'w') as f:
        json.dump(status, f, indent=2)
        
except Exception as e:
    print(f'Warning: Could not update manager status: {e}', file=sys.stderr)
"
fi

# Display confirmation
echo "✅ TASK SENT TO DEVELOPER QUEUE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID: $TASK_ID"
echo "Description: $TASK_DESCRIPTION"
echo "Sent to: RabbitMQ developer-queue"
echo "Timestamp: $TIMESTAMP"
echo ""
echo "📋 STANDARD REQUIREMENTS INCLUDED:"
echo "  • Implement requested functionality"
echo "  • Write comprehensive tests"
echo "  • Create/update documentation"
echo "  • Follow coding standards"
echo "  • Ensure code quality"
echo ""
echo "🎯 TASK DELIVERED TO DEVELOPER"
echo "📬 Developer will be notified immediately"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Task Message Format
The command creates JSON messages with this structure:
- `message_type`: "task_assignment"
- `task_id`: Unique identifier with timestamp
- `from_agent`/`to_agent`: Agent communication routing
- `task.description`: User-provided task description
- `task.requirements`: Standard implementation requirements
- `task.deliverables`: Expected outputs
- `metadata`: Additional task tracking information

## Actions Performed
- Sends task message to RabbitMQ developer-queue
- Log entry in `.logs/manager.log`
- Updated `.agents/manager/status.json` with current task
- Immediate delivery to developer via message broker

## Example
```bash
project:create_task "Add user authentication to the dashboard"
```

Creates task with ID like `task_20241126_143022_A7F3Kx` and structured requirements.