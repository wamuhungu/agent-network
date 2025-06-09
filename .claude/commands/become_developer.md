# Become Developer Agent

Initialize this Claude Code instance as a Developer Agent in the agent network using database state management.

## Purpose
Transforms the current Claude Code session into a Developer Agent with:
- Agent identity stored in MongoDB database
- Real-time status tracking via database
- Activity logging to centralized database
- Code implementation and testing capabilities

## Implementation

```bash
# Set agent identity environment variables
export AGENT_ID="developer"
export AGENT_TYPE="developer"
export AGENT_START_TIME=$(date -Iseconds)
export AGENT_SESSION_ID=$(date +%s)_dev

# Create necessary directories if they don't exist
mkdir -p .agents/developer
mkdir -p .logs

# Initialize Developer Agent in Database
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager
from datetime import datetime

# Initialize StateManager
state_manager = StateManager()

if state_manager.is_connected():
    print('✅ Connected to MongoDB')
    
    # Set initial developer state
    developer_state = {
        'agent_id': 'developer',
        'agent_type': 'developer',
        'status': 'active',
        'session_id': '$AGENT_SESSION_ID',
        'start_time': '$AGENT_START_TIME',
        'last_activity': '$AGENT_START_TIME',
        'pid': $$,
        'version': '1.0.0',
        'environment': {
            'AGENT_ID': '$AGENT_ID',
            'AGENT_TYPE': '$AGENT_TYPE',
            'AGENT_SESSION_ID': '$AGENT_SESSION_ID'
        }
    }
    
    # Update developer state in database
    if state_manager.update_agent_state('developer', 'active', developer_state):
        print('✅ Developer state initialized in database')
    
    # Set developer capabilities
    capabilities = [
        'code_implementation',
        'software_development',
        'testing_and_debugging',
        'code_review',
        'technical_documentation',
        'system_integration',
        'performance_optimization',
        'security_analysis'
    ]
    
    if state_manager.set_agent_capabilities('developer', capabilities):
        print('✅ Developer capabilities stored')
    
    # Store available development tools
    dev_tools = [
        'python',
        'javascript',
        'typescript',
        'html_css',
        'flask',
        'react',
        'mongodb',
        'rabbitmq',
        'git',
        'pytest',
        'jest'
    ]
    
    # Update state with development tools
    state_manager.update_agent_state('developer', metadata={
        'development_tools': dev_tools
    })
    
    # Log initialization activity
    if state_manager.log_activity('developer', 'initialization', {
        'session_id': '$AGENT_SESSION_ID',
        'message': 'Developer agent initialized successfully',
        'capabilities': capabilities,
        'development_tools': dev_tools,
        'communication_channels': ['rabbitmq:developer-queue']
    }):
        print('✅ Initialization logged to database')
    
    # Display current state
    state = state_manager.get_agent_state('developer')
    if state:
        print(f'📊 Developer Status: {state.get(\"status\")}')
        print(f'🔧 Capabilities: {len(state.get(\"capabilities\", []))} registered')
        print(f'🛠️  Dev Tools: {len(state.get(\"development_tools\", []))} available')
    
    state_manager.disconnect()
else:
    print('❌ Failed to connect to MongoDB')
    print('💡 Make sure MongoDB is running: brew services start mongodb/brew/mongodb-community@7.0')
    exit(1)
"

# Initialize local log file (backup logging)
echo "$(date -Iseconds) [INIT] Developer Agent initialized - Session: $AGENT_SESSION_ID" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Developer state stored in MongoDB database" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Communication channels: RabbitMQ developer-queue" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Development tools registered in database" >> .logs/developer.log

# Test database and RabbitMQ connectivity
echo "$(date -Iseconds) [TEST] Testing system connectivity..." >> .logs/developer.log

python3 -c "
import sys
sys.path.append('tools')

# Test MongoDB
try:
    from state_manager import StateManager
    sm = StateManager()
    if sm.is_connected():
        print('✅ MongoDB connection successful')
        
        # Get developer status
        state = sm.get_agent_state('developer')
        if state:
            print(f'📊 Developer Status: {state.get(\"status\")}')
            print(f'🆔 Session ID: {state.get(\"session_id\")}')
            
            # Check current tasks
            tasks = sm.get_agent_tasks('developer', ['assigned', 'in_progress'])
            print(f'📋 Current Tasks: {len(tasks)}')
        
        sm.disconnect()
    else:
        print('❌ MongoDB connection failed')
except Exception as e:
    print(f'❌ MongoDB error: {e}')

# Test RabbitMQ
try:
    from message_broker import MessageBroker
    broker = MessageBroker()
    if broker.connect():
        print('✅ RabbitMQ connection successful')
        status = broker.get_broker_status()
        print(f'📊 Broker status: Connected')
        broker.disconnect()
    else:
        print('❌ RabbitMQ connection failed')
        print('💡 Start RabbitMQ: project:start_message_broker')
except Exception as e:
    print(f'❌ RabbitMQ error: {e}')
"

# Create developer context file if it doesn't exist
if [ ! -f .agents/developer/context.md ]; then
  cat > .agents/developer/context.md << 'EOF'
# Developer Agent Context

## Role and Responsibilities

This agent is responsible for:
- Implementing code based on specifications from the manager agent
- Writing unit tests and ensuring code quality
- Refactoring and optimizing code
- Documenting implementation details
- Reporting progress and issues
- Testing and debugging implementations
- Performing code reviews
- Creating technical documentation
- Following coding standards and best practices

## State Management
- Agent state stored in MongoDB database
- Real-time status updates via StateManager
- Activity logging to centralized database
- Task tracking and progress monitoring
- Heartbeat monitoring for availability

## Communication Protocol
- Receive tasks via RabbitMQ developer-queue
- Provide status updates via database
- Ask clarifying questions when requirements are unclear
- Submit completed work with summary of implementation approach
- Monitor task assignments in database
- Create completion messages when work is finished
- Track work status in MongoDB
- Maintain activity logs for audit trail

## Development Tools
The developer agent has access to:
- Python (Flask, Django, FastAPI)
- JavaScript/TypeScript (React, Node.js)
- HTML/CSS (modern web standards)
- Database systems (MongoDB, PostgreSQL)
- Message queuing (RabbitMQ)
- Version control (Git)
- Testing frameworks (pytest, jest)
- Documentation tools

## Best Practices
- Follow the project's established coding standards
- Commit code frequently with descriptive messages
- Write self-documenting code with appropriate comments
- Implement comprehensive error handling
- Consider performance, security, and maintainability
- Test implementations thoroughly before completion
- Update documentation as part of every task
- Ensure code quality and maintainability standards
- Review requirements carefully before starting implementation

## Database Operations
- Query assigned tasks from database
- Update task progress in real-time
- Log all development activities
- Track resource utilization
- Monitor code quality metrics
- Store test results and coverage
EOF
fi

# Display confirmation
echo "👨‍💻 DEVELOPER AGENT INITIALIZED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent ID: $AGENT_ID"
echo "Session ID: $AGENT_SESSION_ID"
echo "Start Time: $AGENT_START_TIME"
echo "Database: MongoDB (agent_network)"
echo "Log File: .logs/developer.log"
echo ""
echo "🛠️  DEVELOPER CAPABILITIES:"
echo "  • Code implementation"
echo "  • Software testing and debugging"
echo "  • Code review and quality assurance"
echo "  • Technical documentation"
echo "  • System integration"
echo "  • Performance optimization"
echo ""
echo "⚙️  DEVELOPMENT TOOLS:"
echo "  • Python, JavaScript, TypeScript"
echo "  • HTML/CSS, React, Flask"
echo "  • MongoDB, RabbitMQ"
echo "  • Git version control"
echo "  • Testing frameworks"
echo ""
echo "💾 DATABASE INTEGRATION:"
echo "  • Agent state in MongoDB"
echo "  • Real-time task tracking"
echo "  • Activity logging"
echo "  • Progress monitoring"
echo ""
echo "📡 COMMUNICATION CHANNELS:"
echo "  • RabbitMQ developer-queue"
echo "  • Database state synchronization"
echo ""
echo "🚀 READY FOR DEVELOPMENT TASKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set prompt context
echo "You are now acting as the Developer Agent for this agent network."
echo "Your state is managed in MongoDB database for persistence and reliability."
echo "Implement code, test functionality, and create technical solutions."
echo "Monitor task assignments through database queries."
```

