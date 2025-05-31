# Become Developer Agent

Initialize this Claude Code instance as a Developer Agent in the agent network.

## Purpose
Transforms the current Claude Code session into a Developer Agent with:
- Agent identity and environment setup
- Status tracking and logging capabilities
- Task implementation capabilities
- Code development and testing responsibilities

## Implementation

```bash
# Set agent identity environment variables
export AGENT_ID="developer"
export AGENT_TYPE="developer"
export AGENT_START_TIME=$(date -Iseconds)
export AGENT_SESSION_ID=$(date +%s)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)

# Create necessary directories if they don't exist
mkdir -p .agents/manager
mkdir -p .agents/developer
mkdir -p .logs
mkdir -p .comms/completed
mkdir -p .comms/processed

# Create developer status file
cat > .agents/developer/status.json << EOF
{
  "agent_id": "developer",
  "agent_type": "developer",
  "status": "active",
  "session_id": "$AGENT_SESSION_ID",
  "start_time": "$AGENT_START_TIME",
  "last_activity": "$AGENT_START_TIME",
  "capabilities": [
    "code_implementation",
    "software_development",
    "testing_and_debugging",
    "code_review",
    "technical_documentation",
    "system_integration"
  ],
  "current_tasks": [],
  "completed_tasks": [],
  "communication_channels": [
    "rabbitmq:developer-queue"
  ],
  "message_broker": {
    "enabled": true,
    "queue_name": "developer-queue",
    "status": "initializing"
  },
  "log_file": ".logs/developer.log",
  "pid": $$,
  "version": "1.0.0",
  "development_tools": [
    "python",
    "javascript", 
    "html_css",
    "flask",
    "git"
  ]
}
EOF

# Initialize developer log file
echo "$(date -Iseconds) [INIT] Developer Agent initialized - Session: $AGENT_SESSION_ID" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Developer capabilities: code implementation, testing, debugging, documentation" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Communication channels active: RabbitMQ developer-queue" >> .logs/developer.log
echo "$(date -Iseconds) [INFO] Development tools ready: Python, JavaScript, HTML/CSS, Flask, Git" >> .logs/developer.log

# Initialize RabbitMQ connection and start listening
echo "$(date -Iseconds) [BROKER] Initializing RabbitMQ connection..." >> .logs/developer.log

# Create developer message listener script
cat > .agents/developer/message_listener.py << 'EOF'
#!/usr/bin/env python3
"""
Developer Agent RabbitMQ Message Listener

Listens for task assignment messages on the developer-queue and processes them.
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
        logging.FileHandler('.logs/developer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def handle_task_assignment(message):
    """
    Handle incoming task assignment messages.
    
    Args:
        message: Parsed JSON message from manager
    """
    try:
        message_type = message.get('message_type', 'unknown')
        task_id = message.get('task_id', 'unknown')
        from_agent = message.get('from_agent', 'unknown')
        
        logger.info(f"Received {message_type} from {from_agent} for task {task_id}")
        
        if message_type == 'task_assignment':
            # Process task assignment
            task = message.get('task', {})
            priority = message.get('priority', 'medium')
            
            # Update developer status
            update_developer_status(message)
            
            # Archive task assignment
            archive_task_assignment(message)
            
            # Log assignment
            logger.info(f"Task {task_id} assigned by {from_agent}")
            
            print(f"📋 NEW TASK ASSIGNED: {task_id}")
            print(f"   Assigned by: {from_agent}")
            print(f"   Priority: {priority}")
            
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
            
            print("   📋 Use project:developer_work to begin implementation")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def update_developer_status(task_message):
    """Update developer status with new task assignment."""
    try:
        with open('.agents/developer/status.json', 'r') as f:
            status = json.load(f)
        
        # Add to current tasks
        task_info = {
            'task_id': task_message.get('task_id'),
            'assigned_by': task_message.get('from_agent'),
            'assigned_at': task_message.get('timestamp'),
            'priority': task_message.get('priority', 'medium'),
            'description': task_message.get('task', {}).get('description', '')
        }
        
        status['current_tasks'].append(task_info)
        status['last_activity'] = datetime.now().isoformat()
        status['status'] = 'working'
        
        # Update message broker status
        if 'message_broker' in status:
            status['message_broker']['status'] = 'connected'
        
        with open('.agents/developer/status.json', 'w') as f:
            json.dump(status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error updating developer status: {e}")

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

def main():
    """Main developer message listener."""
    print("👨‍💻 DEVELOPER MESSAGE LISTENER STARTING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # Create broker connection
        broker = MessageBroker()
        
        if not broker.connect():
            logger.error("Failed to connect to RabbitMQ")
            return 1
        
        logger.info("Connected to RabbitMQ successfully")
        print("✅ Connected to RabbitMQ")
        print("📬 Listening for task assignment messages...")
        print("Press Ctrl+C to stop")
        print("")
        
        # Start consuming messages
        broker.start_consuming(MessageBroker.DEVELOPER_QUEUE, handle_task_assignment)
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping developer message listener...")
            logger.info("Developer message listener stopped by user")
            
    except Exception as e:
        logger.error(f"Developer listener error: {e}")
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
chmod +x .agents/developer/message_listener.py

# Test RabbitMQ connection
echo "$(date -Iseconds) [BROKER] Testing RabbitMQ connection..." >> .logs/developer.log

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
        with open('.logs/developer.log', 'a') as f:
            f.write('$(date -Iseconds) [BROKER] RabbitMQ connection test successful\n')
    else:
        print('❌ RabbitMQ connection failed')
        print('💡 Make sure RabbitMQ is running (use: project:start_message_broker)')
        with open('.logs/developer.log', 'a') as f:
            f.write('$(date -Iseconds) [BROKER] RabbitMQ connection test failed\n')
except Exception as e:
    print(f'❌ RabbitMQ connection error: {e}')
    print('💡 Install pika: pip install pika')
    print('💡 Start RabbitMQ: project:start_message_broker')
    with open('.logs/developer.log', 'a') as f:
        f.write('$(date -Iseconds) [BROKER] RabbitMQ connection error: $e\n')
"

# Create developer context file if it doesn't exist
if [ ! -f .agents/developer/context.md ]; then
  cat > .agents/developer/context.md << 'EOF'
# Developer Agent Context

## Role
The Developer Agent implements code based on specifications, tests and debugs implementations, performs code reviews, and creates technical documentation.

## Responsibilities
- Code implementation and development
- Software testing and debugging
- Code review and quality assurance
- Technical documentation creation
- System integration and deployment
- Performance optimization

## Communication Protocols
- Receive task assignments via RabbitMQ developer-queue
- Send completion messages to manager-queue via RabbitMQ
- Archive active tasks in .comms/active/ directory
- Request clarification when requirements are unclear
- Report blockers and technical challenges
- Use message_listener.py for real-time message processing

## Development Standards
- Follow project coding standards in docs/standards/
- Write clean, maintainable, and well-documented code
- Implement proper error handling and validation
- Ensure responsive design for web components
- Use existing libraries and frameworks when possible

## Technical Stack
- Python (Flask, backend development)
- JavaScript (frontend functionality)
- HTML/CSS (user interfaces)
- Git (version control)
- Testing frameworks as needed
EOF
fi

# Display confirmation
echo "👨‍💻 DEVELOPER AGENT INITIALIZED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent ID: $AGENT_ID"
echo "Session ID: $AGENT_SESSION_ID"
echo "Start Time: $AGENT_START_TIME"
echo "Status File: .agents/developer/status.json"
echo "Log File: .logs/developer.log"
echo ""
echo "🛠️  DEVELOPER CAPABILITIES:"
echo "  • Code implementation"
echo "  • Software testing and debugging"
echo "  • Code review and quality assurance"
echo "  • Technical documentation"
echo "  • System integration"
echo ""
echo "⚙️  DEVELOPMENT TOOLS:"
echo "  • Python (Flask)"
echo "  • JavaScript"
echo "  • HTML/CSS"
echo "  • Git version control"
echo ""
echo "📡 COMMUNICATION CHANNELS:"
echo "  • RabbitMQ developer-queue - Task assignment messages"
echo "  • Message listener: .agents/developer/message_listener.py"
echo ""
echo "🚀 READY FOR DEVELOPMENT TASKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set prompt context
echo "You are now acting as the Developer Agent for this agent network."
echo "Your role is to implement code, test functionality, and create technical solutions."
echo "Monitor the .comms/ directory for task assignments from the Manager Agent."
```

