# Become Manager Agent

Initialize this Claude Code instance as a Manager Agent in the agent network using database state management.

## Purpose
Transforms the current Claude Code session into a Manager Agent with:
- Agent identity stored in MongoDB database
- Real-time status tracking via database
- Activity logging to centralized database
- Task coordination and monitoring capabilities

## Implementation

```bash
# Set agent identity environment variables
export AGENT_ID="manager"
export AGENT_TYPE="manager"
export AGENT_START_TIME=$(date -Iseconds)
export AGENT_SESSION_ID=$(date +%s)_mgr

# Create necessary directories if they don't exist
mkdir -p .agents/manager
mkdir -p .logs

# Initialize Manager Agent in Database
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager
from datetime import datetime

# Initialize StateManager
state_manager = StateManager()

if state_manager.is_connected():
    print('✅ Connected to MongoDB')
    
    # Set initial manager state
    manager_state = {
        'agent_id': 'manager',
        'agent_type': 'manager',
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
    
    # Update manager state in database
    if state_manager.update_agent_state('manager', 'active', manager_state):
        print('✅ Manager state initialized in database')
    
    # Set manager capabilities
    capabilities = [
        'task_assignment',
        'task_coordination',
        'resource_allocation',
        'progress_monitoring',
        'conflict_resolution',
        'project_planning',
        'team_management',
        'requirement_analysis'
    ]
    
    if state_manager.set_agent_capabilities('manager', capabilities):
        print('✅ Manager capabilities stored')
    
    # Log initialization activity
    if state_manager.log_activity('manager', 'initialization', {
        'session_id': '$AGENT_SESSION_ID',
        'message': 'Manager agent initialized successfully',
        'capabilities': capabilities,
        'communication_channels': ['rabbitmq:manager-queue']
    }):
        print('✅ Initialization logged to database')
    
    # Display current state
    state = state_manager.get_agent_state('manager')
    if state:
        print(f'📊 Manager Status: {state.get(\"status\")}')
        print(f'🔧 Capabilities: {len(state.get(\"capabilities\", []))} registered')
    
    state_manager.disconnect()
else:
    print('❌ Failed to connect to MongoDB')
    print('💡 Make sure MongoDB is running: brew services start mongodb/brew/mongodb-community@7.0')
    exit(1)
"

# Initialize local log file (backup logging)
echo "$(date -Iseconds) [INIT] Manager Agent initialized - Session: $AGENT_SESSION_ID" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Manager state stored in MongoDB database" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Communication channels: RabbitMQ manager-queue" >> .logs/manager.log

# Test database and RabbitMQ connectivity
echo "$(date -Iseconds) [TEST] Testing system connectivity..." >> .logs/manager.log

python3 -c "
import sys
sys.path.append('tools')

# Test MongoDB
try:
    from state_manager import StateManager
    sm = StateManager()
    if sm.is_connected():
        print('✅ MongoDB connection successful')
        
        # Get manager status
        state = sm.get_agent_state('manager')
        if state:
            print(f'📊 Manager Status: {state.get(\"status\")}')
            print(f'🆔 Session ID: {state.get(\"session_id\")}')
        
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

# Create manager context file if it doesn't exist
if [ ! -f .agents/manager/context.md ]; then
  cat > .agents/manager/context.md << 'EOF'
# Manager Agent Context

## Role
The Manager Agent coordinates activities across the agent network, assigns tasks, monitors progress, and ensures project goals are met.

## State Management
- Agent state stored in MongoDB database
- Real-time status updates via StateManager
- Activity logging to centralized database
- Heartbeat monitoring for availability

## Responsibilities
- Task assignment and delegation
- Resource allocation and optimization
- Progress monitoring and reporting  
- Conflict resolution between agents
- Project planning and timeline management
- Communication facilitation
- Work request processing

## Communication Protocols
- Receive messages via RabbitMQ manager-queue
- Send task assignments to developer-queue
- Store completed tasks in MongoDB
- Maintain real-time status in MongoDB
- Process work requests from agents

## Database Operations
- Update agent states and heartbeats
- Track task completions and assignments
- Log all activities for audit trail
- Query agent availability and workload
- Monitor system-wide performance
EOF
fi

# Display confirmation
echo "🤖 MANAGER AGENT INITIALIZED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent ID: $AGENT_ID"
echo "Session ID: $AGENT_SESSION_ID"
echo "Start Time: $AGENT_START_TIME"
echo "Database: MongoDB (agent_network)"
echo "Log File: .logs/manager.log"
echo ""
echo "📋 MANAGER CAPABILITIES:"
echo "  • Task assignment and coordination"
echo "  • Resource allocation and optimization"
echo "  • Progress monitoring via database"
echo "  • Conflict resolution"
echo "  • Project planning"
echo "  • Work request processing"
echo ""
echo "💾 DATABASE INTEGRATION:"
echo "  • Agent state in MongoDB"
echo "  • Real-time activity logging"
echo "  • Centralized task tracking"
echo "  • Heartbeat monitoring"
echo ""
echo "📡 COMMUNICATION CHANNELS:"
echo "  • RabbitMQ manager-queue"
echo "  • Database state synchronization"
echo ""
echo "🎯 READY FOR TASK COORDINATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set prompt context
echo "You are now acting as the Manager Agent for this agent network."
echo "Your state is managed in MongoDB database for persistence and reliability."
echo "Monitor agent activities through database queries and coordinate tasks effectively."
```

## Usage
Run this command to initialize the current Claude Code session as a Manager Agent:

```bash
# Execute the become_manager command
project:become_manager
```

## Post-Initialization
After running this command:
1. Your agent state is stored in MongoDB database
2. Start the message listener in a separate terminal: `python3 .agents/manager/message_listener.py`
3. Monitor agent activities via database queries
4. Track tasks and work requests in centralized database
5. All activities are logged for audit trail

## Database State
The manager agent maintains the following in the database:
- **Agent State**: Current status, capabilities, session info
- **Activity Logs**: All actions and decisions logged
- **Task Tracking**: Monitor task assignments and completions
- **Work Requests**: Process and track agent requests
- **Heartbeat**: Regular updates to show availability

## Monitoring Commands
After initialization, use these to monitor state:
```python
# Check manager status
from tools.state_manager import StateManager
sm = StateManager()
state = sm.get_agent_state('manager')
print(f"Status: {state['status']}")

# View recent activities
activities = sm.get_activity_history('manager', limit=10)
for activity in activities:
    print(f"{activity['timestamp']}: {activity['activity_type']}")
```

## Environment Variables Set
- `AGENT_ID`: "manager"
- `AGENT_TYPE`: "manager" 
- `AGENT_START_TIME`: ISO timestamp of initialization
- `AGENT_SESSION_ID`: Unique session identifier

## Files Created
- `.agents/manager/context.md`: Role and responsibility documentation
- `.logs/manager.log`: Local activity log (backup)
- Database entries for agent state and capabilities