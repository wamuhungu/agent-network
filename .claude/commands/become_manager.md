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
    ".comms/"
  ],
  "log_file": ".logs/manager.log",
  "pid": $$,
  "version": "1.0.0"
}
EOF

# Initialize manager log file
echo "$(date -Iseconds) [INIT] Manager Agent initialized - Session: $AGENT_SESSION_ID" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Manager capabilities: task coordination, resource allocation, progress monitoring" >> .logs/manager.log
echo "$(date -Iseconds) [INFO] Communication channels active: .comms/" >> .logs/manager.log

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
- Monitor .comms/ directory for messages
- Create task assignments in JSON format
- Track task completion and provide feedback
- Maintain status updates in status.json

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
echo "  • .comms/ - Inter-agent messaging"
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
1. Monitor `.comms/` directory for incoming messages
2. Create task assignments using structured JSON format
3. Track progress through agent status files
4. Maintain communication logs in `.logs/manager.log`
5. Use TodoWrite tool to manage and track tasks

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