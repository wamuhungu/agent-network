# Agent Network

A network of Claude Code powered developer agents

## Overview

This is an agent network project that uses Claude Code agents to collaborate on tasks.

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
4. Run the dashboard: `python tools/run_dashboard.py`

## Project Structure

- `.agents/`: Agent configuration and personas
- `.claude/`: Claude-specific configurations and commands
- `.comms/`: Inter-agent communication logs
- `src/`: Source code
- `docs/`: Documentation
- `tests/`: Test suites
- `tools/`: Utility scripts and tools

## Usage

The system consists of two main agents:

1. **Manager Agent**: Responsible for breaking down requirements, assigning tasks, reviewing work, and making architectural decisions.
2. **Developer Agent**: Responsible for implementing code, writing tests, and documenting implementations.

Agents communicate through structured messages in the `.comms/` directory following standardized formats defined in `docs/standards/message_schema.json`.

The monitoring dashboard is accessible at http://localhost:5000 after starting the server.

## License

MIT