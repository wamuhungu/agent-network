#!/usr/bin/env python3
"""
State Export/Import Utilities

Provides comprehensive state export and import capabilities for:
- System migration
- Backup and restore
- Configuration management
- Selective component export
"""

import os
import sys
import json
import yaml
import tarfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import hashlib
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager
from tools.message_broker import MessageBroker


@dataclass
class ExportManifest:
    """Metadata about an export."""
    export_id: str
    export_type: str  # 'full', 'selective', 'config_only'
    timestamp: datetime
    version: str
    components: List[str]
    collections: List[str]
    metadata: Dict[str, Any]
    checksum: Optional[str] = None


class StateExporter:
    """
    Handles export and import of system state.
    
    Features:
    - Full system state export
    - Selective component export
    - Configuration backup
    - Data validation
    - Version compatibility checking
    - Incremental exports
    """
    
    EXPORT_VERSION = "1.0.0"
    
    def __init__(self):
        """Initialize the state exporter."""
        self.state_manager = StateManager()
        self.export_dir = "./exports"
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Define exportable collections
        self.collections = {
            'tasks': {
                'required': True,
                'indexes': ['task_id', 'status']
            },
            'agent_states': {
                'required': True,
                'indexes': ['agent_id']
            },
            'activity_logs': {
                'required': False,
                'indexes': ['timestamp', 'agent_id']
            },
            'messages': {
                'required': False,
                'indexes': ['message_id', 'agent_id']
            },
            'archived_tasks': {
                'required': False,
                'indexes': ['task_id', 'archived_at']
            }
        }
        
        # Configuration files to export
        self.config_files = [
            'project.json',
            '.agents/manager/persona.json',
            '.agents/developer/persona.json',
            'requirements.txt',
            'tools/webserver_config.py'
        ]
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('StateExporter')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/state_export.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def export_full_state(self, description: str = "") -> Optional[str]:
        """
        Export complete system state.
        
        Args:
            description: Optional description for the export
            
        Returns:
            Export ID if successful
        """
        export_id = f"full_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        export_path = os.path.join(self.export_dir, export_id)
        
        self.logger.info(f"Starting full state export: {export_id}")
        
        try:
            # Create export directory
            os.makedirs(export_path, exist_ok=True)
            
            # Export database collections
            collections_exported = self._export_collections(export_path)
            
            # Export configurations
            configs_exported = self._export_configurations(export_path)
            
            # Export queue state
            queue_state = self._export_queue_state(export_path)
            
            # Create manifest
            manifest = ExportManifest(
                export_id=export_id,
                export_type='full',
                timestamp=datetime.utcnow(),
                version=self.EXPORT_VERSION,
                components=['database', 'configuration', 'queue_state'],
                collections=collections_exported,
                metadata={
                    'description': description,
                    'configs': configs_exported,
                    'queue_state': queue_state
                }
            )
            
            # Save manifest
            with open(os.path.join(export_path, 'manifest.json'), 'w') as f:
                json.dump(asdict(manifest), f, indent=2, default=str)
            
            # Create archive
            archive_path = f"{export_path}.tar.gz"
            self._create_archive(export_path, archive_path)
            
            # Calculate checksum
            manifest.checksum = self._calculate_checksum(archive_path)
            
            # Update manifest with checksum
            with open(os.path.join(export_path, 'manifest.json'), 'w') as f:
                json.dump(asdict(manifest), f, indent=2, default=str)
            
            # Recreate archive with updated manifest
            self._create_archive(export_path, archive_path)
            
            # Cleanup temporary directory
            shutil.rmtree(export_path)
            
            self.logger.info(f"Export completed: {export_id}")
            return export_id
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            # Cleanup on failure
            if os.path.exists(export_path):
                shutil.rmtree(export_path)
            return None
    
    def export_selective(self, components: List[str], 
                        collections: Optional[List[str]] = None,
                        description: str = "") -> Optional[str]:
        """
        Export selected components and collections.
        
        Args:
            components: List of components to export ('database', 'config', 'queue')
            collections: Specific collections to export (None = all)
            description: Optional description
            
        Returns:
            Export ID if successful
        """
        export_id = f"selective_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        export_path = os.path.join(self.export_dir, export_id)
        
        self.logger.info(f"Starting selective export: {export_id}")
        
        try:
            os.makedirs(export_path, exist_ok=True)
            
            collections_exported = []
            configs_exported = []
            queue_state = None
            
            # Export requested components
            if 'database' in components:
                collections_exported = self._export_collections(
                    export_path, 
                    specific_collections=collections
                )
            
            if 'config' in components:
                configs_exported = self._export_configurations(export_path)
            
            if 'queue' in components:
                queue_state = self._export_queue_state(export_path)
            
            # Create manifest
            manifest = ExportManifest(
                export_id=export_id,
                export_type='selective',
                timestamp=datetime.utcnow(),
                version=self.EXPORT_VERSION,
                components=components,
                collections=collections_exported,
                metadata={
                    'description': description,
                    'configs': configs_exported,
                    'queue_state': queue_state
                }
            )
            
            # Save manifest and create archive
            with open(os.path.join(export_path, 'manifest.json'), 'w') as f:
                json.dump(asdict(manifest), f, indent=2, default=str)
            
            archive_path = f"{export_path}.tar.gz"
            self._create_archive(export_path, archive_path)
            
            # Cleanup
            shutil.rmtree(export_path)
            
            self.logger.info(f"Selective export completed: {export_id}")
            return export_id
            
        except Exception as e:
            self.logger.error(f"Selective export failed: {e}")
            if os.path.exists(export_path):
                shutil.rmtree(export_path)
            return None
    
    def export_config_only(self, description: str = "") -> Optional[str]:
        """
        Export only configuration files.
        
        Args:
            description: Optional description
            
        Returns:
            Export ID if successful
        """
        return self.export_selective(['config'], description=description)
    
    def import_state(self, export_id: str, 
                    merge: bool = False,
                    dry_run: bool = False) -> bool:
        """
        Import system state from export.
        
        Args:
            export_id: ID of export to import
            merge: If True, merge with existing data; if False, replace
            dry_run: If True, validate but don't import
            
        Returns:
            bool: True if successful
        """
        archive_path = os.path.join(self.export_dir, f"{export_id}.tar.gz")
        
        if not os.path.exists(archive_path):
            self.logger.error(f"Export not found: {export_id}")
            return False
        
        temp_path = os.path.join(self.export_dir, f"temp_{export_id}")
        
        try:
            # Extract archive
            self._extract_archive(archive_path, temp_path)
            
            # Load and validate manifest
            manifest_path = os.path.join(temp_path, export_id, 'manifest.json')
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Check version compatibility
            if not self._check_version_compatibility(manifest_data['version']):
                raise ValueError(f"Incompatible version: {manifest_data['version']}")
            
            if dry_run:
                self.logger.info("Dry run - validating import...")
                # Validate data
                validation_result = self._validate_import_data(
                    os.path.join(temp_path, export_id)
                )
                
                print(f"Validation Result:")
                print(f"  Valid: {validation_result['valid']}")
                print(f"  Collections: {len(validation_result['collections'])}")
                print(f"  Documents: {validation_result['total_documents']}")
                print(f"  Configurations: {len(validation_result['configs'])}")
                
                if validation_result['errors']:
                    print(f"  Errors:")
                    for error in validation_result['errors']:
                        print(f"    - {error}")
                
                return validation_result['valid']
            
            # Perform actual import
            self.logger.info(f"Importing state from {export_id} (merge={merge})")
            
            # Import database collections
            if 'database' in manifest_data['components']:
                self._import_collections(
                    os.path.join(temp_path, export_id, 'database'),
                    merge=merge
                )
            
            # Import configurations
            if 'config' in manifest_data['components']:
                self._import_configurations(
                    os.path.join(temp_path, export_id, 'config')
                )
            
            # Import queue state if requested
            if 'queue' in manifest_data['components']:
                self._import_queue_state(
                    os.path.join(temp_path, export_id, 'queue_state.json')
                )
            
            self.logger.info(f"Import completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            return False
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
    
    def _export_collections(self, export_path: str,
                          specific_collections: Optional[List[str]] = None) -> List[str]:
        """Export database collections."""
        db_path = os.path.join(export_path, 'database')
        os.makedirs(db_path, exist_ok=True)
        
        collections_exported = []
        
        # Determine which collections to export
        collections_to_export = specific_collections or list(self.collections.keys())
        
        for collection_name in collections_to_export:
            if collection_name not in self.collections:
                self.logger.warning(f"Unknown collection: {collection_name}")
                continue
            
            try:
                # Export collection data
                collection = self.state_manager.db[collection_name]
                documents = list(collection.find())
                
                # Save to file
                collection_file = os.path.join(db_path, f"{collection_name}.json")
                with open(collection_file, 'w') as f:
                    json.dump(documents, f, indent=2, default=str)
                
                # Export indexes
                indexes = collection.list_indexes()
                index_file = os.path.join(db_path, f"{collection_name}_indexes.json")
                with open(index_file, 'w') as f:
                    json.dump(list(indexes), f, indent=2, default=str)
                
                collections_exported.append(collection_name)
                self.logger.info(f"Exported {len(documents)} documents from {collection_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to export {collection_name}: {e}")
        
        return collections_exported
    
    def _export_configurations(self, export_path: str) -> List[str]:
        """Export configuration files."""
        config_path = os.path.join(export_path, 'config')
        os.makedirs(config_path, exist_ok=True)
        
        configs_exported = []
        
        for config_file in self.config_files:
            try:
                src_path = config_file
                if os.path.exists(src_path):
                    # Preserve directory structure
                    dst_dir = os.path.join(config_path, os.path.dirname(config_file))
                    os.makedirs(dst_dir, exist_ok=True)
                    
                    dst_path = os.path.join(config_path, config_file)
                    shutil.copy2(src_path, dst_path)
                    
                    configs_exported.append(config_file)
                    self.logger.info(f"Exported config: {config_file}")
                    
            except Exception as e:
                self.logger.error(f"Failed to export config {config_file}: {e}")
        
        return configs_exported
    
    def _export_queue_state(self, export_path: str) -> Dict[str, Any]:
        """Export message queue state."""
        queue_state = {
            'timestamp': datetime.utcnow().isoformat(),
            'queues': {}
        }
        
        try:
            broker = MessageBroker()
            if broker.connect():
                # Get queue information
                for queue_name in [MessageBroker.MANAGER_QUEUE, 
                                 MessageBroker.DEVELOPER_QUEUE]:
                    info = broker.get_queue_info(queue_name)
                    if info:
                        queue_state['queues'][queue_name] = info
                
                broker.disconnect()
                
                # Save queue state
                with open(os.path.join(export_path, 'queue_state.json'), 'w') as f:
                    json.dump(queue_state, f, indent=2)
                
                self.logger.info("Exported queue state")
                
        except Exception as e:
            self.logger.error(f"Failed to export queue state: {e}")
        
        return queue_state
    
    def _import_collections(self, db_path: str, merge: bool = False):
        """Import database collections."""
        for filename in os.listdir(db_path):
            if filename.endswith('.json') and not filename.endswith('_indexes.json'):
                collection_name = filename[:-5]  # Remove .json
                
                try:
                    # Load documents
                    with open(os.path.join(db_path, filename), 'r') as f:
                        documents = json.load(f)
                    
                    collection = self.state_manager.db[collection_name]
                    
                    if not merge:
                        # Clear existing collection
                        collection.delete_many({})
                        self.logger.info(f"Cleared collection: {collection_name}")
                    
                    # Import documents
                    if documents:
                        # Convert string dates back to datetime objects
                        for doc in documents:
                            for key, value in doc.items():
                                if isinstance(value, str) and 'T' in value and ':' in value:
                                    try:
                                        doc[key] = datetime.fromisoformat(
                                            value.replace('Z', '+00:00')
                                        )
                                    except:
                                        pass
                        
                        if merge:
                            # Upsert documents
                            for doc in documents:
                                filter_key = None
                                if collection_name == 'tasks':
                                    filter_key = {'task_id': doc.get('task_id')}
                                elif collection_name == 'agent_states':
                                    filter_key = {'agent_id': doc.get('agent_id')}
                                
                                if filter_key and doc.get(list(filter_key.keys())[0]):
                                    collection.replace_one(filter_key, doc, upsert=True)
                                else:
                                    collection.insert_one(doc)
                        else:
                            collection.insert_many(documents)
                    
                    self.logger.info(
                        f"Imported {len(documents)} documents into {collection_name}"
                    )
                    
                    # Recreate indexes
                    index_file = os.path.join(db_path, f"{collection_name}_indexes.json")
                    if os.path.exists(index_file):
                        with open(index_file, 'r') as f:
                            indexes = json.load(f)
                        
                        for index in indexes:
                            if index.get('name') != '_id_':  # Skip default index
                                try:
                                    collection.create_index(index['key'])
                                except:
                                    pass
                    
                except Exception as e:
                    self.logger.error(f"Failed to import {collection_name}: {e}")
    
    def _import_configurations(self, config_path: str):
        """Import configuration files."""
        # Create backup of current configs
        backup_dir = f"./config_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        for config_file in self.config_files:
            if os.path.exists(config_file):
                dst = os.path.join(backup_dir, config_file)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(config_file, dst)
        
        # Import new configs
        for root, dirs, files in os.walk(config_path):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, config_path)
                dst_path = rel_path
                
                try:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    self.logger.info(f"Imported config: {rel_path}")
                except Exception as e:
                    self.logger.error(f"Failed to import config {rel_path}: {e}")
    
    def _import_queue_state(self, queue_state_file: str):
        """Import queue state (informational only)."""
        try:
            with open(queue_state_file, 'r') as f:
                queue_state = json.load(f)
            
            self.logger.info(f"Queue state at export: {queue_state}")
            # Note: We don't restore queue messages as they may be stale
            
        except Exception as e:
            self.logger.error(f"Failed to read queue state: {e}")
    
    def _create_archive(self, source_dir: str, archive_path: str):
        """Create compressed archive."""
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    
    def _extract_archive(self, archive_path: str, extract_path: str):
        """Extract compressed archive."""
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(extract_path)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _check_version_compatibility(self, version: str) -> bool:
        """Check if export version is compatible."""
        # For now, just check major version
        export_major = version.split('.')[0]
        current_major = self.EXPORT_VERSION.split('.')[0]
        return export_major == current_major
    
    def _validate_import_data(self, export_path: str) -> Dict[str, Any]:
        """Validate data before import."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'collections': [],
            'configs': [],
            'total_documents': 0
        }
        
        # Check database exports
        db_path = os.path.join(export_path, 'database')
        if os.path.exists(db_path):
            for filename in os.listdir(db_path):
                if filename.endswith('.json') and not filename.endswith('_indexes.json'):
                    collection_name = filename[:-5]
                    
                    try:
                        with open(os.path.join(db_path, filename), 'r') as f:
                            documents = json.load(f)
                        
                        result['collections'].append(collection_name)
                        result['total_documents'] += len(documents)
                        
                        # Validate required collections
                        if (collection_name in self.collections and 
                            self.collections[collection_name]['required'] and 
                            len(documents) == 0):
                            result['warnings'].append(
                                f"Required collection '{collection_name}' is empty"
                            )
                        
                    except Exception as e:
                        result['errors'].append(f"Invalid data in {collection_name}: {str(e)}")
                        result['valid'] = False
        
        # Check config exports
        config_path = os.path.join(export_path, 'config')
        if os.path.exists(config_path):
            for root, dirs, files in os.walk(config_path):
                for file in files:
                    result['configs'].append(
                        os.path.relpath(os.path.join(root, file), config_path)
                    )
        
        return result
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List available exports."""
        exports = []
        
        for filename in os.listdir(self.export_dir):
            if filename.endswith('.tar.gz'):
                export_id = filename[:-7]  # Remove .tar.gz
                
                try:
                    # Extract manifest
                    archive_path = os.path.join(self.export_dir, filename)
                    temp_path = os.path.join(self.export_dir, f"temp_{export_id}")
                    
                    self._extract_archive(archive_path, temp_path)
                    
                    manifest_path = os.path.join(temp_path, export_id, 'manifest.json')
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    # Get file size
                    file_size = os.path.getsize(archive_path)
                    
                    exports.append({
                        'export_id': export_id,
                        'type': manifest['export_type'],
                        'timestamp': manifest['timestamp'],
                        'components': manifest['components'],
                        'collections': manifest['collections'],
                        'size_bytes': file_size,
                        'description': manifest['metadata'].get('description', '')
                    })
                    
                    # Cleanup
                    shutil.rmtree(temp_path)
                    
                except Exception as e:
                    self.logger.error(f"Error reading export {export_id}: {e}")
        
        # Sort by timestamp (newest first)
        exports.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return exports
    
    def delete_export(self, export_id: str) -> bool:
        """Delete an export."""
        archive_path = os.path.join(self.export_dir, f"{export_id}.tar.gz")
        
        try:
            if os.path.exists(archive_path):
                os.remove(archive_path)
                self.logger.info(f"Deleted export: {export_id}")
                return True
            else:
                self.logger.warning(f"Export not found: {export_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete export: {e}")
            return False


