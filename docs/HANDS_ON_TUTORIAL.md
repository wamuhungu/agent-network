# Agent Network System - Hands-On Tutorial Guide

## 🎯 What You'll Learn

This tutorial will walk you through setting up and using the Agent Network System step-by-step. You'll learn how to:

- Start MongoDB and RabbitMQ services
- Initialize Manager and Developer agents
- Create and assign tasks
- Monitor real-time communication between agents
- Use the dashboard to track progress
- Troubleshoot common issues

---

## 📋 Prerequisites

Before starting, ensure you have:
- **Docker Desktop** installed and running
- **Python 3.8+** with pip
- **Claude Code** access
- **Terminal/Command Line** access

---

## 🚀 Step-by-Step Tutorial

### Phase 1: System Setup

#### Step 1.1: Start MongoDB Database

**Why**: MongoDB stores agent states, task history, and activity logs.

```bash
# Start MongoDB using Docker
docker run -d \
  --name agent-network-mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=agentpass \
  --restart unless-stopped \
  mongo:7.0
```

**Verify MongoDB is running**:
```bash
docker ps | grep mongodb
# You should see the container running
```

**Test connection**:
```bash
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager
sm = StateManager()
if sm.is_connected():
    print('✅ MongoDB connected successfully')
else:
    print('❌ MongoDB connection failed')
"
```

#### Step 1.2: Start RabbitMQ Message Broker

**Why**: RabbitMQ enables real-time communication between agents.

**In Claude Code terminal, run**:
```bash
project:start_message_broker
```

**What this does**:
- Starts RabbitMQ Docker container
- Creates agent-specific queues (manager-queue, developer-queue)
- Sets up management interface
- Tests connectivity

**Expected output**:
```
🐰 STARTING RABBITMQ MESSAGE BROKER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Docker is available and running
🚀 Creating new RabbitMQ container...
📥 Pulling RabbitMQ image...
✅ RabbitMQ container created and started successfully
⏳ Waiting for RabbitMQ to be ready...
✅ RabbitMQ is ready!
🔧 Initializing agent queues...
✅ Connected to RabbitMQ successfully
📊 Broker status: Connected = True
📬 Queue manager-queue: 0 messages, 0 consumers
📬 Queue developer-queue: 0 messages, 0 consumers
✅ Queue initialization completed

🎉 RABBITMQ MESSAGE BROKER READY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 CONNECTION INFO:
  • Host: localhost
  • AMQP Port: 5672
  • Management UI: http://localhost:15672
  • Username: agent
  • Password: network

📬 AGENT QUEUES:
  • manager-queue: Ready for task completion messages
  • developer-queue: Ready for task assignment messages
```

**Access RabbitMQ Management UI**:
- Open browser: `http://localhost:15672`
- Login: `agent` / `network`
- You should see the queues created

#### Step 1.3: Start the Monitoring Dashboard

**Why**: The dashboard provides real-time monitoring of agents and tasks.

**In a new terminal**:
```bash
cd /path/to/agent-network
python tools/run_dashboard.py
```

**Expected output**:
```
* Running on http://localhost:5000
* Debug mode: on
```

**Access Dashboard**:
- Open browser: `http://localhost:5000`
- You should see the agent monitoring dashboard

---

### Phase 2: Agent Initialization

#### Step 2.1: Initialize Manager Agent

**Open Claude Code** and run:
```bash
project:become_manager
```

**Expected output**:
```
🤖 MANAGER AGENT INITIALIZED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent ID: manager
Session ID: 1640995200_mgr
Start Time: 2024-01-01T10:00:00+00:00
Database: MongoDB (agent_network)
Log File: .logs/manager.log

📋 MANAGER CAPABILITIES:
  • Task assignment and coordination
  • Resource allocation and optimization
  • Progress monitoring via database
  • Conflict resolution
  • Project planning
  • Work request processing

💾 DATABASE INTEGRATION:
  • Agent state in MongoDB
  • Real-time activity logging
  • Centralized task tracking
  • Heartbeat monitoring

📡 COMMUNICATION CHANNELS:
  • RabbitMQ manager-queue
  • Database state synchronization

🎯 READY FOR TASK COORDINATION
```

**Verify in Dashboard**:
- Refresh `http://localhost:5000`
- You should see the Manager agent listed as "Active"

#### Step 2.2: Start Manager Message Listener

**In the same Claude Code terminal**:
```bash
python3 .agents/manager/message_listener.py
```

**Expected output**:
```
🤖 MANAGER MESSAGE LISTENER STARTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Connected to RabbitMQ
✅ Connected to MongoDB
📬 Listening for messages...
Press Ctrl+C to stop
```

**Keep this terminal running** - it's now listening for completed tasks.

#### Step 2.3: Initialize Developer Agent

**Open a NEW Claude Code session** and run:
```bash
project:become_developer
```

