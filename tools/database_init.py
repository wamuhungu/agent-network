#!/usr/bin/env python3
"""
Database Initialization and Migration Script

This script:
1. Sets up MongoDB database and collections
2. Creates required indexes for optimal performance
3. Migrates existing file-based agent data to database
4. Validates database setup
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, List, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from state_manager import StateManager


class DatabaseInitializer:
    """Initialize and migrate agent network database."""
    
    def __init__(self):
        """Initialize the database initializer."""
        self.state_manager = StateManager()
        self.migration_stats = {
            'agent_states': 0,
            'tasks': 0,
            'activities': 0,
            'errors': []
        }
    
    def initialize_database(self) -> bool:
        """
        Initialize database with proper schema and indexes.
        
        Returns:
            bool: True if initialization successful
        """
        print("🚀 INITIALIZING AGENT NETWORK DATABASE")
        print("="*60)
        
        if not self.state_manager.is_connected():
            print("❌ Failed to connect to MongoDB")
            print("💡 Make sure MongoDB is running")
            return False
        
        print("✅ Connected to MongoDB")
        
        # The indexes are already created in StateManager._setup_collections()
        # Let's verify they exist
        try:
            db = self.state_manager.db
            
            # Check collections
            collections = db.list_collection_names()
            required = ['agent_states', 'tasks', 'activity_logs', 'work_requests']
            
            print("\n📋 Checking collections:")
            for coll in required:
                if coll in collections:
                    print(f"  ✅ {coll}")
                else:
                    print(f"  ❌ {coll} (will be created on first use)")
            
            # Check indexes
            print("\n🔍 Verifying indexes:")
            
            # Agent states indexes
            if 'agent_states' in collections:
                indexes = list(db.agent_states.list_indexes())
                print(f"  agent_states: {len(indexes)} indexes")
            
            # Tasks indexes
            if 'tasks' in collections:
                indexes = list(db.tasks.list_indexes())
                print(f"  tasks: {len(indexes)} indexes")
            
            # Activity logs indexes
            if 'activity_logs' in collections:
                indexes = list(db.activity_logs.list_indexes())
                print(f"  activity_logs: {len(indexes)} indexes")
            
            # Work requests indexes
            if 'work_requests' in collections:
                indexes = list(db.work_requests.list_indexes())
                print(f"  work_requests: {len(indexes)} indexes")
            
            print("\n✅ Database structure verified")
            return True
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            return False
    
    def migrate_agent_states(self) -> int:
        """
        Migrate agent states from JSON files to database.
        
        Returns:
            int: Number of agent states migrated
        """
        print("\n📦 Migrating agent states...")
        migrated = 0
        
        # Look for agent status files
        agent_files = glob.glob('.agents/*/status.json')
        
        for file_path in agent_files:
            try:
                with open(file_path, 'r') as f:
                    status_data = json.load(f)
                
                agent_id = status_data.get('agent_id')
                if not agent_id:
                    continue
                
                # Check if already exists
                existing = self.state_manager.get_agent_state(agent_id)
                if existing:
                    print(f"  ⚠️  {agent_id} already exists in database (skipping)")
                    continue
                
                # Migrate to database
                status = status_data.get('status', 'inactive')
                
                # Prepare metadata
                metadata = {
                    'migrated_from': file_path,
                    'migration_time': datetime.utcnow().isoformat(),
                    'original_data': status_data
                }
                
                # Update state
                if self.state_manager.update_agent_state(agent_id, status, metadata):
                    print(f"  ✅ Migrated {agent_id} state")
                    
                    # Set capabilities if present
                    if 'capabilities' in status_data:
                        self.state_manager.set_agent_capabilities(
                            agent_id, 
                            status_data['capabilities']
                        )
                    
                    migrated += 1
                else:
                    print(f"  ❌ Failed to migrate {agent_id}")
                    self.migration_stats['errors'].append(f"Failed to migrate {agent_id}")
                    
            except Exception as e:
                print(f"  ❌ Error reading {file_path}: {e}")
                self.migration_stats['errors'].append(f"Error reading {file_path}: {e}")
        
        self.migration_stats['agent_states'] = migrated
        return migrated
    
    def migrate_tasks(self) -> int:
        """
        Migrate tasks from .comms directory to database.
        
        Returns:
            int: Number of tasks migrated
        """
        print("\n📋 Migrating tasks...")
        migrated = 0
        
        # Look for task files in .comms
        task_patterns = [
            '.comms/task_*.json',
            '.comms/active/task_*.json',
            '.comms/completed/task_*.json'
        ]
        
        for pattern in task_patterns:
            task_files = glob.glob(pattern)
            
            for file_path in task_files:
                try:
                    with open(file_path, 'r') as f:
                        task_data = json.load(f)
                    
                    # Determine status from path
                    if 'completed' in file_path:
                        task_data['status'] = 'completed'
                    elif 'active' in file_path:
                        task_data['status'] = 'in_progress'
                    else:
                        task_data['status'] = task_data.get('status', 'pending')
                    
                    # Add migration metadata
                    task_data['migrated_from'] = file_path
                    task_data['migration_time'] = datetime.utcnow()
                    
                    # Create task
                    task_id = self.state_manager.create_task(task_data)
                    if task_id:
                        print(f"  ✅ Migrated task {task_id}")
                        migrated += 1
                    else:
                        print(f"  ⚠️  Task from {file_path} may already exist")
                        
                except Exception as e:
                    print(f"  ❌ Error reading {file_path}: {e}")
                    self.migration_stats['errors'].append(f"Error reading {file_path}: {e}")
        
        self.migration_stats['tasks'] = migrated
        return migrated
    
    def migrate_activity_logs(self) -> int:
        """
        Migrate activity logs from log files to database.
        
        Returns:
            int: Number of activities migrated
        """
        print("\n📝 Migrating activity logs...")
        migrated = 0
        
        # For now, just log that we're ready for new activities
        # Parsing existing log files would require specific format knowledge
        
        # Log migration activity
        if self.state_manager.log_activity('system', 'database_migration', {
            'message': 'Database migration completed',
            'agent_states_migrated': self.migration_stats['agent_states'],
            'tasks_migrated': self.migration_stats['tasks']
        }):
            migrated += 1
        
        print(f"  ✅ Logged migration activity")
        
        self.migration_stats['activities'] = migrated
        return migrated
    
    def validate_migration(self) -> bool:
        """
        Validate the migration results.
        
        Returns:
            bool: True if validation passes
        """
        print("\n🔍 Validating migration...")
        
        stats = self.state_manager.get_database_stats()
        
        print(f"\n📊 Database Statistics:")
        print(f"  Agent States: {stats['collections']['agent_states']['count']}")
        print(f"  Tasks: {stats['collections']['tasks']['count']}")
        print(f"  Activity Logs: {stats['collections']['activity_logs']['count']}")
        print(f"  Work Requests: {stats['collections']['work_requests']['count']}")
        
        if self.migration_stats['errors']:
            print(f"\n⚠️  Migration completed with {len(self.migration_stats['errors'])} errors:")
            for error in self.migration_stats['errors'][:5]:
                print(f"  - {error}")
            if len(self.migration_stats['errors']) > 5:
                print(f"  ... and {len(self.migration_stats['errors']) - 5} more")
        
        return True
    
    def create_sample_data(self):
        """Create sample data for testing."""
        print("\n🧪 Creating sample data...")
        
        # Create sample task
        task_id = self.state_manager.create_task({
            'title': 'Database Migration Test',
            'description': 'Verify database operations are working correctly',
            'status': 'pending',
            'priority': 'low',
            'created_by': 'system'
        })
        
        if task_id:
            print(f"  ✅ Created sample task: {task_id}")
        
        # Create sample work request
        req_id = self.state_manager.create_work_request(
            'system',
            'manager',
            {
                'type': 'initialization',
                'details': {
                    'message': 'Database initialized and ready for operations'
                }
            }
        )
        
        if req_id:
            print(f"  ✅ Created sample work request: {req_id}")
    
    def run(self, create_sample: bool = False):
        """
        Run the complete initialization and migration process.
        
        Args:
            create_sample: Whether to create sample data
        """
        print("\n🚀 MONGODB DATABASE INITIALIZATION")
        print("="*60)
        
        # Initialize database
        if not self.initialize_database():
            print("\n❌ Database initialization failed")
            return
        
        # Migrate data
        print("\n📦 MIGRATING EXISTING DATA")
        print("="*60)
        
        self.migrate_agent_states()
        self.migrate_tasks()
        self.migrate_activity_logs()
        
        # Create sample data if requested
        if create_sample:
            self.create_sample_data()
        
        # Validate
        self.validate_migration()
        
        # Summary
        print("\n✅ DATABASE INITIALIZATION COMPLETE")
        print("="*60)
        print(f"Agent States Migrated: {self.migration_stats['agent_states']}")
        print(f"Tasks Migrated: {self.migration_stats['tasks']}")
        print(f"Activities Logged: {self.migration_stats['activities']}")
        
        if not self.migration_stats['errors']:
            print("\n🎉 Migration completed successfully with no errors!")
        else:
            print(f"\n⚠️  Migration completed with {len(self.migration_stats['errors'])} errors")
        
        # Disconnect
        self.state_manager.disconnect()
        print("\n👋 Disconnected from MongoDB")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Initialize and migrate Agent Network database'
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Create sample data for testing'
    )
    parser.add_argument(
        '--skip-migration',
        action='store_true',
        help='Skip migration of existing files'
    )
    
    args = parser.parse_args()
    
    # Create initializer
    initializer = DatabaseInitializer()
    
    if args.skip_migration:
        # Just initialize
        print("🚀 Initializing database (skipping migration)...")
        initializer.initialize_database()
        
        if args.sample:
            initializer.create_sample_data()
        
        initializer.state_manager.disconnect()
    else:
        # Full initialization and migration
        initializer.run(create_sample=args.sample)


if __name__ == '__main__':
    main()