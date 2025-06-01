# Assign Requirement to Manager

Send a high-level requirement to the Manager Agent for intelligent task breakdown and orchestration.

## Purpose
Allows users to submit complex requirements that the Manager Agent will:
- Analyze and break down into manageable tasks
- Prioritize based on dependencies and project goals
- Create appropriate task assignments for developers
- Coordinate execution across multiple agents

## Implementation

```bash
#!/bin/bash

# Validate input
if [ $# -eq 0 ]; then
    echo "❌ Error: No requirement provided"
    echo "Usage: project:assign_requirement \"<requirement description>\""
    echo ""
    echo "Example:"
    echo "  project:assign_requirement \"Add user authentication with JWT tokens and password reset functionality\""
    exit 1
fi

REQUIREMENT="$1"
REQUIREMENT_ID="req_$(date +%s)_$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)"
TIMESTAMP=$(date -Iseconds)

echo "📋 ASSIGNING REQUIREMENT TO MANAGER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Requirement ID: $REQUIREMENT_ID"
echo "Timestamp: $TIMESTAMP"
echo "Requirement: $REQUIREMENT"
echo ""

# Create requirement message
cat > /tmp/requirement_message.json << EOF
{
  "message_type": "requirement_assignment",
  "requirement_id": "$REQUIREMENT_ID",
  "timestamp": "$TIMESTAMP",
  "from_user": "$(whoami)",
  "requirement": {
    "description": "$REQUIREMENT",
    "priority": "normal",
    "complexity": "auto_detect",
    "deadline": null,
    "context": {
      "project_phase": "development",
      "available_resources": ["developer"],
      "constraints": []
    }
  },
  "expected_deliverables": [],
  "acceptance_criteria": [],
  "dependencies": [],
  "metadata": {
    "source": "user_request",
    "urgency": "normal",
    "business_value": "medium"
  }
}
EOF

echo "📤 Sending requirement to manager-requirements-queue..."

# Send requirement to manager via RabbitMQ
python3 -c "
import sys
import json
sys.path.append('tools')

try:
    from message_broker import MessageBroker
    
    # Read message from temp file
    with open('/tmp/requirement_message.json', 'r') as f:
        message = json.load(f)
    
    # Send to manager requirements queue
    broker = MessageBroker()
    if broker.connect():
        success = broker.send_message(MessageBroker.MANAGER_REQUIREMENTS_QUEUE, message)
        if success:
            print('✅ Requirement sent successfully to manager-requirements-queue')
            print(f'📊 Requirement ID: {message[\"requirement_id\"]}')
            print('🤖 Manager will analyze and create appropriate tasks')
        else:
            print('❌ Failed to send requirement')
            sys.exit(1)
        broker.disconnect()
    else:
        print('❌ Failed to connect to RabbitMQ')
        print('💡 Make sure RabbitMQ is running and manager is listening')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error sending requirement: {e}')
    sys.exit(1)
"

# Clean up temp file
rm -f /tmp/requirement_message.json

# Log the requirement assignment
echo "$(date -Iseconds) [REQUIREMENT] Assigned requirement $REQUIREMENT_ID: $REQUIREMENT" >> .logs/manager.log

echo ""
echo "🎯 REQUIREMENT SUBMITTED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "The Manager Agent will:"
echo "  1. Analyze the requirement complexity"
echo "  2. Break it down into specific tasks"
echo "  3. Determine task dependencies and priorities"
echo "  4. Create task assignments for available developers"
echo "  5. Monitor progress and coordinate execution"
echo ""
echo "💡 Monitor progress in .logs/manager.log or run the manager message listener"
```

## Usage

```bash
# Submit a complex feature requirement
project:assign_requirement "Implement user authentication system with login, registration, and password reset"

# Submit a bug fix requirement  
project:assign_requirement "Fix memory leak in data processing module and add performance monitoring"

# Submit a refactoring requirement
project:assign_requirement "Refactor the API layer to use async/await patterns and improve error handling"
```

## Manager Processing Workflow

When a requirement is received, the Manager Agent will:

1. **Analysis Phase**
   - Parse requirement description
   - Assess complexity and scope
   - Identify required skills and resources

2. **Planning Phase**
   - Break down into specific, actionable tasks
   - Determine dependencies between tasks
   - Set priorities based on business value

3. **Assignment Phase**
   - Create task messages for developer-queue
   - Assign tasks based on developer availability
   - Set up monitoring and progress tracking

4. **Coordination Phase**
   - Monitor task completion
   - Handle dependencies and blockers
   - Provide status updates and reports

## Message Schema

The requirement message follows this schema:

```json
{
  "message_type": "requirement_assignment",
  "requirement_id": "req_<timestamp>_<random>",
  "timestamp": "ISO-8601 timestamp",
  "from_user": "username",
  "requirement": {
    "description": "High-level requirement description",
    "priority": "low|normal|high|critical",
    "complexity": "simple|medium|complex|auto_detect",
    "deadline": "ISO-8601 timestamp or null",
    "context": {
      "project_phase": "planning|development|testing|deployment",
      "available_resources": ["developer", "designer", "qa"],
      "constraints": ["time", "budget", "technical"]
    }
  },
  "expected_deliverables": ["list of expected outputs"],
  "acceptance_criteria": ["list of success criteria"],
  "dependencies": ["list of dependencies"],
  "metadata": {
    "source": "user_request|api|automated",
    "urgency": "low|normal|high|critical",
    "business_value": "low|medium|high|critical"
  }
}
```

## Integration with Existing Commands

- **project:create_task**: Direct task creation (bypasses manager)
- **project:assign_requirement**: High-level orchestration (via manager)
- **project:request_work**: Developer requests work from manager

This provides flexibility for both direct control and intelligent orchestration.