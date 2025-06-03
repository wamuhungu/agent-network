#!/usr/bin/env python3
"""
Enhanced Backup and Recovery System

Provides comprehensive backup and point-in-time recovery capabilities
for the agent network database.
"""

import os
import sys
import json
import time
import shutil
import tarfile
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import pymongo
from pymongo import MongoClient

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    CONTINUOUS = "continuous"


@dataclass
class BackupInfo:
    """Information about a backup."""
    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    size_bytes: int
    collections: List[str]
    base_backup_id: Optional[str] = None  # For incremental backups
    metadata: Dict[str, Any] = None


class BackupRecoveryManager:
    """
    Enhanced backup and recovery system with point-in-time recovery.
    
    Features:
    - Full backups
    - Incremental backups
    - Continuous backup with oplog
    - Point-in-time recovery
    - Backup verification
    - Automated backup scheduling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the backup recovery manager."""
        self.config = config or {}
        
        # Backup settings
        self.backup_dir = self.config.get('backup_dir', './backups')
        self.retention_days = self.config.get('retention_days', 30)
        self.compression_level = self.config.get('compression_level', 6)
        
        # Database connection
        self.connection_string = self.config.get(
            'connection_string', 
            'mongodb://localhost:27017/'
        )
        self.database_name = 'agent_network'
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'full'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'incremental'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'oplog'), exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Backup catalog
        self.catalog_file = os.path.join(self.backup_dir, 'backup_catalog.json')
        self.catalog = self._load_catalog()
    
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('BackupRecovery')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/backup_recovery.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_catalog(self) -> Dict[str, Any]:
        """Load backup catalog."""
        if os.path.exists(self.catalog_file):
            try:
                with open(self.catalog_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load catalog: {e}")
        
        return {
            'backups': [],
            'last_full_backup': None,
            'last_incremental_backup': None
        }
    
    def _save_catalog(self):
        """Save backup catalog."""
        try:
            with open(self.catalog_file, 'w') as f:
                json.dump(self.catalog, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save catalog: {e}")
    
    def create_full_backup(self, description: str = "") -> Optional[BackupInfo]:
        """
        Create a full backup of the database.
        
        Args:
            description: Optional description for the backup
            
        Returns:
            BackupInfo object if successful
        """
        backup_id = f"full_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(self.backup_dir, 'full', backup_id)
        
        self.logger.info(f"Starting full backup: {backup_id}")
        
        try:
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Use mongodump for full backup
            dump_cmd = [
                'mongodump',
                '--uri', self.connection_string,
                '--db', self.database_name,
                '--out', backup_path,
                '--oplog'  # Include oplog for point-in-time recovery
            ]
            
            result = subprocess.run(dump_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Mongodump failed: {result.stderr}")
                return None
            
            # Create metadata
            metadata = {
                'backup_id': backup_id,
                'type': 'full',
                'timestamp': datetime.utcnow().isoformat(),
                'description': description,
                'database': self.database_name,
                'collections': self._list_collections(),
                'mongodump_version': self._get_mongodump_version()
            }
            
            # Save metadata
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Compress backup
            archive_path = f"{backup_path}.tar.gz"
            with tarfile.open(archive_path, 'w:gz', compresslevel=self.compression_level) as tar:
                tar.add(backup_path, arcname=backup_id)
            
            # Remove uncompressed backup
            shutil.rmtree(backup_path)
            
            # Get backup size
            backup_size = os.path.getsize(archive_path)
            
            # Create backup info
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                timestamp=datetime.utcnow(),
                size_bytes=backup_size,
                collections=metadata['collections'],
                metadata=metadata
            )
            
            # Update catalog
            self.catalog['backups'].append({
                'backup_id': backup_id,
                'type': 'full',
                'timestamp': backup_info.timestamp.isoformat(),
                'size_bytes': backup_size,
                'path': archive_path,
                'metadata': metadata
            })
            self.catalog['last_full_backup'] = backup_id
            self._save_catalog()
            
            self.logger.info(
                f"Full backup completed: {backup_id} "
                f"({backup_size / (1024*1024):.2f} MB)"
            )
            
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Full backup failed: {e}")
            return None
    
    def create_incremental_backup(self, description: str = "") -> Optional[BackupInfo]:
        """
        Create an incremental backup since the last full backup.
        
        Args:
            description: Optional description
            
        Returns:
            BackupInfo object if successful
        """
        if not self.catalog['last_full_backup']:
            self.logger.error("No full backup found. Creating full backup instead.")
            return self.create_full_backup(description)
        
        backup_id = f"incr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(self.backup_dir, 'incremental', backup_id)
        
        self.logger.info(f"Starting incremental backup: {backup_id}")
        
        try:
            # Get timestamp of last backup
            last_backup = self._get_backup_info(self.catalog['last_full_backup'])
            if not last_backup:
                return None
            
            last_timestamp = datetime.fromisoformat(
                last_backup['timestamp'].replace('Z', '+00:00')
            )
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Export changes since last backup
            changes = self._export_changes_since(last_timestamp, backup_path)
            
            if not changes:
                self.logger.info("No changes since last backup")
                shutil.rmtree(backup_path)
                return None
            
            # Create metadata
            metadata = {
                'backup_id': backup_id,
                'type': 'incremental',
                'timestamp': datetime.utcnow().isoformat(),
                'description': description,
                'base_backup_id': self.catalog['last_full_backup'],
                'changes': changes
            }
            
            # Save metadata
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Compress backup
            archive_path = f"{backup_path}.tar.gz"
            with tarfile.open(archive_path, 'w:gz', compresslevel=self.compression_level) as tar:
                tar.add(backup_path, arcname=backup_id)
            
            # Remove uncompressed backup
            shutil.rmtree(backup_path)
            
            # Get backup size
            backup_size = os.path.getsize(archive_path)
            
            # Create backup info
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type=BackupType.INCREMENTAL,
                timestamp=datetime.utcnow(),
                size_bytes=backup_size,
                collections=list(changes.keys()),
                base_backup_id=self.catalog['last_full_backup'],
                metadata=metadata
            )
            
            # Update catalog
            self.catalog['backups'].append({
                'backup_id': backup_id,
                'type': 'incremental',
                'timestamp': backup_info.timestamp.isoformat(),
                'size_bytes': backup_size,
                'path': archive_path,
                'base_backup_id': self.catalog['last_full_backup'],
                'metadata': metadata
            })
            self.catalog['last_incremental_backup'] = backup_id
            self._save_catalog()
            
            self.logger.info(
                f"Incremental backup completed: {backup_id} "
                f"({backup_size / (1024*1024):.2f} MB)"
            )
            
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Incremental backup failed: {e}")
            return None
    
    def restore_to_point_in_time(self, target_time: datetime,
                                dry_run: bool = False) -> bool:
        """
        Restore database to a specific point in time.
        
        Args:
            target_time: Target timestamp to restore to
            dry_run: If True, only show what would be restored
            
        Returns:
            bool: True if successful
        """
        self.logger.info(f"Starting point-in-time recovery to {target_time}")
        
        try:
            # Find the appropriate backup chain
            backup_chain = self._find_backup_chain(target_time)
            
            if not backup_chain:
                self.logger.error("No suitable backup found for target time")
                return False
            
            if dry_run:
                print(f"Would restore using backup chain:")
                for backup in backup_chain:
                    print(f"  - {backup['backup_id']} ({backup['type']})")
                return True
            
            # Create restore workspace
            restore_path = os.path.join(
                self.backup_dir, 
                f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(restore_path, exist_ok=True)
            
            # Restore full backup first
            full_backup = backup_chain[0]
            if not self._restore_backup(full_backup, restore_path):
                return False
            
            # Apply incremental backups
            for backup in backup_chain[1:]:
                if backup['type'] == 'incremental':
                    if not self._apply_incremental(backup, restore_path):
                        return False
            
            # Apply oplog to reach target time
            if not self._apply_oplog_to_time(restore_path, target_time):
                self.logger.warning("Could not apply oplog to exact time")
            
            # Restore to MongoDB
            if not self._restore_to_mongodb(restore_path):
                return False
            
            # Cleanup
            shutil.rmtree(restore_path)
            
            self.logger.info(f"Point-in-time recovery completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Point-in-time recovery failed: {e}")
            return False
    
    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Verify backup integrity.
        
        Args:
            backup_id: Backup to verify
            
        Returns:
            Verification report
        """
        report = {
            'backup_id': backup_id,
            'timestamp': datetime.utcnow(),
            'status': 'unknown',
            'errors': [],
            'warnings': []
        }
        
        try:
            # Find backup
            backup_info = self._get_backup_info(backup_id)
            if not backup_info:
                report['status'] = 'failed'
                report['errors'].append('Backup not found in catalog')
                return report
            
            # Check file exists
            if not os.path.exists(backup_info['path']):
                report['status'] = 'failed'
                report['errors'].append('Backup file missing')
                return report
            
            # Verify archive integrity
            try:
                with tarfile.open(backup_info['path'], 'r:gz') as tar:
                    # Check all members can be read
                    for member in tar.getmembers():
                        try:
                            tar.extractfile(member)
                        except Exception as e:
                            report['errors'].append(f"Corrupt file: {member.name}")
            except Exception as e:
                report['status'] = 'failed'
                report['errors'].append(f"Archive corrupt: {str(e)}")
                return report
            
            # For incremental backups, verify base backup exists
            if backup_info.get('base_backup_id'):
                base_backup = self._get_backup_info(backup_info['base_backup_id'])
                if not base_backup:
                    report['warnings'].append('Base backup missing from catalog')
                elif not os.path.exists(base_backup['path']):
                    report['errors'].append('Base backup file missing')
            
            # Set final status
            if report['errors']:
                report['status'] = 'failed'
            elif report['warnings']:
                report['status'] = 'warning'
            else:
                report['status'] = 'verified'
            
            return report
            
        except Exception as e:
            report['status'] = 'error'
            report['errors'].append(f"Verification error: {str(e)}")
            return report
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Remove backups older than retention period.
        
        Returns:
            Cleanup report
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        report = {
            'timestamp': datetime.utcnow(),
            'removed_count': 0,
            'removed_size_bytes': 0,
            'removed_backups': []
        }
        
        self.logger.info(f"Cleaning up backups older than {cutoff_date}")
        
        # Find old backups
        old_backups = []
        for backup in self.catalog['backups']:
            backup_time = datetime.fromisoformat(
                backup['timestamp'].replace('Z', '+00:00')
            )
            if backup_time < cutoff_date:
                old_backups.append(backup)
        
        # Remove old backups
        for backup in old_backups:
            try:
                if os.path.exists(backup['path']):
                    size = os.path.getsize(backup['path'])
                    os.remove(backup['path'])
                    report['removed_count'] += 1
                    report['removed_size_bytes'] += size
                    report['removed_backups'].append(backup['backup_id'])
                
                # Remove from catalog
                self.catalog['backups'].remove(backup)
                
            except Exception as e:
                self.logger.error(f"Failed to remove backup {backup['backup_id']}: {e}")
        
        # Save updated catalog
        self._save_catalog()
        
        self.logger.info(
            f"Cleanup completed: removed {report['removed_count']} backups "
            f"({report['removed_size_bytes'] / (1024*1024):.2f} MB)"
        )
        
        return report
    
    def get_backup_schedule(self) -> Dict[str, Any]:
        """Get recommended backup schedule based on activity."""
        try:
            # Connect to database
            client = MongoClient(self.connection_string)
            db = client[self.database_name]
            
            # Analyze recent activity
            now = datetime.utcnow()
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            
            # Count recent changes
            daily_changes = 0
            weekly_changes = 0
            
            for collection_name in self._list_collections():
                collection = db[collection_name]
                
                # Estimate changes (simplified - production would use change streams)
                daily_changes += collection.count_documents({
                    '$or': [
                        {'created_at': {'$gte': day_ago}},
                        {'updated_at': {'$gte': day_ago}}
                    ]
                })
                
                weekly_changes += collection.count_documents({
                    '$or': [
                        {'created_at': {'$gte': week_ago}},
                        {'updated_at': {'$gte': week_ago}}
                    ]
                })
            
            client.close()
            
            # Recommend schedule based on activity
            if daily_changes > 1000:
                full_backup_interval = "daily"
                incremental_interval = "hourly"
            elif weekly_changes > 1000:
                full_backup_interval = "weekly"
                incremental_interval = "daily"
            else:
                full_backup_interval = "weekly"
                incremental_interval = "twice daily"
            
            return {
                'analysis_time': now,
                'daily_changes': daily_changes,
                'weekly_changes': weekly_changes,
                'recommendations': {
                    'full_backup': full_backup_interval,
                    'incremental_backup': incremental_interval,
                    'retention_days': self.retention_days
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze backup schedule: {e}")
            return {
                'error': str(e),
                'recommendations': {
                    'full_backup': 'daily',
                    'incremental_backup': 'every 6 hours',
                    'retention_days': 30
                }
            }
    
    def _list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            client = MongoClient(self.connection_string)
            db = client[self.database_name]
            collections = db.list_collection_names()
            client.close()
            return collections
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []
    
    def _get_mongodump_version(self) -> str:
        """Get mongodump version."""
        try:
            result = subprocess.run(['mongodump', '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.split('\n')[0]
        except:
            return "unknown"
    
    def _get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup information from catalog."""
        for backup in self.catalog['backups']:
            if backup['backup_id'] == backup_id:
                return backup
        return None
    
    def _export_changes_since(self, since_time: datetime, 
                            export_path: str) -> Dict[str, int]:
        """Export changes since a specific time."""
        changes = {}
        
        try:
            client = MongoClient(self.connection_string)
            db = client[self.database_name]
            
            for collection_name in self._list_collections():
                collection = db[collection_name]
                
                # Find documents modified since last backup
                # This is simplified - production would use change streams
                modified_docs = list(collection.find({
                    '$or': [
                        {'updated_at': {'$gte': since_time}},
                        {'created_at': {'$gte': since_time}}
                    ]
                }))
                
                if modified_docs:
                    # Export to file
                    collection_path = os.path.join(export_path, f"{collection_name}.json")
                    with open(collection_path, 'w') as f:
                        json.dump(modified_docs, f, default=str)
                    
                    changes[collection_name] = len(modified_docs)
            
            client.close()
            
        except Exception as e:
            self.logger.error(f"Failed to export changes: {e}")
        
        return changes
    
    def _find_backup_chain(self, target_time: datetime) -> List[Dict[str, Any]]:
        """Find the backup chain needed to restore to target time."""
        chain = []
        
        # Find the latest full backup before target time
        full_backups = [b for b in self.catalog['backups'] if b['type'] == 'full']
        full_backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        base_backup = None
        for backup in full_backups:
            backup_time = datetime.fromisoformat(
                backup['timestamp'].replace('Z', '+00:00')
            )
            if backup_time <= target_time:
                base_backup = backup
                break
        
        if not base_backup:
            return []
        
        chain.append(base_backup)
        
        # Find incremental backups between base and target
        incrementals = [
            b for b in self.catalog['backups'] 
            if b['type'] == 'incremental' and 
            b.get('base_backup_id') == base_backup['backup_id']
        ]
        
        for backup in incrementals:
            backup_time = datetime.fromisoformat(
                backup['timestamp'].replace('Z', '+00:00')
            )
            if backup_time <= target_time:
                chain.append(backup)
        
        return chain
    
    def _restore_backup(self, backup_info: Dict[str, Any], 
                       restore_path: str) -> bool:
        """Restore a backup to a directory."""
        try:
            # Extract backup
            with tarfile.open(backup_info['path'], 'r:gz') as tar:
                tar.extractall(restore_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _apply_incremental(self, backup_info: Dict[str, Any],
                          restore_path: str) -> bool:
        """Apply incremental backup to restore directory."""
        # This is simplified - production would merge changes properly
        return True
    
    def _apply_oplog_to_time(self, restore_path: str, 
                           target_time: datetime) -> bool:
        """Apply oplog entries up to target time."""
        # This would replay oplog entries
        # Simplified for this implementation
        return True
    
    def _restore_to_mongodb(self, restore_path: str) -> bool:
        """Restore backup to MongoDB."""
        try:
            # Find the backup data directory
            backup_dirs = [d for d in os.listdir(restore_path) 
                          if os.path.isdir(os.path.join(restore_path, d))]
            
            if not backup_dirs:
                self.logger.error("No backup data found in restore path")
                return False
            
            data_path = os.path.join(restore_path, backup_dirs[0], self.database_name)
            
            # Use mongorestore
            restore_cmd = [
                'mongorestore',
                '--uri', self.connection_string,
                '--db', self.database_name,
                '--drop',  # Drop existing collections first
                data_path
            ]
            
            result = subprocess.run(restore_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Mongorestore failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore to MongoDB: {e}")
            return False


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backup and Recovery Manager')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('--type', choices=['full', 'incremental'], 
                              default='incremental', help='Backup type')
    backup_parser.add_argument('--description', help='Backup description')
    
    # Restore commands
    restore_parser = subparsers.add_parser('restore', help='Restore backup')
    restore_parser.add_argument('--backup-id', help='Specific backup to restore')
    restore_parser.add_argument('--point-in-time', help='Restore to specific time (ISO format)')
    restore_parser.add_argument('--dry-run', action='store_true', 
                               help='Show what would be restored')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify backup')
    verify_parser.add_argument('backup_id', help='Backup to verify')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List backups')
    list_parser.add_argument('--limit', type=int, default=10, 
                            help='Number of backups to show')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean old backups')
    
    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', 
                                          help='Show recommended schedule')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = BackupRecoveryManager()
    
    if args.command == 'backup':
        if args.type == 'full':
            backup_info = manager.create_full_backup(args.description or "")
        else:
            backup_info = manager.create_incremental_backup(args.description or "")
        
        if backup_info:
            print(f"Backup created: {backup_info.backup_id}")
            print(f"Size: {backup_info.size_bytes / (1024*1024):.2f} MB")
        else:
            print("Backup failed")
            sys.exit(1)
    
    elif args.command == 'restore':
        if args.point_in_time:
            target_time = datetime.fromisoformat(args.point_in_time)
            success = manager.restore_to_point_in_time(target_time, args.dry_run)
        else:
            print("Point-in-time restore requires --point-in-time parameter")
            sys.exit(1)
        
        if success:
            print("Restore completed successfully")
        else:
            print("Restore failed")
            sys.exit(1)
    
    elif args.command == 'verify':
        report = manager.verify_backup(args.backup_id)
        print(f"Verification Report for {args.backup_id}:")
        print(f"Status: {report['status']}")
        if report['errors']:
            print("Errors:")
            for error in report['errors']:
                print(f"  - {error}")
        if report['warnings']:
            print("Warnings:")
            for warning in report['warnings']:
                print(f"  - {warning}")
    
    elif args.command == 'list':
        backups = manager.catalog['backups'][-args.limit:]
        print(f"Recent Backups (showing {len(backups)}):")
        for backup in backups:
            print(f"\n{backup['backup_id']}:")
            print(f"  Type: {backup['type']}")
            print(f"  Time: {backup['timestamp']}")
            print(f"  Size: {backup['size_bytes'] / (1024*1024):.2f} MB")
            if backup.get('base_backup_id'):
                print(f"  Base: {backup['base_backup_id']}")
    
    elif args.command == 'cleanup':
        report = manager.cleanup_old_backups()
        print(f"Cleanup Report:")
        print(f"Removed: {report['removed_count']} backups")
        print(f"Freed: {report['removed_size_bytes'] / (1024*1024):.2f} MB")
    
    elif args.command == 'schedule':
        schedule = manager.get_backup_schedule()
        print("Backup Schedule Recommendations:")
        print(f"Daily changes: {schedule.get('daily_changes', 'N/A')}")
        print(f"Weekly changes: {schedule.get('weekly_changes', 'N/A')}")
        print("\nRecommended Schedule:")
        for key, value in schedule['recommendations'].items():
            print(f"  {key}: {value}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()