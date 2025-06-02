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
mkdir -p .comms/completed
mkdir -p .comms/processed
mkdir -p .comms/active

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

# Create developer message listener script with database integration
cat > .agents/developer/message_listener.py << 'EOF'
#!/usr/bin/env python3
"""
Developer Agent RabbitMQ Message Listener with Database Integration

Listens for task assignments on the developer-queue and updates database state.
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

def handle_message(message):
    """
    Handle incoming messages for the developer.
    
    Args:
        message: Parsed JSON message
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type == 'task_assignment':
            handle_task_assignment(message)
        elif message_type == 'task_update':
            handle_task_update(message)
        elif message_type == 'resource_allocation':
            handle_resource_allocation(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def handle_task_assignment(message):
    """Handle task assignment messages."""
    task_id = message.get('task_id')
    from_agent = message.get('from_agent')
    task = message.get('task', {})
    priority = message.get('priority', 'normal')
    
    # Create task in database if it doesn't exist
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
    if created_task_id:
        logger.info(f"Task {task_id} created in database")
    
    # Update developer state with current task
    current_tasks = state_manager.get_agent_tasks('developer', ['assigned', 'in_progress'])
    state_manager.update_agent_state('developer', 'working', {
        'current_task_id': task_id,
        'current_tasks_count': len(current_tasks) + 1,
        'last_assignment': datetime.utcnow().isoformat()
    })
    
    # Log task assignment activity
    state_manager.log_activity('developer', 'task_assigned', {
        'task_id': task_id,
        'assigned_by': from_agent,
        'priority': priority,
        'title': task.get('title', '')
    })
    
    # Archive task assignment
    archive_task_assignment(message)
    
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

def handle_task_update(message):
    """Handle task update messages."""
    task_id = message.get('task_id')
    update_type = message.get('update_type')
    
    # Log task update
    state_manager.log_activity('developer', 'task_update_received', {
        'task_id': task_id,
        'update_type': update_type,
        'details': message.get('details', {})
    })
    
    print(f"📝 TASK UPDATE: {task_id}")
    print(f"   Update type: {update_type}")

def handle_resource_allocation(message):
    """Handle resource allocation messages."""
    resources = message.get('resources', {})
    
    # Update developer state with allocated resources
    state_manager.update_agent_state('developer', metadata={
        'allocated_resources': resources,
        'resources_updated': datetime.utcnow().isoformat()
    })
    
    print(f"🔧 RESOURCES ALLOCATED")
    for resource, value in resources.items():
        print(f"   {resource}: {value}")

def archive_task_assignment(task_message):
    """Archive the task assignment for record keeping."""
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
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")

def update_heartbeat():
    """Update developer heartbeat in database."""
    state_manager.update_agent_state('developer', metadata={
        'last_heartbeat': datetime.utcnow().isoformat()
    })

def main():
    """Main developer message listener."""
    print("👨‍💻 DEVELOPER MESSAGE LISTENER STARTING")
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
        print("Press Ctrl+C to stop")
        print("")
        
        # Update status to connected
        state_manager.update_agent_state('developer', 'active', {
            'message_broker_status': 'connected'
        })
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.DEVELOPER_QUEUE, handle_message)
        
        # Keep the main thread alive with periodic heartbeat
        try:
            import time
            while True:
                time.sleep(30)  # Update heartbeat every 30 seconds
                update_heartbeat()
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

# Make the message listener executable
chmod +x .agents/developer/message_listener.py

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
2. Start the message listener: `python3 .agents/developer/message_listener.py`
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
- `.agents/developer/message_listener.py`: RabbitMQ message processor
- `.logs/developer.log`: Local activity log (backup)
- Database entries for agent state, capabilities, and tools