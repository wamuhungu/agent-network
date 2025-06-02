# Database Maintenance Commands

Suite of commands for MongoDB database maintenance including cleanup, optimization, backup, and restore operations.

## Purpose
Provides essential database maintenance capabilities:
- Clean up old data and logs
- Optimize database performance
- Create backups
- Restore from backups
- Verify database integrity

## Commands

### 1. Database Cleanup
```bash
# Clean up old data (default: older than 30 days)
project:db_cleanup

# Custom retention period
project:db_cleanup --days 7
```

### 2. Database Optimization
```bash
# Optimize all collections
project:db_optimize
```

### 3. Database Backup
```bash
# Create backup with timestamp
project:db_backup

# Backup to specific location
project:db_backup --path /backup/location
```

### 4. Database Restore
```bash
# Restore from latest backup
project:db_restore

# Restore from specific backup
project:db_restore --file backup_20241126_1500.tar.gz
```

## Implementation

```bash
#!/bin/bash

COMMAND="$1"
shift

case "$COMMAND" in
    "cleanup")
        # ================== DATABASE CLEANUP ==================
        RETENTION_DAYS=30
        if [ "$1" = "--days" ] && [ -n "$2" ]; then
            RETENTION_DAYS=$2
        fi
        
        echo "🧹 DATABASE CLEANUP"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Retention Period: $RETENTION_DAYS days"
        echo "Started: $(date +'%Y-%m-%d %H:%M:%S')"
        echo ""
        
        python3 -c "
import sys
from datetime import datetime, timedelta

sys.path.append('tools')

try:
    from state_manager import StateManager
    
    sm = StateManager()
    if not sm.is_connected():
        print('❌ Database connection failed')
        sys.exit(1)
    
    cutoff_date = datetime.utcnow() - timedelta(days=$RETENTION_DAYS)
    
    print('🗑️  CLEANING OLD DATA')
    print('─────────────────────────────────────────────────')
    
    # Clean old activity logs
    print('\\nActivity Logs:')
    old_activities = sm.db.activity_logs.count_documents({
        'timestamp': {'\$lt': cutoff_date}
    })
    
    if old_activities > 0:
        result = sm.db.activity_logs.delete_many({
            'timestamp': {'\$lt': cutoff_date}
        })
        print(f'  Deleted {result.deleted_count} old activity logs')
    else:
        print('  No old activity logs to delete')
    
    # Clean completed tasks older than retention
    print('\\nCompleted Tasks:')
    old_completed = sm.db.tasks.count_documents({
        'status': 'completed',
        'metadata.completed_at': {'\$lt': cutoff_date.isoformat()}
    })
    
    if old_completed > 0:
        # Archive before deleting
        archived_count = 0
        tasks_to_archive = sm.db.tasks.find({
            'status': 'completed',
            'metadata.completed_at': {'\$lt': cutoff_date.isoformat()}
        })
        
        for task in tasks_to_archive:
            sm.db.archived_tasks.replace_one(
                {'_id': task['_id']},
                task,
                upsert=True
            )
            archived_count += 1
        
        # Now delete from main collection
        result = sm.db.tasks.delete_many({
            'status': 'completed',
            'metadata.completed_at': {'\$lt': cutoff_date.isoformat()}
        })
        
        print(f'  Archived {archived_count} tasks')
        print(f'  Deleted {result.deleted_count} completed tasks')
    else:
        print('  No old completed tasks to clean')
    
    # Clean old work requests
    print('\\nWork Requests:')
    old_requests = sm.db.work_requests.count_documents({
        'status': 'completed',
        'updated_at': {'\$lt': cutoff_date}
    })
    
    if old_requests > 0:
        result = sm.db.work_requests.delete_many({
            'status': 'completed',
            'updated_at': {'\$lt': cutoff_date}
        })
        print(f'  Deleted {result.deleted_count} old work requests')
    else:
        print('  No old work requests to delete')
    
    # Database statistics after cleanup
    print('\\n📊 DATABASE STATISTICS')
    print('─────────────────────────────────────────────────')
    
    stats = sm.db.command('dbstats')
    print(f'Database Size: {stats["dataSize"] / (1024*1024):.2f} MB')
    print(f'Storage Size: {stats["storageSize"] / (1024*1024):.2f} MB')
    
    collections = ['agent_states', 'tasks', 'activity_logs', 'work_requests', 'archived_tasks']
    for collection in collections:
        count = sm.db[collection].count_documents({})
        print(f'{collection}: {count} documents')
    
    sm.disconnect()
    print('\\n✅ Cleanup completed successfully')
    
except Exception as e:
    print(f'❌ Error during cleanup: {e}')
    import traceback
    traceback.print_exc()
"
        ;;
        
    "optimize")
        # ================== DATABASE OPTIMIZATION ==================
        echo "⚡ DATABASE OPTIMIZATION"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Started: $(date +'%Y-%m-%d %H:%M:%S')"
        echo ""
        
        python3 -c "
import sys
from datetime import datetime

sys.path.append('tools')

try:
    from state_manager import StateManager
    
    sm = StateManager()
    if not sm.is_connected():
        print('❌ Database connection failed')
        sys.exit(1)
    
    print('🔧 OPTIMIZING COLLECTIONS')
    print('─────────────────────────────────────────────────')
    
    collections = ['agent_states', 'tasks', 'activity_logs', 'work_requests', 'archived_tasks']
    
    for collection_name in collections:
        print(f'\\n{collection_name}:')
        collection = sm.db[collection_name]
        
        # Get current stats
        stats = sm.db.command('collStats', collection_name)
        size_before = stats.get('size', 0) / (1024*1024)
        
        # Reindex collection
        print(f'  • Reindexing...')
        collection.reindex()
        
        # Compact collection (requires admin privileges)
        try:
            sm.db.command('compact', collection_name)
            print(f'  • Compacted')
        except:
            print(f'  • Compact skipped (requires admin)')
        
        # Create/update indexes based on collection
        if collection_name == 'tasks':
            collection.create_index([('task_id', 1)], unique=True)
            collection.create_index([('status', 1)])
            collection.create_index([('assigned_to', 1), ('status', 1)])
            collection.create_index([('created_at', -1)])
            print(f'  • Indexes updated')
            
        elif collection_name == 'activity_logs':
            collection.create_index([('agent_id', 1), ('timestamp', -1)])
            collection.create_index([('activity_type', 1)])
            collection.create_index([('timestamp', -1)])
            print(f'  • Indexes updated')
            
        elif collection_name == 'agent_states':
            collection.create_index([('agent_id', 1)], unique=True)
            collection.create_index([('status', 1)])
            print(f'  • Indexes updated')
        
        # Get stats after optimization
        stats_after = sm.db.command('collStats', collection_name)
        size_after = stats_after.get('size', 0) / (1024*1024)
        
        if size_before > 0:
            reduction = ((size_before - size_after) / size_before) * 100
            print(f'  • Size: {size_before:.2f} MB → {size_after:.2f} MB ({reduction:.1f}% reduction)')
        else:
            print(f'  • Size: {size_after:.2f} MB')
    
    # Run database validation
    print('\\n🔍 DATABASE VALIDATION')
    print('─────────────────────────────────────────────────')
    
    for collection_name in collections:
        result = sm.db.command('validate', collection_name)
        if result.get('valid'):
            print(f'{collection_name}: ✅ Valid')
        else:
            print(f'{collection_name}: ❌ Issues found')
            if 'errors' in result:
                for error in result['errors']:
                    print(f'  - {error}')
    
    sm.disconnect()
    print('\\n✅ Optimization completed successfully')
    
except Exception as e:
    print(f'❌ Error during optimization: {e}')
    import traceback
    traceback.print_exc()
"
        ;;
        
    "backup")
        # ================== DATABASE BACKUP ==================
        BACKUP_PATH="./backups"
        if [ "$1" = "--path" ] && [ -n "$2" ]; then
            BACKUP_PATH="$2"
        fi
        
        # Create backup directory if it doesn't exist
        mkdir -p "$BACKUP_PATH"
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_NAME="agent_network_backup_$TIMESTAMP"
        BACKUP_FILE="$BACKUP_PATH/$BACKUP_NAME.tar.gz"
        
        echo "💾 DATABASE BACKUP"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Backup Name: $BACKUP_NAME"
        echo "Destination: $BACKUP_FILE"
        echo "Started: $(date +'%Y-%m-%d %H:%M:%S')"
        echo ""
        
        # Create temporary directory for dump
        TEMP_DIR="/tmp/$BACKUP_NAME"
        mkdir -p "$TEMP_DIR"
        
        # Dump the database
        echo "📤 Exporting database..."
        mongodump --db agent_network --out "$TEMP_DIR" 2>&1 | grep -v "writing"
        
        if [ $? -eq 0 ]; then
            # Get dump size
            DUMP_SIZE=$(du -sh "$TEMP_DIR" | cut -f1)
            echo "✅ Database exported: $DUMP_SIZE"
            
            # Create metadata file
            cat > "$TEMP_DIR/backup_metadata.json" << EOF
{
    "backup_timestamp": "$(date -Iseconds)",
    "database": "agent_network",
    "collections": ["agent_states", "tasks", "activity_logs", "work_requests", "archived_tasks"],
    "backup_tool": "mongodump",
    "system": "$(uname -s)",
    "notes": "Agent Network backup created by database_maintenance command"
}
EOF
            
            # Compress the backup
            echo "🗜️  Compressing backup..."
            tar -czf "$BACKUP_FILE" -C "/tmp" "$BACKUP_NAME"
            
            if [ $? -eq 0 ]; then
                BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
                echo "✅ Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
                
                # Clean up temporary directory
                rm -rf "$TEMP_DIR"
                
                # List recent backups
                echo ""
                echo "📁 RECENT BACKUPS"
                echo "─────────────────────────────────────────────────"
                ls -lht "$BACKUP_PATH"/agent_network_backup_*.tar.gz 2>/dev/null | head -5 | while read line; do
                    echo "  $line"
                done
            else
                echo "❌ Failed to compress backup"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
        else
            echo "❌ Failed to export database"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
        ;;
        
    "restore")
        # ================== DATABASE RESTORE ==================
        BACKUP_FILE=""
        
        if [ "$1" = "--file" ] && [ -n "$2" ]; then
            BACKUP_FILE="$2"
        else
            # Find latest backup
            BACKUP_FILE=$(ls -t ./backups/agent_network_backup_*.tar.gz 2>/dev/null | head -1)
            if [ -z "$BACKUP_FILE" ]; then
                echo "❌ No backup files found in ./backups/"
                exit 1
            fi
        fi
        
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ Backup file not found: $BACKUP_FILE"
            exit 1
        fi
        
        echo "📥 DATABASE RESTORE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Backup File: $BACKUP_FILE"
        echo "Started: $(date +'%Y-%m-%d %H:%M:%S')"
        echo ""
        echo "⚠️  WARNING: This will replace the current database!"
        echo -n "Continue? (yes/no): "
        read CONFIRM
        
        if [ "$CONFIRM" != "yes" ]; then
            echo "❌ Restore cancelled"
            exit 0
        fi
        
        # Extract backup name from file
        BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
        TEMP_DIR="/tmp/$BACKUP_NAME"
        
        # Extract the backup
        echo "📦 Extracting backup..."
        tar -xzf "$BACKUP_FILE" -C "/tmp"
        
        if [ $? -eq 0 ]; then
            # Check metadata
            if [ -f "$TEMP_DIR/backup_metadata.json" ]; then
                echo "📋 Backup metadata:"
                cat "$TEMP_DIR/backup_metadata.json" | python3 -m json.tool
                echo ""
            fi
            
            # Restore the database
            echo "📥 Restoring database..."
            mongorestore --db agent_network --drop "$TEMP_DIR/agent_network" 2>&1 | grep -v "writing"
            
            if [ $? -eq 0 ]; then
                echo "✅ Database restored successfully"
                
                # Verify restoration
                echo ""
                echo "🔍 VERIFICATION"
                echo "─────────────────────────────────────────────────"
                
                python3 -c "
import sys
sys.path.append('tools')

try:
    from state_manager import StateManager
    
    sm = StateManager()
    if sm.is_connected():
        collections = ['agent_states', 'tasks', 'activity_logs', 'work_requests', 'archived_tasks']
        for collection in collections:
            count = sm.db[collection].count_documents({})
            print(f'{collection}: {count} documents')
        sm.disconnect()
        print('\\n✅ Database verification successful')
    else:
        print('❌ Cannot connect to database')
except Exception as e:
    print(f'❌ Verification error: {e}')
"
                
                # Clean up
                rm -rf "$TEMP_DIR"
            else:
                echo "❌ Failed to restore database"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
        else:
            echo "❌ Failed to extract backup"
            exit 1
        fi
        ;;
        
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        echo "Available commands:"
        echo "  project:db_cleanup    - Clean old data"
        echo "  project:db_optimize   - Optimize database"
        echo "  project:db_backup     - Create backup"
        echo "  project:db_restore    - Restore from backup"
        exit 1
        ;;
esac
```