**Expected output**:
```
👨‍💻 DEVELOPER AGENT INITIALIZED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent ID: developer
Session ID: 1640995300_dev
Start Time: 2024-01-01T10:05:00+00:00
Database: MongoDB (agent_network)
Log File: .logs/developer.log

🛠️ DEVELOPER CAPABILITIES:
  • Code implementation
  • Software testing and debugging
  • Code review and quality assurance
  • Technical documentation
  • System integration

💾 DATABASE INTEGRATION:
  • Agent state in MongoDB
  • Real-time activity logging
  • Task assignment tracking
  • Work completion reporting

📡 COMMUNICATION CHANNELS:
  • RabbitMQ developer-queue
  • Database state synchronization

🚀 READY FOR DEVELOPMENT TASKS
```

#### Step 2.4: Start Developer Message Listener

**In the developer Claude Code terminal**:
```bash
python3 .agents/developer/message_listener.py
```

**Expected output**:
```
👨‍💻 DEVELOPER MESSAGE LISTENER STARTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Connected to RabbitMQ
✅ Connected to MongoDB
📬 Listening for messages...
Press Ctrl+C to stop
```

**Keep this terminal running** - it's now listening for task assignments.

---

### Phase 3: Task Creation and Assignment

#### Step 3.1: Create Your First Task

**In the Manager Claude Code terminal** (create a new session if needed):
```bash
project:create_task "Create a simple Hello World Python script with unit tests"
```

**Expected output**:
```
📋 CREATING TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task ID: task_20240101_100500_A7F3Kx
Description: Create a simple Hello World Python script with unit tests

💾 TASK CREATED IN DATABASE
✅ Task stored with ID: task_20240101_100500_A7F3Kx
✅ Task assigned to developer queue
✅ Status: assigned

📨 MESSAGE SENT TO DEVELOPER
✅ RabbitMQ message delivered successfully
📊 Queue status: 1 message pending

🎯 TASK ASSIGNMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: task_20240101_100500_A7F3Kx
Assigned to: developer
Priority: normal
Status: assigned
```

#### Step 3.2: Watch Real-Time Communication

**In the Developer Message Listener terminal**, you should immediately see:
```
📨 NEW TASK ASSIGNMENT: task_20240101_100500_A7F3Kx
   From: manager
   Description: Create a simple Hello World Python script with unit tests
   Priority: normal
   Requirements: ['implementation', 'testing', 'documentation']
✅ Task accepted and stored in database
```

**In the Manager Message Listener terminal**, you might see:
```
📊 STATUS UPDATE from developer: working
   Task: task_20240101_100500_A7F3Kx
   Progress: Task started
```

#### Step 3.3: Monitor in Dashboard

**In your browser** (`http://localhost:5000`):
1. Refresh the page
2. You should see:
   - **Agents**: Manager (Active), Developer (Working)
   - **Tasks**: 1 Active task
   - **Recent Activity**: Task assignment logged

---

### Phase 4: Task Implementation

#### Step 4.1: Implement the Task

**In the Developer Claude Code terminal**:
```bash
project:developer_work
```

**This command will**:
- Check for assigned tasks
- Start implementation
- Create the Hello World script
- Write unit tests
- Update progress in database

**Expected output**:
```
👨‍💻 DEVELOPER WORK CYCLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Timestamp: 2024-01-01T10:06:00+00:00

📊 Checking current status...
  Current status: working
  Current task: task_20240101_100500_A7F3Kx

🔄 CURRENTLY WORKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task: task_20240101_100500_A7F3Kx
Description: Create a simple Hello World Python script with unit tests

🎯 IMPLEMENTING TASK...
✅ Created hello_world.py
✅ Created test_hello_world.py
✅ All tests passing
✅ Documentation added

📈 WORK CYCLE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: working
Current task: task_20240101_100500_A7F3Kx
Action: Implementation completed

🔄 Implementation ready. Run: project:complete_task "task_20240101_100500_A7F3Kx"
```

#### Step 4.2: Complete the Task

**In the Developer Claude Code terminal**:
```bash
project:complete_task "task_20240101_100500_A7F3Kx"
```

**Expected output**:
```
✅ TASK COMPLETION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task ID: task_20240101_100500_A7F3Kx
Completed at: 2024-01-01T10:15:00+00:00

📦 DELIVERABLES:
✅ hello_world.py - Python script
✅ test_hello_world.py - Unit tests
✅ README.md - Documentation

💾 COMPLETION STORED IN DATABASE
✅ Task marked as completed
✅ Deliverables logged
✅ Performance metrics recorded

📨 NOTIFICATION SENT TO MANAGER
✅ Completion message sent via RabbitMQ
📊 Manager notified successfully

🎉 TASK COMPLETED SUCCESSFULLY
```

---

### Phase 5: Monitor Task Completion

#### Step 5.1: Manager Receives Completion

**In the Manager Message Listener terminal**, you should see:
```
✅ TASK COMPLETED: task_20240101_100500_A7F3Kx
   Completed by: developer
   Summary: Hello World Python script with unit tests implemented successfully
   Files created: ['hello_world.py', 'test_hello_world.py', 'README.md']
   All tests passing: True
```

