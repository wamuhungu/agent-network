#!/usr/bin/env python3
"""
Test script for StateManager functionality
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager


def test_state_manager():
    """Test StateManager functionality."""
    print("🧪 Testing StateManager...")
    print("=" * 60)
    
    # Initialize StateManager
    print("\n1️⃣ Initializing StateManager...")
    state_manager = StateManager()
    
    # Check connection
    if state_manager.is_connected():
        print("✅ Connected to MongoDB successfully!")
        
        # Test 1: Update Agent State
        print("\n2️⃣ Testing agent state operations...")
        
        # Update developer agent state
        developer_state = {
            "agent_id": "developer",
            "agent_type": "developer",
            "status": "active",
            "session_id": "test_session_123",
            "capabilities": [
                "code_implementation",
                "software_development",
                "testing_and_debugging",
                "code_review",
                "technical_documentation"
            ],
            "current_tasks": [],
            "completed_tasks": []
        }
        
        if state_manager.update_agent_state("developer", developer_state):
            print("  ✅ Successfully updated developer agent state")
        else:
            print("  ❌ Failed to update developer agent state")
        
        # Update manager agent state
        manager_state = {
            "agent_id": "manager",
            "agent_type": "manager",
            "status": "active",
            "session_id": "test_session_456",
            "capabilities": [
                "task_management",
                "resource_allocation",
                "progress_monitoring"
            ],
            "monitoring": {
                "last_check": datetime.utcnow().isoformat(),
                "pending_tasks": 0,
                "completed_tasks": 0
            }
        }
        
        if state_manager.update_agent_state("manager", manager_state):
            print("  ✅ Successfully updated manager agent state")
        else:
            print("  ❌ Failed to update manager agent state")
        
        # Retrieve agent states
        dev_state = state_manager.get_agent_state("developer")
        if dev_state:
            print(f"  ✅ Retrieved developer state: {dev_state['status']}")
        
        mgr_state = state_manager.get_agent_state("manager")
        if mgr_state:
            print(f"  ✅ Retrieved manager state: {mgr_state['status']}")
        
        # Test 2: Task Operations
        print("\n3️⃣ Testing task operations...")
        
        # Create a task
        task_data = {
            "task_id": "test_task_001",
            "title": "Implement database connection",
            "description": "Create MongoDB connection module for state persistence",
            "status": "pending",
            "priority": "high",
            "assigned_to": "developer",
            "assigned_by": "manager",
            "requirements": [
                "Install pymongo",
                "Create StateManager class",
                "Implement CRUD operations",
                "Add error handling"
            ]
        }
        
        task_id = state_manager.create_task(task_data)
        if task_id:
            print(f"  ✅ Created task: {task_id}")
        else:
            print("  ❌ Failed to create task")
        
        # Retrieve the task
        task = state_manager.get_task("test_task_001")
        if task:
            print(f"  ✅ Retrieved task: {task['title']} (Status: {task['status']})")
        
        # Update task status
        if state_manager.update_task("test_task_001", {"status": "in_progress"}):
            print("  ✅ Updated task status to in_progress")
        
        # Test 3: Activity Logging
        print("\n4️⃣ Testing activity logging...")
        
        # Log some activities
        activities = [
            {
                "agent_id": "developer",
                "activity_type": "task_started",
                "details": {"task_id": "test_task_001", "message": "Started working on database connection"}
            },
            {
                "agent_id": "developer",
                "activity_type": "code_implemented",
                "details": {"file": "state_manager.py", "lines": 350}
            },
            {
                "agent_id": "manager",
                "activity_type": "task_assigned",
                "details": {"task_id": "test_task_001", "assigned_to": "developer"}
            }
        ]
        
        for activity in activities:
            if state_manager.log_activity(
                activity["agent_id"],
                activity["activity_type"],
                activity["details"]
            ):
                print(f"  ✅ Logged {activity['activity_type']} for {activity['agent_id']}")
        
        # Retrieve activities
        dev_activities = state_manager.get_agent_activities("developer", limit=5)
        print(f"  ✅ Retrieved {len(dev_activities)} developer activities")
        
        # Test 4: Work Requests
        print("\n5️⃣ Testing work request operations...")
        
        # Create a work request
        work_request = {
            "request_id": "req_001",
            "requesting_agent": "developer",
            "request_type": "task_assignment",
            "status": "pending",
            "details": {
                "message": "Ready for next task",
                "capabilities": ["python", "testing"]
            }
        }
        
        req_id = state_manager.create_work_request(work_request)
        if req_id:
            print(f"  ✅ Created work request: {req_id}")
        
        # Get pending work requests
        pending_requests = state_manager.get_pending_work_requests()
        print(f"  ✅ Found {len(pending_requests)} pending work requests")
        
        # Test 5: Database Statistics
        print("\n6️⃣ Getting database statistics...")
        stats = state_manager.get_database_stats()
        
        if stats.get("connected"):
            print("  📊 Database Statistics:")
            print(f"     • Database: {stats['database']}")
            print(f"     • Tasks: {stats['collections']['tasks']['count']} total")
            print(f"       - Pending: {stats['collections']['tasks']['pending']}")
            print(f"       - In Progress: {stats['collections']['tasks']['in_progress']}")
            print(f"       - Completed: {stats['collections']['tasks']['completed']}")
            print(f"     • Agent States: {stats['collections']['agent_states']['count']} agents")
            print(f"     • Activity Logs: {stats['collections']['activity_logs']['count']} entries")
            print(f"     • Work Requests: {stats['collections']['work_requests']['count']} total")
        
        # Disconnect
        state_manager.disconnect()
        print("\n✅ Test completed successfully!")
        
    else:
        print("❌ Could not connect to MongoDB")
        print("\n📋 To use the StateManager, you need to:")
        print("1. Install MongoDB:")
        print("   - macOS: brew install mongodb-community")
        print("   - Ubuntu: sudo apt-get install mongodb")
        print("   - Windows: Download from mongodb.com")
        print("\n2. Start MongoDB:")
        print("   - macOS: brew services start mongodb-community")
        print("   - Ubuntu: sudo systemctl start mongodb")
        print("   - Windows: Run mongod.exe")
        print("\n3. Alternatively, use MongoDB Atlas (cloud):")
        print("   - Create a free cluster at mongodb.com/atlas")
        print("   - Set MONGODB_URI environment variable with connection string")
        
        # Show fallback JSON file approach
        print("\n💡 Alternative: Using JSON file storage (fallback mode)")
        print("=" * 60)
        demonstrate_json_fallback()


def demonstrate_json_fallback():
    """Demonstrate JSON file-based state storage as fallback."""
    import json
    
    # Create state directory
    state_dir = ".state"
    os.makedirs(state_dir, exist_ok=True)
    
    # Agent state file
    agent_state_file = os.path.join(state_dir, "agent_states.json")
    
    # Load or create agent states
    if os.path.exists(agent_state_file):
        with open(agent_state_file, 'r') as f:
            agent_states = json.load(f)
    else:
        agent_states = {}
    
    # Update developer state
    agent_states["developer"] = {
        "agent_id": "developer",
        "agent_type": "developer",
        "status": "active",
        "last_updated": datetime.utcnow().isoformat(),
        "current_tasks": []
    }
    
    # Save state
    with open(agent_state_file, 'w') as f:
        json.dump(agent_states, f, indent=2)
    
    print(f"✅ Created JSON-based state file: {agent_state_file}")
    print(f"📄 Agent states saved: {list(agent_states.keys())}")
    
    # Show sample state
    print("\n📋 Sample agent state (JSON format):")
    print(json.dumps(agent_states["developer"], indent=2))


if __name__ == "__main__":
    test_state_manager()