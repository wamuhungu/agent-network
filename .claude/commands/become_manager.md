# Become Manager Agent

Initialize this Claude Code instance as a Manager Agent in the agent network.

## Purpose
Transforms the current Claude Code session into a Manager Agent with:
- Agent identity and environment setup
- Status tracking and logging capabilities
- Communication monitoring
- Task coordination responsibilities

## Implementation

```bash
# Set agent identity environment variables
export AGENT_ID="manager"
export AGENT_TYPE="manager"
export AGENT_START_TIME=$(date -Iseconds)
export AGENT_SESSION_ID=$(date +%s)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)

# Create necessary directories if they don't exist
mkdir -p .agents/manager
mkdir -p .agents/developer
mkdir -p .logs
mkdir -p .comms/completed
mkdir -p .comms/processed

# Create manager status file
cat > .agents/manager/status.json << EOF
{
  "agent_id": "manager",
  "agent_type": "manager",
  "status": "active",
  "session_id": "$AGENT_SESSION_ID",
  "start_time": "$AGENT_START_TIME",
  "last_activity": "$AGENT_START_TIME",
  "capabilities": [
    "task_assignment",
    "task_coordination", 
    "resource_allocation",
    "progress_monitoring",
    "conflict_resolution",
    "project_planning"
  ],
  "current_tasks": [],
  "completed_tasks": [],
  "communication_channels": [
    "rabbitmq:manager-queue"
  ],
  "message_broker": {
    "enabled": true,
    "queue_name": "manager-queue",
    "status": "initializing"
  },
  "log_file": ".logs/manager.log",
  "pid": $$,
  "version": "1.0.0"
}
EOF

# Initialize manager log file
echo "$(date -Iseconds) [INIT] Manager Agent initialized - Session: $AGENT_SESSION_ID" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Manager capabilities: task coordination, resource allocation, progress monitoring" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Communication channels active: RabbitMQ manager-queue" >> .logs/manager.log

# Initialize RabbitMQ connection and start listening
echo "$(date -Iseconds) [BROKER] Initializing RabbitMQ connection..." >> .logs/manager.log

# Create manager message listener script
cat > .agents/manager/message_listener.py << 'EOF'
#!/usr/bin/env python3
"""
Manager Agent RabbitMQ Message Listener

Listens for task completion messages on the manager-queue and processes them.
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
except ImportError:
    print("ERROR: message_broker module not found. Ensure tools/message_broker.py exists.")
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

def handle_completion_message(message):
    """
    Handle incoming task completion messages.
    
    Args:
        message: Parsed JSON message from developer
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type == 'task_completion':
            # Process task completion
            completion_time = message.get('timestamp', datetime.now().isoformat())
            
            # Update manager status
            update_manager_status(message)
            
            # Archive completed task
            archive_completed_task(message)
            
            # Log completion
            logger.info(f"Task {task_id} completed successfully by {from_agent}")
            
            print(f"✅ TASK COMPLETED: {task_id}")
            print(f"   Completed by: {from_agent}")
            print(f"   Completed at: {completion_time}")
            
            # Display completion summary
            completion = message.get('completion', {})
            summary = completion.get('summary', 'No summary provided')
            print(f"   Summary: {summary}")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def update_manager_status(completion_message):
    """Update manager status with completed task information."""
    try:
        with open('.agents/manager/status.json', 'r') as f:
            status = json.load(f)
        
        # Add to completed tasks
        task_info = {
            'task_id': completion_message.get('task_id'),
            'completed_by': completion_message.get('from_agent'),
            'completed_at': completion_message.get('timestamp'),
            'summary': completion_message.get('completion', {}).get('summary', '')
        }
        
        status['completed_tasks'].append(task_info)
        status['last_activity'] = datetime.now().isoformat()
        
        # Update message broker status
        if 'message_broker' in status:
            status['message_broker']['status'] = 'connected'
        
        with open('.agents/manager/status.json', 'w') as f:
            json.dump(status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error updating manager status: {e}")

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

def main():
    """Main manager message listener."""
    print("🤖 MANAGER MESSAGE LISTENER STARTING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("📬 Listening for task completion messages...")
        print("Press Ctrl+C to stop")
        print("")
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.MANAGER_QUEUE, handle_completion_message)
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping manager message listener...")
            logger.info("Manager message listener stopped by user")
            
    except Exception as e:
        logger.error(f"Manager listener error: {e}")
        return 1
    finally:
        try:
            broker.disconnect()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
EOF

# Make the message listener executable
chmod +x .agents/manager/message_listener.py

# Test RabbitMQ connection
echo "$(date -Iseconds) [BROKER] Testing RabbitMQ connection..." >> .logs/manager.log

python3 -c "
import sys
sys.path.append('tools')
try:
    from message_broker import MessageBroker
    broker = MessageBroker()
    if broker.connect():
        print('✅ RabbitMQ connection successful')
        status = broker.get_broker_status()
        print(f'📊 Broker status: {status[\"connected\"]}')
        broker.disconnect()
        with open('.logs/manager.log', 'a') as f:
            f.write('$(date -Iseconds) [BROKER] RabbitMQ connection test successful\n')
    else:
        print('❌ RabbitMQ connection failed')
        print('💡 Make sure RabbitMQ is running (use: project:start_message_broker)')
        with open('.logs/manager.log', 'a') as f:
            f.write('$(date -Iseconds) [BROKER] RabbitMQ connection test failed\n')
except Exception as e:
    print(f'❌ RabbitMQ connection error: {e}')
    print('💡 Install pika: pip install pika')
    print('💡 Start RabbitMQ: project:start_message_broker')
    with open('.logs/manager.log', 'a') as f:
        f.write('$(date -Iseconds) [BROKER] RabbitMQ connection error: $e\n')
"

# Create manager context file if it doesn't exist
if [ ! -f .agents/manager/context.md ]; then
  cat > .agents/manager/context.md << 'EOF'
# Manager Agent Context

## Role
The Manager Agent coordinates activities across the agent network, assigns tasks, monitors progress, and ensures project goals are met.

## Responsibilities
- Task assignment and delegation
- Resource allocation and optimization
- Progress monitoring and reporting  
- Conflict resolution between agents
- Project planning and timeline management
- Communication facilitation

## Communication Protocols
- Receive completion messages via RabbitMQ manager-queue
- Send task assignments to developer-queue via RabbitMQ
- Archive completed tasks in .comms/completed/ directory
- Maintain status updates in status.json
- Use message_listener.py for real-time message processing

## Decision Making
- Prioritize tasks based on project goals
- Allocate resources efficiently
- Resolve conflicts and dependencies
- Ensure quality standards are met
EOF
fi

# Display confirmation
echo "🤖 MANAGER AGENT INITIALIZED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent ID: $AGENT_ID"
echo "Session ID: $AGENT_SESSION_ID"
echo "Start Time: $AGENT_START_TIME"
echo "Status File: .agents/manager/status.json"
echo "Log File: .logs/manager.log"
echo ""
echo "📋 MANAGER CAPABILITIES:"
echo "  • Task assignment and coordination"
echo "  • Resource allocation"
echo "  • Progress monitoring"
echo "  • Conflict resolution"
echo "  • Project planning"
echo ""
echo "📡 COMMUNICATION CHANNELS:"
echo "  • RabbitMQ manager-queue - Task completion messages"
echo "  • Message listener: .agents/manager/message_listener.py"
echo ""
echo "🎯 READY FOR TASK COORDINATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set prompt context
echo "You are now acting as the Manager Agent for this agent network."
echo "Your role is to coordinate tasks, allocate resources, and monitor progress."
echo "Use the .comms/ directory to communicate with other agents."
```

## Usage
Run this command to initialize the current Claude Code session as a Manager Agent:

```bash
# Make executable and run
chmod +x .claude/commands/become_manager.md
```

## Post-Initialization
After running this command:
1. Start the message listener: `python3 .agents/manager/message_listener.py`
2. Create task assignments using RabbitMQ (project:create_task)
3. Track progress through agent status files and queue monitoring
4. Maintain communication logs in `.logs/manager.log`
5. Use TodoWrite tool to manage and track tasks

## Message Listener
To start receiving task completion messages:
```bash
# Run in a separate terminal or background process
python3 .agents/manager/message_listener.py
```

This listener will:
- Connect to RabbitMQ manager-queue
- Process incoming task completion messages
- Update manager status and archive completed tasks
- Provide real-time feedback on task completions

## Environment Variables Set
- `AGENT_ID`: "manager"
- `AGENT_TYPE`: "manager" 
- `AGENT_START_TIME`: ISO timestamp of initialization
- `AGENT_SESSION_ID`: Unique session identifier

## Files Created
- `.agents/manager/status.json`: Agent status and metadata
- `.agents/manager/context.md`: Role and responsibility documentation
- `.logs/manager.log`: Activity and communication log
- Required directories for agent network operation