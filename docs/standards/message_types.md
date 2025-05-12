# Message Types and Content Structure

This document describes each message type and its expected content structure for agent communication.

## task_assignment

Used by the manager agent to assign tasks to other agents.

```json
{
  "content": {
    "task_id": "string",
    "title": "string",
    "description": "string",
    "requirements": ["string"],
    "acceptance_criteria": ["string"],
    "deadline": "date-time",
    "resources": [
      {
        "type": "string",
        "url": "string",
        "description": "string"
      }
    ],
    "dependencies": ["task_id"]
  }
}
```

## status_update

Used by agents to report progress on assigned tasks.

```json
{
  "content": {
    "task_id": "string",
    "status": "not_started|in_progress|blocked|completed",
    "progress_percentage": "number",
    "description": "string",
    "blockers": [
      {
        "description": "string",
        "severity": "low|medium|high",
        "potential_solutions": ["string"]
      }
    ],
    "next_steps": ["string"],
    "estimated_completion": "date-time"
  }
}
```

## question

Used by agents to ask questions about task requirements or implementation details.

```json
{
  "content": {
    "task_id": "string",
    "question": "string",
    "context": "string",
    "attempted_solutions": ["string"],
    "impact_on_progress": "low|medium|high"
  }
}
```

## review

Used by the manager agent to provide feedback on completed work.

```json
{
  "content": {
    "task_id": "string",
    "status": "approved|changes_requested|rejected",
    "comments": [
      {
        "file_path": "string",
        "line_number": "number",
        "comment": "string",
        "type": "suggestion|issue|praise"
      }
    ],
    "general_feedback": "string",
    "requested_changes": ["string"]
  }
}
```

## approval

Used by the manager agent to approve completed work.

```json
{
  "content": {
    "task_id": "string",
    "approval_reason": "string",
    "approved_version": "string",
    "follow_up_tasks": ["task_id"],
    "notes": "string"
  }
}
```

## rejection

Used by the manager agent to reject work that doesn't meet requirements.

```json
{
  "content": {
    "task_id": "string",
    "rejection_reason": "string",
    "specific_issues": [
      {
        "issue": "string",
        "severity": "low|medium|high",
        "suggested_fix": "string"
      }
    ],
    "next_steps": ["string"],
    "reference_materials": ["string"]
  }
}
```