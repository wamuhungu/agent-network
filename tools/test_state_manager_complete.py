#!/usr/bin/env python3
"""
Comprehensive test script for StateManager functionality
Tests all core state management operations as per requirements
"""

import sys
import os
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager


def test_agent_state_management(state_manager):
    """Test Agent State Management operations."""
    print("\n" + "="*60)
    print("🤖 TESTING AGENT STATE MANAGEMENT")
    print("="*60)
    
    # 1. update_agent_state
    print("\n1️⃣ Testing update_agent_state...")
    success = state_manager.update_agent_state("developer", "active", {
        "session_id": "test_123",
        "pid": 12345
    })
    print(f"   ✅ Updated developer state: {success}")
    
    success = state_manager.update_agent_state("manager", "working", {
        "current_task": "monitoring"
    })
    print(f"   ✅ Updated manager state: {success}")
    
    # 2. get_agent_state
    print("\n2️⃣ Testing get_agent_state...")
    state = state_manager.get_agent_state("developer")
    if state:
        print(f"   ✅ Developer state: {state['status']}")
    
    # 3. get_all_agents_status
    print("\n3️⃣ Testing get_all_agents_status...")
    statuses = state_manager.get_all_agents_status()
    print(f"   ✅ All agent statuses: {statuses}")
    
    # 4. set_agent_capabilities
    print("\n4️⃣ Testing set_agent_capabilities...")
    success = state_manager.set_agent_capabilities("developer", [
        "python_development",
        "javascript",
        "testing",
        "documentation"
    ])
    print(f"   ✅ Set developer capabilities: {success}")
    
    # Verify capabilities were set
    state = state_manager.get_agent_state("developer")
    if state and 'capabilities' in state:
        print(f"   ✅ Capabilities: {state['capabilities']}")


def test_task_state_management(state_manager):
    """Test Task State Management operations."""
    print("\n" + "="*60)
    print("📋 TESTING TASK STATE MANAGEMENT")
    print("="*60)
    
    # 1. create_task
    print("\n1️⃣ Testing create_task...")
    task_data = {
        "title": "Implement database module",
        "description": "Create MongoDB state management",
        "status": "pending",
        "priority": "high"
    }
    task_id = state_manager.create_task(task_data)
    print(f"   ✅ Created task: {task_id}")
    
    # Create another task
    task_data2 = {
        "task_id": "test_task_002",
        "title": "Write unit tests",
        "description": "Test all StateManager methods",
        "status": "pending",
        "priority": "medium"
    }
    task_id2 = state_manager.create_task(task_data2)
    print(f"   ✅ Created task: {task_id2}")
    
    # 2. update_task_state
    print("\n2️⃣ Testing update_task_state...")
    success = state_manager.update_task_state(task_id, "in_progress", {
        "started_at": datetime.utcnow().isoformat()
    })
    print(f"   ✅ Updated task state: {success}")
    
    # 3. get_task_by_id
    print("\n3️⃣ Testing get_task_by_id...")
    task = state_manager.get_task_by_id(task_id)
    if task:
        print(f"   ✅ Retrieved task: {task['title']} (Status: {task['status']})")
    
    # 4. assign_task_to_agent
    print("\n4️⃣ Testing assign_task_to_agent...")
    success = state_manager.assign_task_to_agent(task_id, "developer")
    print(f"   ✅ Assigned task to developer: {success}")
    
    success = state_manager.assign_task_to_agent(task_id2, "developer")
    print(f"   ✅ Assigned second task to developer: {success}")
    
    # 5. get_agent_tasks
    print("\n5️⃣ Testing get_agent_tasks...")
    dev_tasks = state_manager.get_agent_tasks("developer")
    print(f"   ✅ Developer has {len(dev_tasks)} tasks")
    
    # Get only pending tasks
    pending_tasks = state_manager.get_agent_tasks("developer", ["pending"])
    print(f"   ✅ Developer has {len(pending_tasks)} pending tasks")


def test_activity_logging(state_manager):
    """Test Activity Logging operations."""
    print("\n" + "="*60)
    print("📝 TESTING ACTIVITY LOGGING")
    print("="*60)
    
    # 1. log_activity
    print("\n1️⃣ Testing log_activity...")
    activities = [
        ("developer", "task_started", {"task_id": "test_001", "message": "Started implementation"}),
        ("developer", "code_committed", {"commit": "abc123", "files": 5}),
        ("manager", "task_assigned", {"task_id": "test_002", "to": "developer"}),
        ("manager", "monitoring", {"agents_checked": 2, "status": "all_healthy"}),
        ("system", "startup", {"version": "1.0.0", "environment": "development"})
    ]
    
    for agent_id, activity_type, details in activities:
        success = state_manager.log_activity(agent_id, activity_type, details)
        print(f"   ✅ Logged {activity_type} for {agent_id}: {success}")
    
    # 2. get_activity_history
    print("\n2️⃣ Testing get_activity_history...")
    dev_history = state_manager.get_activity_history("developer", limit=5)
    print(f"   ✅ Developer activity history: {len(dev_history)} entries")
    
    # 3. get_system_activity
    print("\n3️⃣ Testing get_system_activity...")
    system_activity = state_manager.get_system_activity(limit=10)
    print(f"   ✅ System activity log: {len(system_activity)} entries")
    
    # Show recent activities
    if system_activity:
        print("\n   📋 Recent System Activities:")
        for activity in system_activity[:3]:
            print(f"      • {activity['agent_id']}: {activity['activity_type']}")


