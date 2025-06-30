# The backend part of this project is written in Python. Please criticize me harshly if I have any cognitive errors or incorrect ideas
Always ensure code clarity, readability, reusability, and efficiency.
Also, feel free to delete any unnecessary files

后端的启动方法是cd backend然后fastapi run app/api_service/main.py
前端的启动方法是cd frontend然后npm run dev

## 📌 Project Overview

This project implements a **multi-agent dialogue system** based on [LangGraph](https://github.com/langchain-ai/langgraph), emphasizing **modular design**, **code clarity**, and **reusability**.

Each intelligent agent (such as TenantAgent, LandlordAgent) is implemented as an independent LangGraph. A Controller Graph coordinates the turn-taking dialogue between them for housing rental negotiations.

All dialogue sessions are **initiated by the tenant** and first go through a **matching node** to filter suitable landlords before starting the conversation.

## 🎯 Design Highlights

- **Tenant-Initiated Negotiation**
  - Each session begins with a matching node triggered by TenantAgent.
  - This node selects a LandlordAgent based on internal configuration or retrieval mechanisms.
  - Then formally enters the dynamic dialogue loop between tenant and landlord.

- **Agent-as-Graph Architecture**
  - TenantAgent and LandlordAgent are complete LangGraphs with their own set of nodes (such as summarize, retrieve, reason, reflect).
  - Each graph can be independently reused and tested.

- **Controller Graph**
  - An independent scheduling LangGraph responsible for turn control, agent switching, end condition judgment, and other logic.
  - Includes termination conditions such as reaching an agreement or one party refusing to continue the dialogue.

## 💾 MongoDB-based Memory and State Management

### Short-term Memory
- **Checkpoints** (MONGO_STATE_CHECKPOINT_COLLECTION): Complete snapshots of the current conversation state for fault tolerance and recovery.
- **Incremental Writes** (MONGO_STATE_WRITES_COLLECTION): State changes recorded after each node execution to improve performance.

### Long-term Memory
- Agent-specific long-term knowledge is stored in MONGO_LONG_TERM_MEMORY_COLLECTION.

### State Management
Implemented by AsyncMongoDBSaver, with features including:
- Initial checkpoint creation
- Incremental writes after each round of dialogue
- State recovery based on the latest valid checkpoint + write records
- Support for stateless reset via the /reset-memory interface

## 🔁 Streaming Support

The controller graph provides an astream_events() interface that can be used to stream intermediate events (such as messages, state transitions) to the frontend or logging system.

This allows the dialogue process between multiple agents to be observed and feedback provided in real-time.

## 🧱 Technology Stack

- [LangGraph](https://github.com/langchain-ai/langgraph) — For modeling agents and processes
- LangChain — For memory management, tool scheduling, and LLM integration
- MongoDB — For persistence of short-term and long-term memories
- FastAPI — Provides APIs for session initiation, streaming, and memory reset
- Docker — For containerized deployment
- Optional support: WebSocket / SSE — For real-time data streaming to the frontend

---
## 🎮 Frontend Interaction Design

The frontend of this project builds a visual interface for **showcasing the entire multi-agent rental dialogue** process.

### 👥 Core Interaction Logic

- Users start a simulation round through the interface button, and the system initiates the negotiation process from the tenant agent (TenantAgent).
- Multiple landlord agents (LandlordAgent) are selected by the backend matching logic as interaction partners.
- The negotiation process displays character behaviors, emotions, and dialogue content in real-time.
- Interface elements are driven by backend events (such as `agent_started`, `message_sent`, etc.).
- If negotiation is successful, contract signing feedback is displayed; otherwise, negotiation failure feedback is shown.

### 🔌 Communication Mechanism

The frontend communicates with the backend LangGraph Controller in real-time via HTTP + WebSocket:

- ✅ Using REST API:
  - Trigger matching process: `/start-session`
  - Reset memory state: `/reset-memory`
- 🔁 Using WebSocket to receive streaming events:
  - `agent_started`: A character starts responding
  - `message_sent`: A text dialogue is sent
  - `agent_thought`: Character's internal thinking process
  - `agreement_reached` / `dialogue_ended`: Dialogue success / failure
