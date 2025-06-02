#!/usr/bin/env python3
"""
State Manager for Agent Network

This module provides centralized state management using MongoDB for the multi-agent system.
It handles persistent storage of agent states, tasks, activity logs, and work requests.
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pymongo import MongoClient, errors
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv
import time
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages persistent state storage for the multi-agent system using MongoDB.
    
    Collections:
    - tasks: Task assignments and their status
    - agent_states: Current state of each agent
    - activity_logs: Agent activity history
    - work_requests: Work request queue
    """
    
    def __init__(self, connection_string: Optional[str] = None, database_name: str = "agent_network"):
        """
        Initialize the StateManager with MongoDB connection.
        
        Args:
            connection_string: MongoDB connection string (defaults to env var or localhost)
            database_name: Name of the database to use
        """
        self.connection_string = connection_string or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.connected = False
        
        # Collection references
        self.tasks: Optional[Collection] = None
        self.agent_states: Optional[Collection] = None
        self.activity_logs: Optional[Collection] = None
        self.work_requests: Optional[Collection] = None
        
        # Connection retry settings
        self.max_retries = 3
        self.retry_delay = 2
        
        # Initialize connection
        self._connect()
    
    def _connect(self) -> bool:
        """
        Establish connection to MongoDB with retry logic.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{self.max_retries})")
                
                # Create MongoDB client with timeout settings
                self.client = MongoClient(
                    self.connection_string,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                
                # Test connection
                self.client.admin.command('ping')
                
                # Set up database and collections
                self.db = self.client[self.database_name]
                self._setup_collections()
                
                self.connected = True
                logger.info(f"Successfully connected to MongoDB at {self.connection_string}")
                return True
                
            except errors.ServerSelectionTimeoutError as e:
                logger.error(f"MongoDB connection timeout: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    
            except errors.ConnectionFailure as e:
                logger.error(f"MongoDB connection failed: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        logger.error("Failed to connect to MongoDB after all retries")
        self.connected = False
        return False
    
    def _setup_collections(self):
        """Set up database collections with indexes."""
        if self.db is None:
            return
        
        # Set up collections
        self.tasks = self.db.tasks
        self.agent_states = self.db.agent_states
        self.activity_logs = self.db.activity_logs
        self.work_requests = self.db.work_requests
        
        # Create indexes for better query performance
        try:
            # Tasks indexes
            self.tasks.create_index("task_id", unique=True)
            self.tasks.create_index("status")
            self.tasks.create_index("assigned_to")
            self.tasks.create_index("created_at")
            
            # Agent states indexes
            self.agent_states.create_index("agent_id", unique=True)
            self.agent_states.create_index("agent_type")
            self.agent_states.create_index("status")
            
            # Activity logs indexes
            self.activity_logs.create_index("agent_id")
            self.activity_logs.create_index("timestamp")
            self.activity_logs.create_index([("timestamp", -1)])  # Descending for recent activities
            
            # Work requests indexes
            self.work_requests.create_index("request_id", unique=True)
            self.work_requests.create_index("status")
            self.work_requests.create_index("created_at")
            
            logger.info("Database collections and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        if not self.connected or not self.client:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except:
            self.connected = False
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from MongoDB")
    
    # Agent State Operations
    
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the current state of an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            Agent state document or None if not found
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return None
        
        try:
            state = self.agent_states.find_one({"agent_id": agent_id})
            return state
        except Exception as e:
            logger.error(f"Error retrieving agent state: {e}")
            return None
    
    def update_agent_state(self, agent_id: str, status: str = None, metadata: Dict[str, Any] = None) -> bool:
        """
        Update an agent's state with status and metadata.
        
        Args:
            agent_id: The ID of the agent
            status: New status for the agent (optional)
            metadata: Additional metadata to update (optional)
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
        
        if not agent_id:
            logger.error("Agent ID is required")
            return False
        
        try:
            # Build update document
            state_update = {}
            
            if status is not None:
                state_update['status'] = status
                
            if metadata:
                state_update.update(metadata)
                
            # Add timestamp
            state_update['last_updated'] = datetime.utcnow()
            state_update['agent_id'] = agent_id
            
            # Log the activity
            self.log_activity(agent_id, "state_update", {
                "status": status,
                "metadata": metadata
            })
            
            # Upsert the agent state
            result = self.agent_states.update_one(
                {"agent_id": agent_id},
                {"$set": state_update},
                upsert=True
            )
            
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Error updating agent state: {e}")
            return False
    
    def get_all_agent_states(self) -> List[Dict[str, Any]]:
        """
        Retrieve states of all agents.
        
        Returns:
            List of agent state documents
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
        
        try:
            states = list(self.agent_states.find())
            return states
        except Exception as e:
            logger.error(f"Error retrieving all agent states: {e}")
            return []
    
    def get_all_agents_status(self) -> Dict[str, str]:
        """
        Get status of all agents in the system.
        
        Returns:
            Dictionary mapping agent_id to status
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return {}
        
        try:
            agents = self.agent_states.find({}, {"agent_id": 1, "status": 1})
            return {agent['agent_id']: agent.get('status', 'unknown') for agent in agents}
        except Exception as e:
            logger.error(f"Error retrieving all agents status: {e}")
            return {}
    
    def set_agent_capabilities(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Store agent capabilities.
        
        Args:
            agent_id: The ID of the agent
            capabilities: List of capability strings
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
        
        if not agent_id:
            logger.error("Agent ID is required")
            return False
            
        if not isinstance(capabilities, list):
            logger.error("Capabilities must be a list")
            return False
        
        try:
            result = self.agent_states.update_one(
                {"agent_id": agent_id},
                {
                    "$set": {
                        "capabilities": capabilities,
                        "capabilities_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            # Log the activity
            self.log_activity(agent_id, "capabilities_updated", {
                "capabilities": capabilities
            })
            
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Error setting agent capabilities: {e}")
            return False
    
    # Task Operations
    
    def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new task.
        
        Args:
            task_data: Task information
            
        Returns:
            Task ID if successful, None otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return None
        
        try:
            # Add timestamps
            task_data['created_at'] = datetime.utcnow()
            task_data['updated_at'] = datetime.utcnow()
            
            # Ensure task_id exists
            if 'task_id' not in task_data:
                task_data['task_id'] = f"task_{int(time.time() * 1000)}"
            
            # Insert task
            result = self.tasks.insert_one(task_data)
            
            if result.acknowledged:
                return task_data['task_id']
            return None
            
        except errors.DuplicateKeyError:
            logger.error(f"Task with ID {task_data.get('task_id')} already exists")
            return None
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            Task document or None if not found
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return None
        
        try:
            task = self.tasks.find_one({"task_id": task_id})
            return task
        except Exception as e:
            logger.error(f"Error retrieving task: {e}")
            return None
    
    def update_task(self, task_id: str, task_update: Dict[str, Any]) -> bool:
        """
        Update a task.
        
        Args:
            task_id: The task ID
            task_update: Dictionary containing task updates
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
        
        try:
            # Add updated timestamp
            task_update['updated_at'] = datetime.utcnow()
            
            result = self.tasks.update_one(
                {"task_id": task_id},
                {"$set": task_update}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Task status to filter by
            
        Returns:
            List of task documents
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
        
        try:
            tasks = list(self.tasks.find({"status": status}))
            return tasks
        except Exception as e:
            logger.error(f"Error retrieving tasks by status: {e}")
            return []
    
    def update_task_state(self, task_id: str, new_state: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Update task status with metadata.
        
        Args:
            task_id: The task ID
            new_state: New state/status for the task
            metadata: Additional metadata (optional)
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
            
        if not task_id:
            logger.error("Task ID is required")
            return False
            
        if not new_state:
            logger.error("New state is required")
            return False
        
        try:
            update_data = {
                "status": new_state,
                "updated_at": datetime.utcnow()
            }
            
            if metadata:
                update_data["metadata"] = metadata
            
            result = self.tasks.update_one(
                {"task_id": task_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # Log the state change
                self.log_activity("system", "task_state_change", {
                    "task_id": task_id,
                    "old_state": "unknown",  # Would need to fetch previous state
                    "new_state": new_state,
                    "metadata": metadata
                })
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating task state: {e}")
            return False
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve task details by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            Task document or None if not found
        """
        # This is an alias for get_task method for consistency
        return self.get_task(task_id)
    
    def get_agent_tasks(self, agent_id: str, states: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get tasks assigned to a specific agent.
        
        Args:
            agent_id: The agent ID
            states: List of states to filter by (optional)
            
        Returns:
            List of task documents
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
            
        if not agent_id:
            logger.error("Agent ID is required")
            return []
        
        try:
            query = {"assigned_to": agent_id}
            
            if states:
                query["status"] = {"$in": states}
            
            tasks = list(self.tasks.find(query).sort("created_at", -1))
            return tasks
            
        except Exception as e:
            logger.error(f"Error retrieving agent tasks: {e}")
            return []
    
    def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """
        Assign a task to an agent.
        
        Args:
            task_id: The task ID
            agent_id: The agent ID to assign the task to
            
        Returns:
            bool: True if assignment successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
            
        if not task_id or not agent_id:
            logger.error("Both task_id and agent_id are required")
            return False
        
        try:
            result = self.tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "assigned_to": agent_id,
                        "assigned_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Log the assignment
                self.log_activity(agent_id, "task_assigned", {
                    "task_id": task_id,
                    "assigned_by": "system"
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error assigning task to agent: {e}")
            return False
    
    # Activity Log Operations
    
    def log_activity(self, agent_id: str, activity_type: str, details: Dict[str, Any]) -> bool:
        """
        Log an agent activity.
        
        Args:
            agent_id: The ID of the agent
            activity_type: Type of activity
            details: Activity details
            
        Returns:
            bool: True if log successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
        
        try:
            log_entry = {
                "agent_id": agent_id,
                "activity_type": activity_type,
                "timestamp": datetime.utcnow(),
                "details": details
            }
            
            result = self.activity_logs.insert_one(log_entry)
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return False
    
    def get_agent_activities(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent activities for an agent.
        
        Args:
            agent_id: The ID of the agent
            limit: Maximum number of activities to retrieve
            
        Returns:
            List of activity log entries
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
        
        try:
            activities = list(
                self.activity_logs
                .find({"agent_id": agent_id})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return activities
        except Exception as e:
            logger.error(f"Error retrieving agent activities: {e}")
            return []
    
    def get_activity_history(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent agent activities (alias for get_agent_activities).
        
        Args:
            agent_id: The ID of the agent
            limit: Maximum number of activities to retrieve
            
        Returns:
            List of activity log entries
        """
        return self.get_agent_activities(agent_id, limit)
    
    def get_system_activity(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get system-wide activity log.
        
        Args:
            limit: Maximum number of activities to retrieve
            
        Returns:
            List of all recent activity log entries
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
        
        try:
            activities = list(
                self.activity_logs
                .find({})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return activities
        except Exception as e:
            logger.error(f"Error retrieving system activities: {e}")
            return []
    
    # Work Request Operations
    
    def create_work_request(self, from_agent: str, to_agent: str, request_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a work request between agents.
        
        Args:
            from_agent: ID of the requesting agent
            to_agent: ID of the target agent
            request_data: Work request details
            
        Returns:
            Request ID if successful, None otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return None
            
        if not from_agent or not to_agent:
            logger.error("Both from_agent and to_agent are required")
            return None
        
        try:
            # Build work request document
            work_request = {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Merge with request_data
            work_request.update(request_data)
            
            # Ensure request_id exists
            if 'request_id' not in work_request:
                work_request['request_id'] = f"req_{int(time.time() * 1000)}"
            
            # Insert request
            result = self.work_requests.insert_one(work_request)
            
            if result.acknowledged:
                # Log the activity
                self.log_activity(from_agent, "work_request_created", {
                    "request_id": work_request['request_id'],
                    "to_agent": to_agent
                })
                return work_request['request_id']
            return None
            
        except Exception as e:
            logger.error(f"Error creating work request: {e}")
            return None
    
    def get_pending_work_requests(self) -> List[Dict[str, Any]]:
        """
        Get all pending work requests.
        
        Returns:
            List of work request documents
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
        
        try:
            requests = list(
                self.work_requests
                .find({"status": "pending"})
                .sort("created_at", 1)
            )
            return requests
        except Exception as e:
            logger.error(f"Error retrieving pending work requests: {e}")
            return []
    
    def get_pending_requests(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get pending requests for a specific agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            List of pending work request documents
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return []
            
        if not agent_id:
            logger.error("Agent ID is required")
            return []
        
        try:
            requests = list(
                self.work_requests
                .find({
                    "to_agent": agent_id,
                    "status": "pending"
                })
                .sort("created_at", 1)
            )
            return requests
        except Exception as e:
            logger.error(f"Error retrieving pending requests for agent: {e}")
            return []
    
    def update_request_status(self, request_id: str, status: str) -> bool:
        """
        Update work request status.
        
        Args:
            request_id: The request ID
            status: New status for the request
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return False
            
        if not request_id or not status:
            logger.error("Both request_id and status are required")
            return False
        
        try:
            result = self.work_requests.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Log the status update
                self.log_activity("system", "work_request_status_update", {
                    "request_id": request_id,
                    "new_status": status
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating request status: {e}")
            return False
    
    # Utility Methods
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database collections.
        
        Returns:
            Dictionary containing collection statistics
        """
        if not self.is_connected():
            logger.error("Not connected to database")
            return {}
        
        try:
            stats = {
                "connected": True,
                "database": self.database_name,
                "collections": {
                    "tasks": {
                        "count": self.tasks.count_documents({}),
                        "pending": self.tasks.count_documents({"status": "pending"}),
                        "in_progress": self.tasks.count_documents({"status": "in_progress"}),
                        "completed": self.tasks.count_documents({"status": "completed"})
                    },
                    "agent_states": {
                        "count": self.agent_states.count_documents({}),
                        "active": self.agent_states.count_documents({"status": "active"}),
                        "working": self.agent_states.count_documents({"status": "working"})
                    },
                    "activity_logs": {
                        "count": self.activity_logs.count_documents({})
                    },
                    "work_requests": {
                        "count": self.work_requests.count_documents({}),
                        "pending": self.work_requests.count_documents({"status": "pending"})
                    }
                }
            }
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"connected": False, "error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    # Initialize StateManager
    state_manager = StateManager()
    
    if state_manager.is_connected():
        print("✅ Successfully connected to MongoDB")
        
        # Get database statistics
        stats = state_manager.get_database_stats()
        print("\n📊 Database Statistics:")
        print(json.dumps(stats, indent=2))
        
        # Test agent state operations
        print("\n🧪 Testing agent state operations...")
        
        # Update developer agent state
        dev_state = {
            "agent_id": "developer",
            "agent_type": "developer",
            "status": "active",
            "capabilities": ["code_implementation", "testing", "debugging"],
            "current_tasks": []
        }
        
        if state_manager.update_agent_state("developer", dev_state):
            print("✅ Successfully updated developer agent state")
        
        # Retrieve agent state
        retrieved_state = state_manager.get_agent_state("developer")
        if retrieved_state:
            print(f"✅ Retrieved agent state: {retrieved_state['agent_id']} - Status: {retrieved_state['status']}")
        
        # Log an activity
        if state_manager.log_activity("developer", "initialization", {"message": "Agent initialized"}):
            print("✅ Successfully logged activity")
        
        # Close connection
        state_manager.disconnect()
        print("\n👋 Disconnected from MongoDB")
    else:
        print("❌ Failed to connect to MongoDB")
        print("💡 Make sure MongoDB is running on localhost:27017")
        print("💡 You can start MongoDB with: brew services start mongodb-community")