## Individual Command Files

### db_cleanup.md
```bash
#!/bin/bash
# Wrapper for cleanup command
bash .claude/commands/database_maintenance.sh cleanup "$@"
```

### db_optimize.md
```bash
#!/bin/bash
# Wrapper for optimize command
bash .claude/commands/database_maintenance.sh optimize "$@"
```

### db_backup.md
```bash
#!/bin/bash
# Wrapper for backup command
bash .claude/commands/database_maintenance.sh backup "$@"
```

### db_restore.md
```bash
#!/bin/bash
# Wrapper for restore command
bash .claude/commands/database_maintenance.sh restore "$@"
```

## Features

### Database Cleanup
- Removes old activity logs
- Archives and removes completed tasks
- Cleans completed work requests
- Configurable retention period
- Shows before/after statistics

### Database Optimization
- Reindexes all collections
- Compacts collections (if permitted)
- Updates indexes for performance
- Validates collection integrity
- Reports size reductions

### Database Backup
- Full database export using mongodump
- Compressed tar.gz format
- Includes metadata file
- Automatic timestamping
- Lists recent backups

### Database Restore
- Restores from backup files
- Automatic latest backup detection
- Confirmation prompt for safety
- Drops existing data before restore
- Post-restore verification

## Usage Examples

### Regular Maintenance
```bash
# Weekly cleanup of data older than 30 days
project:db_cleanup

# Monthly optimization
project:db_optimize

# Daily backups
project:db_backup
```