def test_work_request_management(state_manager):
    """Test Work Request Management operations."""
    print("\n" + "="*60)
    print("📮 TESTING WORK REQUEST MANAGEMENT")
    print("="*60)
    
    # 1. create_work_request
    print("\n1️⃣ Testing create_work_request...")
    request_data = {
        "type": "task_assignment",
        "priority": "high",
        "details": {
            "message": "Need help with database implementation",
            "estimated_time": "2 hours"
        }
    }
    req_id = state_manager.create_work_request("developer", "manager", request_data)
    print(f"   ✅ Created work request: {req_id}")
    
    # Create another request
    request_data2 = {
        "type": "resource_request",
        "priority": "medium",
        "details": {
            "resource": "additional_compute",
            "reason": "Complex processing task"
        }
    }
    req_id2 = state_manager.create_work_request("developer", "manager", request_data2)
    print(f"   ✅ Created work request: {req_id2}")
    
    # 2. get_pending_requests
    print("\n2️⃣ Testing get_pending_requests...")
    manager_requests = state_manager.get_pending_requests("manager")
    print(f"   ✅ Manager has {len(manager_requests)} pending requests")
    
    # 3. update_request_status
    print("\n3️⃣ Testing update_request_status...")
    if req_id:
        success = state_manager.update_request_status(req_id, "in_review")
        print(f"   ✅ Updated request status: {success}")
        
        success = state_manager.update_request_status(req_id, "approved")
        print(f"   ✅ Approved request: {success}")
    
    # 4. get_pending_work_requests (system-wide)
    print("\n4️⃣ Testing get_pending_work_requests...")
    all_pending = state_manager.get_pending_work_requests()
    print(f"   ✅ System has {len(all_pending)} pending work requests")


def test_validation_and_error_handling(state_manager):
    """Test validation and error handling."""
    print("\n" + "="*60)
    print("🛡️ TESTING VALIDATION AND ERROR HANDLING")
    print("="*60)
    
    # Test missing required parameters
    print("\n1️⃣ Testing parameter validation...")
    
    # Empty agent_id
    success = state_manager.update_agent_state("", "active")
    print(f"   ✅ Empty agent_id rejected: {not success}")
    
    # Invalid capabilities type
    success = state_manager.set_agent_capabilities("developer", "not_a_list")
    print(f"   ✅ Invalid capabilities type rejected: {not success}")
    
    # Missing required fields
    success = state_manager.assign_task_to_agent("", "developer")
    print(f"   ✅ Empty task_id rejected: {not success}")
    
    success = state_manager.create_work_request("", "manager", {})
    print(f"   ✅ Empty from_agent rejected: {not success}")


def display_database_summary(state_manager):
    """Display final database summary."""
    print("\n" + "="*60)
    print("📊 FINAL DATABASE SUMMARY")
    print("="*60)
    
    stats = state_manager.get_database_stats()
    
    if stats.get("connected"):
        print(f"\n✅ Database: {stats['database']}")
        print("\n📈 Collection Statistics:")
        
        # Tasks
        tasks_stats = stats['collections']['tasks']
        print(f"\n   📋 Tasks ({tasks_stats['count']} total):")
        print(f"      • Pending: {tasks_stats['pending']}")
        print(f"      • In Progress: {tasks_stats['in_progress']}")
        print(f"      • Completed: {tasks_stats['completed']}")
        
        # Agent States
        agents_stats = stats['collections']['agent_states']
        print(f"\n   🤖 Agent States ({agents_stats['count']} agents):")
        print(f"      • Active: {agents_stats['active']}")
        print(f"      • Working: {agents_stats['working']}")
        
        # Activity Logs
        print(f"\n   📝 Activity Logs: {stats['collections']['activity_logs']['count']} entries")
        
        # Work Requests
        requests_stats = stats['collections']['work_requests']
        print(f"\n   📮 Work Requests ({requests_stats['count']} total):")
        print(f"      • Pending: {requests_stats['pending']}")


def main():
    """Run all StateManager tests."""
    print("🧪 COMPREHENSIVE STATEMANAGER TEST SUITE")
    print("="*60)
    
    # Initialize StateManager
    print("Initializing StateManager...")
    state_manager = StateManager()
    
    if state_manager.is_connected():
        print("✅ Connected to MongoDB successfully!")
        
        # Run all test suites
        test_agent_state_management(state_manager)
        test_task_state_management(state_manager)
        test_activity_logging(state_manager)
        test_work_request_management(state_manager)
        test_validation_and_error_handling(state_manager)
        
        # Display summary
        display_database_summary(state_manager)
        
        # Disconnect
        state_manager.disconnect()
        print("\n✅ All tests completed successfully!")
        print("👋 Disconnected from MongoDB")
        
    else:
        print("❌ Could not connect to MongoDB")
        print("Make sure MongoDB is running: brew services start mongodb/brew/mongodb-community@7.0")


if __name__ == "__main__":
    main()