def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='State Export/Import Utility')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Export commands
    export_parser = subparsers.add_parser('export', help='Export system state')
    export_parser.add_argument('--type', choices=['full', 'selective', 'config'],
                              default='full', help='Export type')
    export_parser.add_argument('--components', nargs='+',
                              choices=['database', 'config', 'queue'],
                              help='Components to export (for selective export)')
    export_parser.add_argument('--collections', nargs='+',
                              help='Specific collections to export')
    export_parser.add_argument('--description', help='Export description')
    
    # Import commands
    import_parser = subparsers.add_parser('import', help='Import system state')
    import_parser.add_argument('export_id', help='Export ID to import')
    import_parser.add_argument('--merge', action='store_true',
                              help='Merge with existing data instead of replacing')
    import_parser.add_argument('--dry-run', action='store_true',
                              help='Validate without importing')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available exports')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an export')
    delete_parser.add_argument('export_id', help='Export ID to delete')
    
    args = parser.parse_args()
    
    exporter = StateExporter()
    
    if args.command == 'export':
        if args.type == 'full':
            export_id = exporter.export_full_state(
                description=args.description or ""
            )
        elif args.type == 'selective':
            if not args.components:
                print("Error: --components required for selective export")
                sys.exit(1)
            export_id = exporter.export_selective(
                components=args.components,
                collections=args.collections,
                description=args.description or ""
            )
        elif args.type == 'config':
            export_id = exporter.export_config_only(
                description=args.description or ""
            )
        
        if export_id:
            print(f"Export created: {export_id}")
        else:
            print("Export failed")
            sys.exit(1)
    
    elif args.command == 'import':
        success = exporter.import_state(
            args.export_id,
            merge=args.merge,
            dry_run=args.dry_run
        )
        
        if not args.dry_run:
            if success:
                print(f"Import successful")
            else:
                print("Import failed")
                sys.exit(1)
    
    elif args.command == 'list':
        exports = exporter.list_exports()
        
        if not exports:
            print("No exports found")
        else:
            print(f"Available Exports ({len(exports)}):")
            print(f"{'Export ID':<30} {'Type':<12} {'Timestamp':<20} {'Size':<10} Description")
            print("-" * 90)
            
            for export in exports:
                size_mb = export['size_bytes'] / (1024 * 1024)
                timestamp = datetime.fromisoformat(export['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{export['export_id']:<30} {export['type']:<12} {timestamp:<20} "
                      f"{size_mb:>6.1f} MB  {export['description']}")
    
    elif args.command == 'delete':
        if exporter.delete_export(args.export_id):
            print(f"Export deleted: {args.export_id}")
        else:
            print("Delete failed")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()