## Usage
Run this command to initialize the current Claude Code session as a Developer Agent:

```bash
# Execute the become_developer command
project:become_developer
```

## Post-Initialization
After running this command:
1. Your agent state is stored in MongoDB database
2. Start the message listener in a separate terminal: `python3 .agents/developer/message_listener.py`
3. Check for task assignments via database queries
4. Implement code following project standards
5. All activities are logged for audit trail

## Database State
The developer agent maintains the following in the database:
- **Agent State**: Current status, capabilities, session info
- **Development Tools**: Available languages and frameworks
- **Task Assignments**: Current and completed tasks
- **Activity Logs**: All development activities
- **Progress Tracking**: Real-time task progress
- **Heartbeat**: Regular updates to show availability

## Task Management
Monitor and manage tasks using database queries:
```python
# Check assigned tasks
from tools.state_manager import StateManager
sm = StateManager()

# Get current tasks
tasks = sm.get_agent_tasks('developer', ['assigned', 'in_progress'])
for task in tasks:
    print(f"Task: {task['task_id']} - {task['title']}")

# Update task progress
sm.update_task_state(task_id, 'in_progress', {
    'progress': 50,
    'notes': 'Implementing core functionality'
})

# View recent activities
activities = sm.get_activity_history('developer', limit=10)
```

## Environment Variables Set
- `AGENT_ID`: "developer"
- `AGENT_TYPE`: "developer"
- `AGENT_START_TIME`: ISO timestamp of initialization
- `AGENT_SESSION_ID`: Unique session identifier

## Files Created
- `.agents/developer/context.md`: Role and responsibility documentation
- `.logs/developer.log`: Local activity log (backup)
- Database entries for agent state, capabilities, and tools