#### Step 5.2: Dashboard Updates

**In your browser dashboard** (`http://localhost:5000`):
1. Refresh the page
2. You should now see:
   - **Agents**: Manager (Active), Developer (Ready)
   - **Tasks**: 0 Active tasks, 1 Completed task
   - **Recent Activity**: Task completion logged
   - **Performance**: Completion time metrics

---

### Phase 6: Advanced Operations

#### Step 6.1: Create Multiple Tasks

**Create several tasks to see the system handle workload**:

```bash
# Task 1
project:create_task "Create a simple calculator web app"

# Task 2  
project:create_task "Write a data validation utility"

# Task 3
project:create_task "Implement user authentication system"
```

#### Step 6.2: Enable Auto-Work Mode

**In the Developer Claude Code terminal**:
```bash
project:auto_work
```

**This will**:
- Automatically check for new tasks every 30 seconds
- Pick up tasks immediately when assigned
- Process tasks continuously
- Update dashboard in real-time

**Expected output**:
```
🔄 AUTO WORK MODE ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Checking for new tasks every 30 seconds...
Press Enter to continue or type 'stop' to halt

🔍 WORK CHECK CYCLE #1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Found available task: task_20240101_101000_B8G4Ly
Description: Create a simple calculator web app
Priority: normal

🚀 STARTING WORK...
Status updated to: working

[Implementation happens automatically...]

✅ TASK PICKED UP - STOPPING AUTO CHECK
A task has been assigned. Work on the task then run /auto_work again.
```

#### Step 6.3: Monitor System Performance

**In your dashboard** (`http://localhost:5000`):
- Watch real-time updates as tasks are processed
- Monitor agent status changes
- View performance metrics
- Check task completion rates

---

### Phase 7: Troubleshooting Common Issues

#### Issue 1: RabbitMQ Connection Failed

**Symptoms**: Agents can't connect to message broker

**Solution**:
```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# Restart RabbitMQ if needed
docker restart agent-network-rabbitmq

# Check logs
docker logs agent-network-rabbitmq
```

#### Issue 2: MongoDB Connection Failed

**Symptoms**: Database operations fail

**Solution**:
```bash
# Check if MongoDB is running
docker ps | grep mongodb

# Restart MongoDB if needed
docker restart agent-network-mongodb

# Test connection
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager
sm = StateManager()
print('Connected:' if sm.is_connected() else 'Failed')
"
```

#### Issue 3: Agent Not Responding

**Symptoms**: Agent appears stuck or unresponsive

**Solution**:
```bash
# Check agent status in database
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager
sm = StateManager()
state = sm.get_agent_state('developer')
print(f'Status: {state.get(\"status\")}')
print(f'Last activity: {state.get(\"last_activity\")}')
"

# Restart agent if needed
# Kill existing process and re-run project:become_developer
```

#### Issue 4: Tasks Not Being Assigned

**Symptoms**: Tasks created but not picked up by developer

**Solution**:
```bash
# Check message queue status
python3 -c "
import sys
sys.path.append('tools')
from message_broker import MessageBroker
broker = MessageBroker()
if broker.connect():
    info = broker.get_queue_info('developer-queue')
    print(f'Messages in queue: {info.get(\"messages\")}')
    print(f'Consumers: {info.get(\"consumers\")}')
    broker.disconnect()
"

# Restart developer message listener if no consumers
```

---

### Phase 8: System Shutdown

#### Step 8.1: Stop Agents Gracefully

**In each Claude Code terminal with agents**:
1. Press `Ctrl+C` to stop message listeners
2. Agents will update their status to "stopped" in database

#### Step 8.2: Stop Services

**Stop RabbitMQ**:
```bash
docker stop agent-network-rabbitmq
```

**Stop MongoDB**:
```bash
docker stop agent-network-mongodb
```

**Stop Dashboard**:
- Press `Ctrl+C` in the dashboard terminal

---

## 🎉 Congratulations!

You've successfully:
✅ Set up the complete Agent Network System  
✅ Initialized Manager and Developer agents  
✅ Created and assigned tasks  
✅ Monitored real-time communication  
✅ Completed tasks and tracked progress  
✅ Used the monitoring dashboard  
✅ Troubleshot common issues  

## 🔧 Next Steps

Now that you have the system running, try:

1. **Create Custom Tasks**: Experiment with different types of development tasks
2. **Monitor Performance**: Use the dashboard to track metrics over time
3. **Scale Up**: Run multiple developer agents for parallel work
4. **Integrate Applications**: Use the logbook and web server components
5. **Customize Workflows**: Modify agent behaviors for specific use cases

## 📚 Additional Resources

- **User Guide**: `docs/USER_GUIDE.md` - Comprehensive system documentation
- **API Reference**: `docs/API_REFERENCE.md` - Detailed API documentation
- **Configuration**: `docs/CONFIGURATION.md` - System configuration options
- **Troubleshooting**: `docs/TROUBLESHOOTING.md` - Common issues and solutions

---

**Happy Agent Networking! 🤖✨**