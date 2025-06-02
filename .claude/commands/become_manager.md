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
mkdir -p .comms/completed
mkdir -p .comms/processed

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

# Create manager message listener script with database integration
cat > .agents/manager/message_listener.py << 'EOF'
#!/usr/bin/env python3
"""
Manager Agent RabbitMQ Message Listener with Database Integration

Listens for messages on the manager-queue and updates database state.
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
        logging.FileHandler('.logs/manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize StateManager
state_manager = StateManager()

def handle_message(message):
    """
    Handle incoming messages for the manager.
    
    Args:
        message: Parsed JSON message
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type == 'task_completion':
            handle_task_completion(message)
        elif message_type == 'work_request':
            handle_work_request(message)
        elif message_type == 'status_update':
            handle_status_update(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def handle_task_completion(message):
    """Handle task completion messages."""
    task_id = message.get('task_id')
    from_agent = message.get('from_agent')
    completion_time = message.get('timestamp', datetime.utcnow().isoformat())
    
    # Update task status in database
    state_manager.update_task_state(task_id, 'completed', {
        'completed_by': from_agent,
        'completed_at': completion_time,
        'completion_summary': message.get('completion', {}).get('summary', '')
    })
    
    # Log completion activity
    state_manager.log_activity('manager', 'task_completed', {
        'task_id': task_id,
        'completed_by': from_agent,
        'summary': message.get('completion', {}).get('summary', '')
    })
    
    # Update manager heartbeat
    state_manager.update_agent_state('manager', metadata={
        'last_task_completion': completion_time,
        'tasks_completed_today': state_manager.get_tasks_by_status('completed')
    })
    
    # Archive completed task
    archive_completed_task(message)
    
    print(f"✅ TASK COMPLETED: {task_id}")
    print(f"   Completed by: {from_agent}")
    print(f"   Summary: {message.get('completion', {}).get('summary', 'N/A')}")

def handle_work_request(message):
    """Handle work request messages."""
    request_id = message.get('request_id')
    from_agent = message.get('from_agent')
    
    # Create work request in database
    req_id = state_manager.create_work_request(
        from_agent, 
        'manager',
        {
            'request_id': request_id,
            'type': message.get('request_type', 'general'),
            'details': message.get('details', {}),
            'priority': message.get('priority', 'normal')
        }
    )
    
    if req_id:
        print(f"📨 NEW WORK REQUEST: {req_id}")
        print(f"   From: {from_agent}")
        print(f"   Type: {message.get('request_type', 'general')}")

def handle_status_update(message):
    """Handle agent status update messages."""
    from_agent = message.get('from_agent')
    status = message.get('status')
    
    # Log status update
    state_manager.log_activity(from_agent, 'status_update', {
        'new_status': status,
        'metadata': message.get('metadata', {})
    })
    
    print(f"📊 STATUS UPDATE from {from_agent}: {status}")

def archive_completed_task(completion_message):
    """Archive the completed task for record keeping."""
    try:
        task_id = completion_message.get('task_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create archive filename
        archive_file = f".comms/completed/{task_id}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(archive_file), exist_ok=True)
        
        # Save completion message
        with open(archive_file, 'w') as f:
            json.dump(completion_message, f, indent=2)
            
        logger.info(f"Archived completion message to {archive_file}")
        
    except Exception as e:
        logger.error(f"Error archiving task: {e}")

def update_heartbeat():
    """Update manager heartbeat in database."""
    state_manager.update_agent_state('manager', metadata={
        'last_heartbeat': datetime.utcnow().isoformat()
    })

def main():
    """Main manager message listener."""
    print("🤖 MANAGER MESSAGE LISTENER STARTING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if not state_manager.is_connected():
        logger.error("Failed to connect to MongoDB")
        print("❌ Database connection failed")
        return 1
    
    try:
        # Update manager status to listening
        state_manager.update_agent_state('manager', 'listening')
        
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            state_manager.update_agent_state('manager', 'error', {
                'error': 'RabbitMQ connection failed'
            })
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("✅ Connected to MongoDB")
        print("📬 Listening for messages...")
        print("Press Ctrl+C to stop")
        print("")
        
        # Update status to connected
        state_manager.update_agent_state('manager', 'active', {
            'message_broker_status': 'connected'
        })
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.MANAGER_QUEUE, handle_message)
        
        # Keep the main thread alive with periodic heartbeat
        try:
            import time
            while True:
                time.sleep(30)  # Update heartbeat every 30 seconds
                update_heartbeat()
        except KeyboardInterrupt:
            print("\n🛑 Stopping manager message listener...")
            logger.info("Manager message listener stopped by user")
            
    except Exception as e:
        logger.error(f"Manager listener error: {e}")
        state_manager.update_agent_state('manager', 'error', {
            'error': str(e)
        })
        return 1
    finally:
        try:
            broker.disconnect()
            state_manager.update_agent_state('manager', 'stopped')
            state_manager.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
EOF

# Make the message listener executable
chmod +x .agents/manager/message_listener.py

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
- Archive completed tasks locally and in database
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
2. Start the message listener: `python3 .agents/manager/message_listener.py`
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
- `.agents/manager/message_listener.py`: RabbitMQ message processor
- `.logs/manager.log`: Local activity log (backup)
- Database entries for agent state and capabilities