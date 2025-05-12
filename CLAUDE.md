# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent system built with Claude Code. The system consists of specialized agents (Manager, Developer) that collaborate to solve complex problems.

## Directory Structure

- `.agents/` - Agent configurations and personas
  - `manager/` - Manager agent files
  - `developer/` - Developer agent files
- `.claude/` - Claude-specific configurations
  - `commands/` - Custom Claude Code commands
- `.comms/` - Inter-agent communication logs
- `src/` - Source code
- `docs/` - Documentation
- `tests/` - Test suites
- `tools/` - Utility scripts and tools

## Agent Roles

### Manager Agent
- Coordinates the activities of other agents
- Allocates tasks and resources
- Monitors progress and resolves conflicts
- Ensures project goals are met

### Developer Agent
- Implements code based on specifications
- Tests and debugs implementations
- Performs code reviews
- Creates technical documentation

## Working with This Codebase

When working with this codebase:

1. Start by understanding the current state of the system from the `.comms/` directory
2. Check agent-specific guidelines in the `.agents/` directory
3. Use custom commands in the `.claude/commands/` directory for special operations

## Agent Communication

Agents should communicate through structured messages that include:
- Clear task descriptions
- Required context
- Expected outputs
- Dependencies on other tasks

## Development Workflow

As this project evolves, this section will be updated with specific workflows and commands for development tasks.