### Custom Operations
```bash
# Aggressive cleanup - keep only 7 days
project:db_cleanup --days 7

# Backup to specific location
project:db_backup --path /mnt/backups

# Restore specific backup
project:db_restore --file backups/agent_network_backup_20241126_1500.tar.gz
```

### Automated Maintenance
```bash
# Crontab entries for automated maintenance

# Daily backup at 2 AM
0 2 * * * cd /path/to/project && project:db_backup

# Weekly cleanup on Sunday at 3 AM
0 3 * * 0 cd /path/to/project && project:db_cleanup

# Monthly optimization on 1st at 4 AM
0 4 1 * * cd /path/to/project && project:db_optimize
```

## Best Practices

1. **Regular Backups**: Run daily or before major changes
2. **Cleanup Schedule**: Weekly cleanup to manage growth
3. **Optimization**: Monthly optimization for performance
4. **Retention Policy**: Balance history needs with storage
5. **Test Restores**: Periodically verify backup integrity

## Storage Estimates

Based on typical usage:
- Activity logs: ~1KB per activity
- Tasks: ~2KB per task
- Agent states: ~1KB per update
- Work requests: ~1KB per request

Monthly storage growth (active system):
- ~10MB for activity logs
- ~5MB for tasks
- ~1MB for agent states
- Total: ~20MB/month

## Recovery Procedures

In case of data loss:
1. Stop all agents immediately
2. Identify latest good backup
3. Run restore command
4. Verify data integrity
5. Restart agents
6. Check system dashboard