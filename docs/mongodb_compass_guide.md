# MongoDB Compass Connection Guide

## Connecting to Local MongoDB Instance

### Quick Connection
1. In MongoDB Compass, click **"Add new connection"** (green button)
2. Enter connection string: `mongodb://localhost:27017`
3. Click **"Connect"**

### Connection Details
- **Host:** localhost
- **Port:** 27017
- **Authentication:** None (local development)
- **Database:** agent_network

### After Connecting
Once connected, you'll see:
- **agent_network** database in the left sidebar
- Four collections:
  - `agent_states` - Current state of each agent
  - `tasks` - Task assignments and status
  - `activity_logs` - Agent activity history
  - `work_requests` - Work request queue

### Viewing Data
1. Click on **agent_network** database
2. Select any collection to view documents
3. Use the query bar to filter results
4. Click on documents to expand and view details

### Useful Queries
- View all agent states: `{}`
- Find active agents: `{"status": "active"}`
- Find pending tasks: `{"status": "pending"}`
- Recent activities: Sort by `timestamp` (descending)

### MongoDB Compass Features
- **Schema Analysis** - Understand your data structure
- **Query History** - Save and reuse queries
- **Aggregation Pipeline Builder** - Create complex queries visually
- **Performance Insights** - Monitor query performance
- **Import/Export** - Backup or migrate data