# Manager Monitor Command

Monitor system status and process incoming messages for the manager agent.

## Purpose
Performs a single monitoring cycle to check for completion messages, process completed tasks, handle new requirements, and provide status updates with next action guidance.

## Usage
```bash
# Run a single monitoring cycle
project:manager_monitor
```

## Implementation

```python
#!/usr/bin/env python3
import sys
sys.path.append('/Users/abdelr/Projects/claudecode/agent-network')

from src.services.database import DatabaseService
from src.services.message_broker import MessageBroker
import asyncio
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitor_system():
    db = DatabaseService()
    broker = MessageBroker()
    
    timestamp = datetime.utcnow()
    processed_count = 0
    completion_count = 0
    requirement_count = 0
    next_actions = []
    
    print("🔍 MANAGER MONITORING CYCLE")
    print("━" * 50)
    print(f"Timestamp: {timestamp.isoformat()}")
    print()
    
    # Check for completion messages from developer
    print("📋 Checking for completion messages...")
    completions = await db.messages.find({
        "type": "completion",
        "to": "manager",
        "status": {"$in": ["pending", "unread"]}
    }).to_list(None)
    
    if completions:
        for completion in completions:
            print(f"  ✅ Processing: {completion['_id']}")
            task_id = completion.get('task_id', 'unknown')
            
            # Update message status
            await db.messages.update_one(
                {"_id": completion['_id']},
                {"$set": {"status": "processed", "processed_at": timestamp}}
            )
            
            # Update task status if task_id exists
            if task_id != 'unknown':
                await db.tasks.update_one(
                    {"task_id": task_id},
                    {"$set": {"status": "completed", "completed_at": timestamp}}
                )
            
            # Log to monitoring collection
            await db.logs.insert_one({
                "timestamp": timestamp,
                "agent": "manager",
                "action": "process_completion",
                "task_id": task_id
            })
            
            completion_count += 1
            processed_count += 1
    else:
        print("  ℹ️  No completion messages found")
    
    print()
    
    # Check for new requirements
    print("📥 Checking for new requirements...")
    requirements = await db.messages.find({
        "type": "requirement",
        "to": "manager",
        "status": {"$in": ["pending", "unread"]}
    }).to_list(None)
    
    if requirements:
        for requirement in requirements:
            print(f"  📝 New requirement: {requirement['_id']}")
            desc = requirement.get('description', 'No description available')
            print(f"     Summary: {desc[:80]}...")
            
            # Update message status
            await db.messages.update_one(
                {"_id": requirement['_id']},
                {"$set": {"status": "acknowledged", "acknowledged_at": timestamp}}
            )
            
            # Log to monitoring collection
            await db.logs.insert_one({
                "timestamp": timestamp,
                "agent": "manager",
                "action": "new_requirement",
                "requirement_id": str(requirement['_id'])
            })
            
            requirement_count += 1
            processed_count += 1
            next_actions.append(f"Create task from requirement: {requirement['_id']}")
    else:
        print("  ℹ️  No new requirements found")
    
    print()
    
    # Check pending tasks
    print("📊 Checking system status...")
    pending_tasks = await db.tasks.count_documents({"status": {"$in": ["assigned", "in_progress"]}})
    completed_tasks = await db.tasks.count_documents({"status": "completed"})
    
    print(f"  📋 Pending tasks: {pending_tasks}")
    print(f"  ✅ Completed tasks: {completed_tasks}")
    
    # Check developer status
    dev_state = await db.agent_states.find_one({"agent_name": "developer"})
    if dev_state:
        dev_status = dev_state.get('status', 'unknown')
        print(f"  👨‍💻 Developer status: {dev_status}")
        
        if dev_status == "ready" and pending_tasks > 0:
            next_actions.append("Developer ready - tasks available for assignment")
    else:
        print("  ⚠️  Developer status not found")
        next_actions.append("Initialize developer agent")
    
    print()
    
    # Update manager status
    await db.agent_states.update_one(
        {"agent_name": "manager"},
        {
            "$set": {
                "last_activity": timestamp,
                "monitoring": {
                    "last_check": timestamp,
                    "completions_processed": completion_count,
                    "requirements_found": requirement_count,
                    "pending_tasks": pending_tasks,
                    "completed_tasks": completed_tasks
                }
            }
        },
        upsert=True
    )
    print("✅ Manager status updated")
    
    # Log monitoring cycle
    await db.logs.insert_one({
        "timestamp": timestamp,
        "agent": "manager",
        "action": "monitoring_cycle",
        "processed_count": processed_count
    })
    
    print()
    
    # Display summary
    print("📈 MONITORING SUMMARY")
    print("━" * 50)
    print(f"Items processed: {processed_count}")
    print(f"  • Completions: {completion_count}")
    print(f"  • Requirements: {requirement_count}")
    print(f"System status: {pending_tasks} pending, {completed_tasks} completed")
    print()
    
    # Provide next actions guidance
    if next_actions:
        print("🎯 RECOMMENDED NEXT ACTIONS:")
        for i, action in enumerate(next_actions, 1):
            print(f"  {i}. {action}")
        print()
        print("💡 SUGGESTED COMMANDS:")
        
        if requirement_count > 0:
            print('  • project:create_task "[description from requirement]"')
        
        if dev_status == "ready" and pending_tasks > 0:
            print("  • Developer can run: project:developer_work")
        
        if pending_tasks == 0 and requirement_count == 0:
            print("  • System idle - waiting for new requirements")
            print("  • Consider running this monitor again in a few minutes")
    else:
        print("✅ SYSTEM STATUS: All up to date")
        print("💡 Run this monitor again periodically to check for new activity")
    
    print()
    print("🔄 To continue monitoring, run: project:manager_monitor")
    print("━" * 50)
    
    await broker.close()

# Run the monitor
asyncio.run(monitor_system())
```

## Monitoring Functions
1. **Completion Processing**: Finds and processes completion messages from developer in MongoDB
2. **Requirement Detection**: Identifies new requirement messages for task creation
3. **Status Updates**: Updates manager status in MongoDB with current timestamp and metrics
4. **System Overview**: Shows pending/completed task counts and agent status from database
5. **Next Actions**: Provides specific guidance on what to do next

## Output Information
- Timestamp and processing summary
- Count of processed completions and requirements
- System status (pending/completed tasks, developer status)
- Recommended next actions with specific commands
- Guidance for continued monitoring

## Database Collections Used
- `messages`: For completion and requirement messages
- `tasks`: For task status tracking
- `agent_states`: For agent status information
- `logs`: For monitoring activity logs

## Usage Pattern
Run this command periodically (every few minutes) to:
- Process completed work
- Identify new requirements
- Get guidance on next management actions
- Maintain system awareness

## Example Output
```
🔍 MANAGER MONITORING CYCLE
Timestamp: 2024-11-26T14:30:22-08:00

📋 Checking for completion messages...
  ✅ Processing: completion_20241126_143022_B8G4Ly

📥 Checking for new requirements...
  ℹ️  No new requirements found

📊 Checking system status...
  📋 Pending tasks: 2
  ✅ Completed tasks: 1
  👨‍💻 Developer status: ready

🎯 RECOMMENDED NEXT ACTIONS:
  1. Developer ready - tasks available for assignment

💡 SUGGESTED COMMANDS:
  • Developer can run: project:developer_work
```