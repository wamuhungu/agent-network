# Request Work from Manager

Allow developer agents to request new work assignments from the Manager Agent when idle.

## Purpose
Enables developer agents to:
- Proactively request work when they complete tasks
- Indicate their current capabilities and availability
- Allow manager to assign tasks based on priorities and workload
- Maintain optimal resource utilization across the agent network

## Implementation

```bash
#!/bin/bash

# Default developer capabilities if not specified
DEFAULT_CAPABILITIES="development,testing,documentation,debugging"

# Parse capabilities from command line or use defaults
if [ $# -eq 0 ]; then
    CAPABILITIES="$DEFAULT_CAPABILITIES"
else
    CAPABILITIES="$1"
fi

# Generate work request details
AGENT_ID="${AGENT_ID:-$(whoami)_dev}"
REQUEST_ID="work_req_$(date +%s)_$(head /dev/urandom | tr -dc a-z0-9 | head -c 4)"
TIMESTAMP=$(date -Iseconds)

echo "💼 REQUESTING WORK FROM MANAGER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent ID: $AGENT_ID"
echo "Request ID: $REQUEST_ID" 
echo "Timestamp: $TIMESTAMP"
echo "Capabilities: $CAPABILITIES"
echo ""

# Create work request message
cat > /tmp/work_request.json << EOF
{
  "message_type": "work_request",
  "request_id": "$REQUEST_ID",
  "timestamp": "$TIMESTAMP",
  "from_agent": "$AGENT_ID",
  "to_agent": "manager",
  "agent_status": {
    "status": "idle",
    "availability": "available",
    "current_workload": 0,
    "max_concurrent_tasks": 3
  },
  "capabilities": [$(echo "$CAPABILITIES" | sed 's/,/", "/g' | sed 's/^/"/' | sed 's/$/"/')],
  "preferences": {
    "task_types": ["development", "testing", "documentation"],
    "complexity": ["simple", "medium", "complex"],
    "priority": "any",
    "estimated_capacity_hours": 8
  },
  "environment": {
    "available_tools": ["code_editor", "test_runner", "debugger"],
    "project_familiarity": "medium",
    "previous_tasks_completed": 0
  },
  "constraints": {
    "time_availability": "8 hours",
    "resource_limitations": [],
    "skill_gaps": []
  }
}
EOF

echo "📤 Sending work request to manager..."

# Send work request to manager via RabbitMQ
python3 -c "
import sys
import json
sys.path.append('tools')

try:
    from message_broker import MessageBroker
    
    # Read message from temp file
    with open('/tmp/work_request.json', 'r') as f:
        message = json.load(f)
    
    # Send to work request queue
    broker = MessageBroker()
    if broker.connect():
        success = broker.send_message(MessageBroker.WORK_REQUEST_QUEUE, message)
        if success:
            print('✅ Work request sent successfully to work-request-queue')
            print(f'📊 Request ID: {message[\"request_id\"]}')
            print('🤖 Manager will assign appropriate tasks if available')
        else:
            print('❌ Failed to send work request')
            sys.exit(1)
        broker.disconnect()
    else:
        print('❌ Failed to connect to RabbitMQ')
        print('💡 Make sure RabbitMQ is running and manager is listening')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error sending work request: {e}')
    sys.exit(1)
"

# Clean up temp file
rm -f /tmp/work_request.json

# Log the work request
echo "$(date -Iseconds) [WORK_REQUEST] Sent work request $REQUEST_ID with capabilities: $CAPABILITIES" >> .logs/developer.log

echo ""
echo "🎯 WORK REQUEST SUBMITTED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Status: Request sent to Manager Agent"
echo ""
echo "The Manager Agent will:"
echo "  1. Evaluate your capabilities against available tasks"
echo "  2. Consider current workload and priorities"
echo "  3. Assign appropriate tasks if available"
echo "  4. Send task assignments to developer-queue"
echo ""
echo "💡 Monitor for incoming tasks or run: python3 .agents/developer/message_listener.py"
```

## Usage Examples

```bash
# Request work with default capabilities
project:request_work

# Request work with specific capabilities
project:request_work "frontend,react,typescript,testing"

# Request work as a backend specialist
project:request_work "backend,api,database,python,testing"

# Request work as a full-stack developer
project:request_work "frontend,backend,database,testing,deployment,documentation"
```

## Manager Response Workflow

When a work request is received, the Manager Agent will:

1. **Evaluate Request**
   - Check developer capabilities
   - Assess current availability
   - Review workload capacity

2. **Match Tasks**
   - Find available tasks matching capabilities
   - Consider task priorities and dependencies
   - Check resource requirements

3. **Assign Work**
   - Create task assignment messages
   - Send to developer-queue
   - Update task tracking and logs

4. **No Work Available**
   - Acknowledge request
   - Queue developer for future assignments
   - Notify when work becomes available

## Integration with Developer Agent

This command integrates with:
- **Developer message listener**: Receives task assignments
- **Task completion workflow**: Triggers automatic work requests
- **Agent status tracking**: Updates availability and workload

## Work Request Message Schema

```json
{
  "message_type": "work_request",
  "request_id": "work_req_<timestamp>_<random>",
  "timestamp": "ISO-8601 timestamp",
  "from_agent": "developer_id",
  "to_agent": "manager",
  "agent_status": {
    "status": "idle|busy|available",
    "availability": "available|limited|unavailable",
    "current_workload": 0,
    "max_concurrent_tasks": 3
  },
  "capabilities": ["list of skills and technologies"],
  "preferences": {
    "task_types": ["development", "testing", "documentation"],
    "complexity": ["simple", "medium", "complex"],
    "priority": "low|normal|high|any",
    "estimated_capacity_hours": 8
  },
  "environment": {
    "available_tools": ["list of available tools"],
    "project_familiarity": "low|medium|high",
    "previous_tasks_completed": 0
  },
  "constraints": {
    "time_availability": "time specification",
    "resource_limitations": ["list of limitations"],
    "skill_gaps": ["list of skills to avoid"]
  }
}
```

## Automated Work Requests

For fully autonomous operation, this command can be integrated into:
- Task completion callbacks
- Scheduled availability checks  
- Agent initialization scripts
- Workload monitoring systems

This enables continuous work assignment and optimal resource utilization across the agent network.