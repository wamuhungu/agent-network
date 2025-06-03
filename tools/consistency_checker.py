#!/usr/bin/env python3
"""
Consistency Checker

Tools for validating and repairing data consistency across the system.
Includes integrity constraints, validation rules, and repair procedures.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.state_manager import StateManager
from tools.transaction_manager import TransactionManager


class InconsistencyType(Enum):
    """Types of data inconsistencies."""
    ORPHANED_TASK = "orphaned_task"
    INVALID_STATUS_TRANSITION = "invalid_status_transition"
    MISSING_REFERENCE = "missing_reference"
    DUPLICATE_ENTRY = "duplicate_entry"
    SCHEMA_VIOLATION = "schema_violation"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    REFERENTIAL_INTEGRITY = "referential_integrity"


@dataclass
class ValidationRule:
    """Defines a validation rule."""
    name: str
    description: str
    collection: str
    check_func: callable
    repair_func: Optional[callable] = None
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue found."""
    type: InconsistencyType
    collection: str
    document_id: Any
    description: str
    severity: str
    data: Dict[str, Any]
    can_auto_repair: bool
    repair_suggestion: str


class ConsistencyChecker:
    """
    Comprehensive consistency checking and repair tool.
    
    Features:
    - Schema validation
    - Referential integrity checks
    - Status consistency validation
    - Temporal consistency checks
    - Automatic repair capabilities
    - Detailed reporting
    """
    
    def __init__(self):
        """Initialize the consistency checker."""
        self.state_manager = StateManager()
        self.transaction_manager = TransactionManager()
        
        # Validation rules
        self.validation_rules = self._define_validation_rules()
        
        # Schema definitions
        self.schemas = self._define_schemas()
        
        # Valid state transitions
        self.valid_transitions = {
            'tasks': {
                'created': ['assigned', 'cancelled'],
                'assigned': ['in_progress', 'created', 'cancelled'],
                'in_progress': ['completed', 'failed', 'assigned'],
                'completed': [],
                'failed': ['created', 'assigned'],
                'cancelled': []
            }
        }
        
        # Setup logging
        self.setup_logging()
        
        # Check results
        self.issues: List[ConsistencyIssue] = []
        self.repairs_performed = 0
    
    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger('ConsistencyChecker')
        
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/consistency.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _define_validation_rules(self) -> List[ValidationRule]:
        """Define all validation rules."""
        return [
            # Task validation rules
            ValidationRule(
                name="task_assigned_agent_exists",
                description="Ensure assigned tasks have valid agent references",
                collection="tasks",
                check_func=self._check_task_agent_references,
                repair_func=self._repair_task_agent_references,
                severity="high"
            ),
            ValidationRule(
                name="task_status_consistency",
                description="Validate task status transitions",
                collection="tasks",
                check_func=self._check_task_status_consistency,
                repair_func=None,  # Manual review needed
                severity="medium"
            ),
            ValidationRule(
                name="task_temporal_consistency",
                description="Ensure task timestamps are logical",
                collection="tasks",
                check_func=self._check_task_temporal_consistency,
                repair_func=self._repair_task_temporal_consistency,
                severity="low"
            ),
            
            # Agent state validation rules
            ValidationRule(
                name="agent_current_task_exists",
                description="Ensure agent current tasks exist",
                collection="agent_states",
                check_func=self._check_agent_task_references,
                repair_func=self._repair_agent_task_references,
                severity="high"
            ),
            ValidationRule(
                name="agent_unique_ids",
                description="Ensure agent IDs are unique",
                collection="agent_states",
                check_func=self._check_agent_uniqueness,
                repair_func=None,  # Critical - manual intervention
                severity="critical"
            ),
            
            # Activity log validation rules
            ValidationRule(
                name="activity_agent_exists",
                description="Ensure activities reference valid agents",
                collection="activity_logs",
                check_func=self._check_activity_agent_references,
                repair_func=None,  # Historical data - no repair
                severity="low"
            ),
            
            # Cross-collection validation rules
            ValidationRule(
                name="bidirectional_references",
                description="Ensure bidirectional references are consistent",
                collection="*",
                check_func=self._check_bidirectional_references,
                repair_func=self._repair_bidirectional_references,
                severity="high"
            )
        ]
    
    def _define_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define expected schemas for collections."""
        return {
            'tasks': {
                'required_fields': ['task_id', 'status', 'created_at'],
                'optional_fields': ['title', 'description', 'assigned_to', 
                                  'priority', 'metadata', 'requirements'],
                'field_types': {
                    'task_id': str,
                    'status': str,
                    'created_at': datetime,
                    'priority': str
                },
                'valid_values': {
                    'status': ['created', 'assigned', 'in_progress', 
                              'completed', 'failed', 'cancelled'],
                    'priority': ['low', 'normal', 'high', 'critical']
                }
            },
            'agent_states': {
                'required_fields': ['agent_id', 'status'],
                'optional_fields': ['current_task_id', 'capabilities', 
                                  'last_heartbeat', 'metadata'],
                'field_types': {
                    'agent_id': str,
                    'status': str,
                    'capabilities': list
                },
                'valid_values': {
                    'status': ['active', 'ready', 'working', 'error', 
                              'stopped', 'listening'],
                    'agent_id': ['manager', 'developer']
                }
            },
            'activity_logs': {
                'required_fields': ['timestamp', 'agent_id', 'activity_type'],
                'optional_fields': ['details', 'task_id'],
                'field_types': {
                    'timestamp': datetime,
                    'agent_id': str,
                    'activity_type': str
                }
            }
        }
    
    def run_full_check(self, auto_repair: bool = False) -> Dict[str, Any]:
        """
        Run all consistency checks.
        
        Args:
            auto_repair: Whether to automatically repair issues
            
        Returns:
            Comprehensive report of issues found and repairs made
        """
        self.logger.info("Starting full consistency check")
        start_time = datetime.utcnow()
        
        # Clear previous results
        self.issues = []
        self.repairs_performed = 0
        
        # Run schema validation
        self._validate_schemas()
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                self.logger.info(f"Running rule: {rule.name}")
                rule.check_func()
            except Exception as e:
                self.logger.error(f"Error running rule {rule.name}: {e}")
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.SCHEMA_VIOLATION,
                    collection=rule.collection,
                    document_id=None,
                    description=f"Rule check failed: {str(e)}",
                    severity="critical",
                    data={'rule': rule.name, 'error': str(e)},
                    can_auto_repair=False,
                    repair_suggestion="Review rule implementation"
                ))
        
        # Perform repairs if requested
        if auto_repair:
            self._perform_repairs()
        
        # Generate report
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        report = {
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'total_issues': len(self.issues),
            'issues_by_severity': self._count_by_severity(),
            'issues_by_type': self._count_by_type(),
            'repairs_performed': self.repairs_performed,
            'auto_repair_enabled': auto_repair,
            'detailed_issues': self._format_issues()
        }
        
        # Log summary
        self.logger.info(
            f"Consistency check completed in {duration:.2f}s - "
            f"Found {len(self.issues)} issues, "
            f"Repaired {self.repairs_performed}"
        )
        
        # Save report to database
        self._save_report(report)
        
        return report
    
    def _validate_schemas(self):
        """Validate document schemas across collections."""
        for collection_name, schema in self.schemas.items():
            try:
                # Get sample of documents
                documents = list(self.state_manager.db[collection_name].find().limit(1000))
                
                for doc in documents:
                    # Check required fields
                    for field in schema['required_fields']:
                        if field not in doc:
                            self.issues.append(ConsistencyIssue(
                                type=InconsistencyType.SCHEMA_VIOLATION,
                                collection=collection_name,
                                document_id=doc.get('_id'),
                                description=f"Missing required field: {field}",
                                severity="high",
                                data={'document': doc, 'missing_field': field},
                                can_auto_repair=False,
                                repair_suggestion=f"Add missing field '{field}' with appropriate value"
                            ))
                    
                    # Check field types
                    for field, expected_type in schema.get('field_types', {}).items():
                        if field in doc and not isinstance(doc[field], expected_type):
                            self.issues.append(ConsistencyIssue(
                                type=InconsistencyType.SCHEMA_VIOLATION,
                                collection=collection_name,
                                document_id=doc.get('_id'),
                                description=f"Invalid type for field {field}",
                                severity="medium",
                                data={
                                    'field': field,
                                    'expected_type': str(expected_type),
                                    'actual_type': str(type(doc[field]))
                                },
                                can_auto_repair=False,
                                repair_suggestion=f"Convert {field} to {expected_type.__name__}"
                            ))
                    
                    # Check valid values
                    for field, valid_values in schema.get('valid_values', {}).items():
                        if field in doc and doc[field] not in valid_values:
                            self.issues.append(ConsistencyIssue(
                                type=InconsistencyType.SCHEMA_VIOLATION,
                                collection=collection_name,
                                document_id=doc.get('_id'),
                                description=f"Invalid value for field {field}",
                                severity="medium",
                                data={
                                    'field': field,
                                    'value': doc[field],
                                    'valid_values': valid_values
                                },
                                can_auto_repair=True,
                                repair_suggestion=f"Set {field} to one of: {valid_values}"
                            ))
                            
            except Exception as e:
                self.logger.error(f"Schema validation error for {collection_name}: {e}")
    
    def _check_task_agent_references(self):
        """Check that tasks reference valid agents."""
        tasks = self.state_manager.db.tasks.find({'assigned_to': {'$exists': True}})
        
        for task in tasks:
            agent_id = task['assigned_to']
            agent = self.state_manager.db.agent_states.find_one({'agent_id': agent_id})
            
            if not agent:
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.MISSING_REFERENCE,
                    collection='tasks',
                    document_id=task['_id'],
                    description=f"Task assigned to non-existent agent: {agent_id}",
                    severity="high",
                    data={'task_id': task['task_id'], 'agent_id': agent_id},
                    can_auto_repair=True,
                    repair_suggestion="Clear assigned_to field and reset status to 'created'"
                ))
    
    def _repair_task_agent_references(self, issue: ConsistencyIssue) -> bool:
        """Repair tasks with invalid agent references."""
        try:
            with self.transaction_manager.transaction("Repair task agent reference") as txn:
                txn.update(
                    'tasks',
                    {'_id': issue.document_id},
                    {
                        '$set': {'status': 'created'},
                        '$unset': {'assigned_to': 1}
                    }
                )
                
                txn.insert('activity_logs', {
                    'timestamp': datetime.utcnow(),
                    'agent_id': 'system',
                    'activity_type': 'consistency_repair',
                    'details': {
                        'issue_type': issue.type.value,
                        'task_id': issue.data['task_id'],
                        'repair': 'Cleared invalid agent assignment'
                    }
                })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair task agent reference: {e}")
            return False
    
    def _check_task_status_consistency(self):
        """Check task status transition validity."""
        # Get all tasks with status history
        tasks = self.state_manager.db.tasks.find({})
        
        for task in tasks:
            # Check if metadata contains status history
            if 'status_history' in task.get('metadata', {}):
                history = task['metadata']['status_history']
                
                for i in range(1, len(history)):
                    prev_status = history[i-1]['status']
                    curr_status = history[i]['status']
                    
                    valid_transitions = self.valid_transitions['tasks'].get(prev_status, [])
                    
                    if curr_status not in valid_transitions:
                        self.issues.append(ConsistencyIssue(
                            type=InconsistencyType.INVALID_STATUS_TRANSITION,
                            collection='tasks',
                            document_id=task['_id'],
                            description=f"Invalid status transition: {prev_status} -> {curr_status}",
                            severity="medium",
                            data={
                                'task_id': task['task_id'],
                                'transition': f"{prev_status} -> {curr_status}"
                            },
                            can_auto_repair=False,
                            repair_suggestion="Review task history and correct if needed"
                        ))
    
    def _check_task_temporal_consistency(self):
        """Check that task timestamps are logical."""
        tasks = self.state_manager.db.tasks.find({})
        
        for task in tasks:
            created_at = task.get('created_at')
            metadata = task.get('metadata', {})
            
            # Check completed_at after created_at
            if 'completed_at' in metadata and created_at:
                completed_at = datetime.fromisoformat(
                    metadata['completed_at'].replace('Z', '+00:00')
                )
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                if completed_at < created_at:
                    self.issues.append(ConsistencyIssue(
                        type=InconsistencyType.TEMPORAL_INCONSISTENCY,
                        collection='tasks',
                        document_id=task['_id'],
                        description="Task completed before it was created",
                        severity="high",
                        data={
                            'task_id': task['task_id'],
                            'created_at': created_at.isoformat(),
                            'completed_at': completed_at.isoformat()
                        },
                        can_auto_repair=True,
                        repair_suggestion="Adjust timestamps to maintain logical order"
                    ))
    
    def _repair_task_temporal_consistency(self, issue: ConsistencyIssue) -> bool:
        """Repair temporal inconsistencies in tasks."""
        try:
            # For this example, we'll adjust the completed_at to be after created_at
            created_at = datetime.fromisoformat(issue.data['created_at'])
            
            with self.transaction_manager.transaction("Repair temporal inconsistency") as txn:
                txn.update(
                    'tasks',
                    {'_id': issue.document_id},
                    {
                        '$set': {
                            'metadata.completed_at': (created_at + timedelta(hours=1)).isoformat()
                        }
                    }
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair temporal inconsistency: {e}")
            return False
    
    def _check_agent_task_references(self):
        """Check that agent current tasks exist."""
        agents = self.state_manager.db.agent_states.find({
            'current_task_id': {'$exists': True, '$ne': None}
        })
        
        for agent in agents:
            task_id = agent['current_task_id']
            task = self.state_manager.db.tasks.find_one({'task_id': task_id})
            
            if not task:
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.MISSING_REFERENCE,
                    collection='agent_states',
                    document_id=agent['_id'],
                    description=f"Agent references non-existent task: {task_id}",
                    severity="high",
                    data={'agent_id': agent['agent_id'], 'task_id': task_id},
                    can_auto_repair=True,
                    repair_suggestion="Clear current_task_id and set status to 'ready'"
                ))
            elif task.get('assigned_to') != agent['agent_id']:
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.REFERENTIAL_INTEGRITY,
                    collection='agent_states',
                    document_id=agent['_id'],
                    description="Agent has task not assigned to them",
                    severity="high",
                    data={
                        'agent_id': agent['agent_id'],
                        'task_id': task_id,
                        'task_assigned_to': task.get('assigned_to')
                    },
                    can_auto_repair=True,
                    repair_suggestion="Clear incorrect task reference"
                ))
    
    def _repair_agent_task_references(self, issue: ConsistencyIssue) -> bool:
        """Repair agent task reference issues."""
        try:
            with self.transaction_manager.transaction("Repair agent task reference") as txn:
                txn.update(
                    'agent_states',
                    {'_id': issue.document_id},
                    {
                        '$set': {'status': 'ready'},
                        '$unset': {'current_task_id': 1}
                    }
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair agent task reference: {e}")
            return False
    
    def _check_agent_uniqueness(self):
        """Check that agent IDs are unique."""
        pipeline = [
            {'$group': {
                '_id': '$agent_id',
                'count': {'$sum': 1},
                'docs': {'$push': '$_id'}
            }},
            {'$match': {'count': {'$gt': 1}}}
        ]
        
        duplicates = list(self.state_manager.db.agent_states.aggregate(pipeline))
        
        for dup in duplicates:
            self.issues.append(ConsistencyIssue(
                type=InconsistencyType.DUPLICATE_ENTRY,
                collection='agent_states',
                document_id=dup['docs'],
                description=f"Duplicate agent_id: {dup['_id']}",
                severity="critical",
                data={'agent_id': dup['_id'], 'count': dup['count']},
                can_auto_repair=False,
                repair_suggestion="Manual intervention required to resolve duplicate agents"
            ))
    
    def _check_activity_agent_references(self):
        """Check that activities reference valid agents."""
        # Sample check - in production would check all
        activities = list(self.state_manager.db.activity_logs.find().limit(1000))
        
        agent_ids = set()
        agents = self.state_manager.db.agent_states.find({}, {'agent_id': 1})
        for agent in agents:
            agent_ids.add(agent['agent_id'])
        
        for activity in activities:
            if activity['agent_id'] not in agent_ids and activity['agent_id'] != 'system':
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.MISSING_REFERENCE,
                    collection='activity_logs',
                    document_id=activity['_id'],
                    description=f"Activity references unknown agent: {activity['agent_id']}",
                    severity="low",
                    data={'agent_id': activity['agent_id']},
                    can_auto_repair=False,
                    repair_suggestion="Historical data - no repair needed"
                ))
    
    def _check_bidirectional_references(self):
        """Check bidirectional references between collections."""
        # Check task-agent bidirectional consistency
        tasks = self.state_manager.db.tasks.find({
            'status': {'$in': ['assigned', 'in_progress']},
            'assigned_to': {'$exists': True}
        })
        
        for task in tasks:
            agent = self.state_manager.db.agent_states.find_one({
                'agent_id': task['assigned_to']
            })
            
            if agent and agent.get('current_task_id') != task['task_id']:
                self.issues.append(ConsistencyIssue(
                    type=InconsistencyType.REFERENTIAL_INTEGRITY,
                    collection='*',
                    document_id={'task': task['_id'], 'agent': agent['_id']},
                    description="Bidirectional reference mismatch",
                    severity="high",
                    data={
                        'task_id': task['task_id'],
                        'task_assigned_to': task['assigned_to'],
                        'agent_current_task': agent.get('current_task_id')
                    },
                    can_auto_repair=True,
                    repair_suggestion="Synchronize task and agent references"
                ))
    
    def _repair_bidirectional_references(self, issue: ConsistencyIssue) -> bool:
        """Repair bidirectional reference issues."""
        try:
            # Decide which reference is correct based on timestamps
            # For now, trust the task assignment
            
            with self.transaction_manager.transaction("Repair bidirectional reference") as txn:
                txn.update(
                    'agent_states',
                    {'_id': issue.document_id['agent']},
                    {'$set': {'current_task_id': issue.data['task_id']}}
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair bidirectional reference: {e}")
            return False
    
    def _perform_repairs(self):
        """Perform automatic repairs for issues that can be fixed."""
        repairable_issues = [i for i in self.issues if i.can_auto_repair]
        
        self.logger.info(f"Found {len(repairable_issues)} repairable issues")
        
        for issue in repairable_issues:
            # Find the appropriate repair function
            repair_func = None
            
            for rule in self.validation_rules:
                if rule.repair_func and rule.collection in [issue.collection, '*']:
                    # This is simplified - in production would match more precisely
                    repair_func = rule.repair_func
                    break
            
            if repair_func:
                try:
                    if repair_func(issue):
                        self.repairs_performed += 1
                        self.logger.info(
                            f"Repaired issue: {issue.type.value} in "
                            f"{issue.collection} (ID: {issue.document_id})"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to repair issue: {issue.type.value}"
                        )
                except Exception as e:
                    self.logger.error(f"Error during repair: {e}")
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity."""
        counts = defaultdict(int)
        for issue in self.issues:
            counts[issue.severity] += 1
        return dict(counts)
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count issues by type."""
        counts = defaultdict(int)
        for issue in self.issues:
            counts[issue.type.value] += 1
        return dict(counts)
    
    def _format_issues(self) -> List[Dict[str, Any]]:
        """Format issues for report."""
        return [
            {
                'type': issue.type.value,
                'collection': issue.collection,
                'severity': issue.severity,
                'description': issue.description,
                'can_auto_repair': issue.can_auto_repair,
                'repair_suggestion': issue.repair_suggestion,
                'data': issue.data
            }
            for issue in self.issues[:100]  # Limit to first 100 for readability
        ]
    
    def _save_report(self, report: Dict[str, Any]):
        """Save consistency check report to database."""
        try:
            self.state_manager.db.consistency_reports.insert_one(report)
            self.logger.info("Consistency report saved to database")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
    
    def get_repair_script(self) -> str:
        """Generate a repair script for manual execution."""
        script_lines = [
            "#!/usr/bin/env python3",
            "# Consistency Repair Script",
            f"# Generated: {datetime.utcnow().isoformat()}",
            f"# Issues found: {len(self.issues)}",
            "",
            "from pymongo import MongoClient",
            "import datetime",
            "",
            "client = MongoClient('mongodb://localhost:27017/')",
            "db = client.agent_network",
            "",
            "# Repairs to perform:",
            ""
        ]
        
        for i, issue in enumerate(self.issues):
            if issue.can_auto_repair:
                script_lines.append(f"# Issue {i+1}: {issue.description}")
                script_lines.append(f"# Suggestion: {issue.repair_suggestion}")
                
                # Generate repair code based on issue type
                if issue.type == InconsistencyType.MISSING_REFERENCE:
                    if issue.collection == 'tasks':
                        script_lines.append(
                            f"db.tasks.update_one("
                            f"{{'_id': {issue.document_id}}}, "
                            f"{{'$set': {{'status': 'created'}}, '$unset': {{'assigned_to': 1}}}}"
                            f")"
                        )
                
                script_lines.append("")
        
        return "\n".join(script_lines)


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Data Consistency Checker')
    parser.add_argument('--auto-repair', action='store_true',
                       help='Automatically repair issues where possible')
    parser.add_argument('--generate-script', action='store_true',
                       help='Generate repair script instead of executing')
    parser.add_argument('--report-only', action='store_true',
                       help='Only generate report, no repairs')
    
    args = parser.parse_args()
    
    checker = ConsistencyChecker()
    
    print("Running consistency check...")
    report = checker.run_full_check(auto_repair=args.auto_repair and not args.report_only)
    
    # Print summary
    print(f"\nConsistency Check Complete")
    print(f"{'='*50}")
    print(f"Total Issues Found: {report['total_issues']}")
    print(f"Issues by Severity:")
    for severity, count in report['issues_by_severity'].items():
        print(f"  {severity}: {count}")
    print(f"\nIssues by Type:")
    for issue_type, count in report['issues_by_type'].items():
        print(f"  {issue_type}: {count}")
    
    if args.auto_repair and not args.report_only:
        print(f"\nRepairs Performed: {report['repairs_performed']}")
    
    if args.generate_script:
        script = checker.get_repair_script()
        with open('consistency_repair_script.py', 'w') as f:
            f.write(script)
        print("\nRepair script generated: consistency_repair_script.py")
    
    # Save detailed report
    report_file = f"consistency_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nDetailed report saved: {report_file}")


if __name__ == '__main__':
    main()