## Usage
Run this command to initialize the current Claude Code session as a Developer Agent:

```bash
# Make executable and run
chmod +x .claude/commands/become_developer.md
```

## Post-Initialization
After running this command:
1. Start the message listener: `python3 .agents/developer/message_listener.py`
2. Implement code following project standards
3. Provide progress updates during development
4. Send completion notifications using RabbitMQ (project:complete_task)
5. Use TodoWrite tool to track implementation tasks

## Message Listener
To start receiving task assignment messages:
```bash
# Run in a separate terminal or background process
python3 .agents/developer/message_listener.py
```

This listener will:
- Connect to RabbitMQ developer-queue
- Process incoming task assignment messages
- Update developer status and archive active tasks
- Provide real-time feedback on new assignments

## Environment Variables Set
- `AGENT_ID`: "developer"
- `AGENT_TYPE`: "developer"
- `AGENT_START_TIME`: ISO timestamp of initialization
- `AGENT_SESSION_ID`: Unique session identifier

## Files Created
- `.agents/developer/status.json`: Agent status and metadata
- `.agents/developer/context.md`: Role and responsibility documentation
- `.logs/developer.log`: Activity and development log
- Required directories for agent network operation

## Development Workflow
1. Receive task assignments via RabbitMQ developer-queue
2. Break down tasks using TodoWrite tool
3. Implement solutions following coding standards
4. Test implementations thoroughly
5. Document code and provide completion updates via RabbitMQ
6. Handle any clarifications or iterations needed