Assign a new task to the developer agent.

Usage: /assign_task [task_id] [description]

This will create a properly formatted task assignment message for the developer agent.

Follow these steps:
1. Create a detailed task specification with:
   - Clear description
   - Specific requirements
   - Acceptance criteria
   - Relevant resources
   - Priority level
   - Deadline (if applicable)
2. Format this as a message using the standard protocol
3. Store the task in MongoDB and publish to RabbitMQ:
   ```python
   import sys
   sys.path.append('/Users/abdelr/Projects/claudecode/agent-network')
   from src.services.database import DatabaseService
   from src.services.message_broker import MessageBroker
   import asyncio
   from datetime import datetime
   
   async def assign_task():
       db = DatabaseService()
       broker = MessageBroker()
       
       task_data = {
           "task_id": "[task_id]",
           "type": "task_assignment",
           "from": "manager",
           "to": "developer", 
           "description": "[description]",
           "requirements": ["..."],
           "priority": "normal",
           "status": "assigned",
           "created_at": datetime.utcnow()
       }
       
       # Store in MongoDB
       await db.tasks.insert_one(task_data)
       
       # Publish to RabbitMQ
       await broker.connect()
       await broker.publish_message("tasks", task_data)
       await broker.close()
       
       print(f"Task {task_data['task_id']} assigned to developer")
   
   asyncio.run(assign_task())
   ```
4. Log the task assignment in the monitoring system