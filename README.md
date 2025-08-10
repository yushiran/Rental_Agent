# 🏠 Rental Agent: Multi-Agent Rental Negotiation System

[🇨🇳 中文版本](./docs/README/README-zh.md) | 🇺🇸 English

An intelligent rental negotiation system based on [LangGraph](https://github.com/langchain-ai/langgraph), implementing automated dialogue negotiation between tenants and landlords with real-time map visualization.

## 🎯 Project Overview

This is a **multi-agent dialogue system** built with [LangGraph](https://github.com/langchain-ai/langgraph), focusing on **modular design**, **code clarity**, and **reusability**.

### ✨ Key Features

- 🤖 **Intelligent Negotiation**: Tenant agents automatically find suitable landlords and negotiate prices
- 🗺️ **Real-time Visualization**: Google Maps-based real-time negotiation process display
- 💾 **State Management**: MongoDB persistent storage for dialogue states and long-term memory
- 🔄 **Streaming Processing**: Real-time streaming output of negotiation processes and intermediate states
- 🎭 **Role Playing**: Different personality agent roles, such as rational and emotional types
- 📊 **Market Analysis**: Integrated UK rental market data analysis functionality

### 🏗️ System Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Database     │
│   (Vue.js)      │◄──►│   (FastAPI)     │◄──►│   (MongoDB)     │
│  - Map Visual   │    │  - LangGraph    │    │  - Chat State   │
│  - Real-time    │    │  - Agent Coord  │    │  - Long Memory  │
│  - WebSocket    │    │  - API Service  │    │  - Checkpoints  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ available memory
- Google Maps API Key (optional, for map functionality)

### 🔧 Environment Setup

**Step 1: Clone the project**

```bash
git clone <repository-url>
cd Rental_Agent
```

**Step 2: Configure environment variables**

```bash
# Copy config file
cp backend/config/config.example.toml backend/config/config.toml

# Edit config file and fill in your API keys
vim backend/config/config.toml
```

**Step 3: Start services**

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build
```

### 📱 Access Applications

After services start, you can access:

- **🎨 Frontend Interface**: <http://localhost:3000>
  - Real-time negotiation visualization
  - Agent role display
  - Negotiation process tracking

- **📚 API Documentation**: <http://localhost:8000/docs>
  - FastAPI auto-generated interactive documentation
  - WebSocket interface description
  - Test interface functionality

- **🗄️ MongoDB**: localhost:27017
  - Direct database connection
  - Use tools like MongoDB Compass

## 💡 Usage

### 1. Start Negotiation Session

**Option A: Through Frontend Interface**

1. Open <http://localhost:3000>
2. Click "Start Negotiation" button
3. Observe agent interactions on the map

**Option B: Through API**

```bash
# Initialize agent data
curl -X POST "http://localhost:8000/initialize" \
  -H "Content-Type: application/json" \
  -d '{
    "num_tenants": 3,
    "num_landlords": 5,
    "area": "London"
  }'

# Start negotiation
curl -X POST "http://localhost:8000/start-negotiation" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_session_001"
  }'
```

### 2. Real-time Monitoring

**WebSocket Connection:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/demo_session_001');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Negotiation update:', data);
};
```

**Event Types:**

- `agent_started`: Agent begins responding
- `message_sent`: Dialogue message sent
- `agent_thought`: Agent internal thinking
- `agreement_reached`: Agreement reached
- `dialogue_ended`: Dialogue ended

### 3. Reset Session

```bash
# Clear all dialogue memory
curl -X POST "http://localhost:8000/reset-memory"
```

## 📁 Project Structure

```text
Rental_Agent/
├── 🐳 docker-compose.yml          # Docker service orchestration
├── 📚 README.md                   # Project documentation
├── backend/                       # Backend service
│   ├── 🐳 Dockerfile             # Backend container config
│   ├── 📦 pyproject.toml         # Python dependency management
│   ├── app/                      # Application core code
│   │   ├── 🤖 agents/            # Agent definitions
│   │   ├── 🌐 api_service/       # API service layer
│   │   ├── 💬 conversation_service/ # Dialogue controller
│   │   ├── 📊 data_analysis/     # Market data analysis
│   │   ├── 💾 mongo/             # Database operations
│   │   └── 🛠️ utils/             # Utility functions
│   ├── config/                   # Configuration files
│   └── dataset/                  # UK rental dataset
├── frontend/                     # Frontend application
│   ├── 🐳 Dockerfile            # Frontend container config
│   ├── 📦 package.json          # Node.js dependencies
│   └── src/                     # Source code
│       ├── 🗺️ maps/             # Map-related components
│       ├── 🌐 network/          # Network communication
│       └── 🎨 components/       # UI components
└── docs/                        # Detailed technical documentation
    ├── 📋 markdown/             # Project documentation
    └── 📖 reference/            # Reference materials
```

## 🔧 Development Guide

### Modifying Code

```bash
# Development mode startup (supports hot reload)
docker-compose up

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Database Management

```bash
# Enter MongoDB container
docker exec -it rental_mongodb mongosh

# View databases
show dbs
use rental_agent_db
show collections
```

### Environment Cleanup

```bash
# Stop all services
docker-compose down

# Clean data volumes (⚠️ will delete all data)
docker-compose down --volumes

# Clean images
docker-compose down --rmi all
```

## 📊 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| 🧠 AI Framework | LangGraph, LangChain | 0.4+ | Agent orchestration & dialogue management |
| 🌐 Backend | FastAPI, Python | 3.13+ | REST API & WebSocket |
| 🎨 Frontend | Vite, JavaScript | ES6+ | Real-time visualization interface |
| 💾 Database | MongoDB | 7.0 | State persistence storage |
| 🗺️ Maps | Google Maps API | - | Geographic visualization |
| 🐳 Deployment | Docker, Docker Compose | - | Containerized deployment |

## 📖 Detailed Documentation

- **[📋 Project Architecture](./docs/markdown/PROJECT_OVERVIEW.md)** - Deep dive into system design
- **[📊 Dataset Description](./docs/markdown/DATASET_README.md)** - UK rental data details
- **[🔌 API Documentation](./docs/markdown/API_Service_Technical_Documentation_Updated.md)** - Interface usage guide
- **[🤖 Agent Design](./docs/markdown/agent_controller_design.md)** - Agent architecture analysis
- **[🔧 LangGraph Integration](./docs/markdown/LANGGRAPH_INTEGRATION.md)** - Workflow engine description

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open sourced under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 FAQ

### Q: Container startup failed?

A: Check port occupation, ensure ports 3000, 8000, 27017 are not occupied.

### Q: No response from negotiation?

A: Check API key configuration, ensure OpenAI or other LLM services are available.

### Q: Map cannot load?

A: Ensure Google Maps API Key is correctly configured.

### Q: Data loss?

A: Check if MongoDB data volume is correctly mounted.

---

**🎉 Start exploring the world of intelligent rental negotiation now!**

## 📚 References

For additional resources, tutorials, and tools used in this project, see our comprehensive [Reference Blog](./docs/README/reference_blog.md).
