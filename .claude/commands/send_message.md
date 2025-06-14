Send a message to another agent in the system.

Usage: /send_message [agent_name] [message_type] [content]

This will create a properly formatted message in MongoDB and publish it to RabbitMQ for the specified agent to process.

Follow these steps:
1. Generate a unique message ID
2. Create a message with the required fields:
   - message_id
   - from_agent (your agent name)
   - to_agent (recipient agent name)
   - message_type
   - content (structured based on message type)
   - priority (default: medium)
   - timestamp
3. Store the message in MongoDB and publish to RabbitMQ:
   ```python
   import sys
   sys.path.append('/Users/abdelr/Projects/claudecode/agent-network')
   from src.services.database import DatabaseService
   from src.services.message_broker import MessageBroker
   import asyncio
   from datetime import datetime
   import uuid
   
   async def send_message():
       db = DatabaseService()
       broker = MessageBroker()
       
       message_data = {
           "_id": str(uuid.uuid4()),
           "message_id": str(uuid.uuid4()),
           "from": "[your_agent_name]",
           "to": "[agent_name]",
           "type": "[message_type]",
           "content": "[content]",
           "priority": "medium",
           "status": "pending",
           "created_at": datetime.utcnow(),
           "timestamp": datetime.utcnow()
       }
       
       # Store in MongoDB
       await db.messages.insert_one(message_data)
       
       # Publish to RabbitMQ
       await broker.connect()
       await broker.publish_message("messages", message_data)
       await broker.close()
       
       print(f"Message {message_data['message_id']} sent to {message_data['to']}")
   
   asyncio.run(send_message())
   ```
4. Log the activity to the agent monitoring system