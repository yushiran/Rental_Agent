# Rental Agent System - LangGraph Agent Controller Implementation

## Architecture Overview

This system implements a multi-agent conversation framework for property rental negotiations between tenants and landlords. The architecture follows a modern approach using LangGraph's state-based flows and streaming capabilities.

```text
Meta Controller Graph
    ├── tenant_agent_graph (LangGraph subgraph)
    └── landlord_agent_graph (LangGraph subgraph)
```

## Key Components

### 1. Meta Controller (`meta_controller.py`)

The central coordinator managing turn-taking between tenant and landlord agents. Features include:

- **State Management**: Maintains conversation history and participant data
- **Agent Coordination**: Controls which agent speaks next
- **Termination Logic**: Detects when conversations should end
- **Streaming Support**: Real-time output delivery to clients

### 2. Group Negotiation Service (`group_negotiation.py`)

Handles multiple negotiation sessions between tenants and landlords:

- Matchmaking between tenants and suitable properties
- Session management and message routing
- WebSocket-based real-time communication
- Streaming responses from LLM agents

### 3. WebSocket Manager (`websocket.py`)

Manages real-time connections between clients and the server:

- Connection tracking for multiple sessions
- Efficient message broadcasting
- Stream handling with proper connection lifecycle management

### 4. API Service (`main.py`)

FastAPI-based endpoints exposing the negotiation functionality:

- REST endpoints for session management and message sending
- WebSocket endpoint for real-time communication
- Automatic negotiation features

## Flow Diagram

```text
Client → WebSocket → GroupNegotiationService → MetaController → Agent Subgraphs → Streaming Response → Client
```

## Termination Logic

Conversations will automatically terminate when:

1. An agreement is reached (keywords like "agreement", "contract", "deal")
2. A rejection is indicated (keywords like "not interested", "reject")
3. Maximum conversation length is reached (30 messages)

## Streaming Implementation

The system implements streaming in two layers:

1. **LangGraph Streaming**: Using `astream()` to get real-time results from the agents
2. **WebSocket Streaming**: Pushing chunks to connected clients as they become available

## Improvements Made

1. **Centralized Controller**: Implemented a meta-controller graph for better agent coordination
2. **Efficient State Management**: Proper state passing between subgraphs
3. **Stream-First Design**: End-to-end streaming from LLM to client
4. **Automatic Termination**: Conversations end naturally when appropriate
5. **Improved Error Handling**: Better error management throughout the system

## Usage Example

To start a negotiation session:

```bash
curl -X POST "http://localhost:8000/start-auto-negotiation-live" -H "Content-Type: application/json" -d '{"max_tenants": 5}'
```

To connect to the WebSocket for real-time updates:

```javascript
const socket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "response_chunk") {
    // Handle streaming chunk
    console.log(`${data.sender_name}: ${data.chunk}`);
  }
};
```
